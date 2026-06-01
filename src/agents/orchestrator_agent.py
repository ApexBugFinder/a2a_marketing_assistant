import os
import json
import logging
from typing import Any
from google.protobuf.json_format import MessageToDict
from dotenv import load_dotenv
from collections.abc import AsyncIterable

from a2a.types import (
     StreamResponse,
     TaskArtifactUpdateEvent,
     TaskState,
     TaskStatusUpdateEvent,
)
from common import instructions
from common.base_agent import BaseAgent
from common.utils import init_api_key
from common.workflow import Status, WorkflowNode, WorkflowGraph

from google import genai
logger  = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
     """The OrchestratorAgent is responsible for managing the overall workflow and coordination of tasks among different agents in the system.
     It oversees the execution of tasks, monitors their progress, and handles any necessary communication or data exchange between agents. The OrchestratorAgent ensures that the various components of the system work together seamlessly to achieve the desired outcomes based on user queries and interactions."""

     def __init__(self):
          init_api_key()
          load_dotenv()
          logger.info("Initializing Orchestrator Agent")

          super().__init__(
               agent_name="Orchestrator Agent",
               description="An agent that facilitates agent communication",
               content_types=['text', 'text/plain']
          )
          self.graph = None
          self.results = []
          self.research_context = []
          self.query_history = []
          self.context_id = None
          self.my_model = os.getenv('LITE_LLM_AGENT')


     async def generate_summary(self) -> str:

          client = genai.Client()
          response = await client.aio.models.generate_content(
               model=self.my_model,
               contents = instructions.SUMMARY_COT_PROMPT.replace('{RESULTS}', str(self.results)),
               config = {'temperature': 0.0}
          )
          return response.text

     async def answer_user_question(self, question:str) -> str:
          try:
               client = genai.Client()
               response = await client.aio.models.generate_content(
                    model=os.getenv('LITE_LLM_AGENT'),
                    contents = instructions.QA_COT_PROMPT
                    .replace('{RESEARCH_CONTEXT}', str(self.research_context))
                    .replace(
                         "{CONVERSATION_HISTORY}", str(self.query_history))
                    .replace("{RESEARCH_QUESTION}", question),
                    config = {'temperature': 0.0,
                              'response_mime_type': 'application/json'}
               )
               return response.text
          except Exception as e:
               logger.error(f"Error in answer_user_question: {e}")
               return json.dumps({'can_answer': 'no', 'answer': 'Cannot answer based on provided context'})

     def set_node_attributes(self, node_id:str,
                         task_id=None,
                         context_id=None,
                         query=None):
          att_val = {}
          if task_id:
               att_val['task_id'] = task_id
          if context_id:
               att_val['context_id'] = context_id
          if query:
               att_val['query'] = query
          self.graph.set_node_attributes(node_id, att_val)

     def add_graph_node(
          self,
          task_id,
          context_id,
          query:str,
          node_id: str = None,
          node_key: str = None,
          node_label: str = None,
     ) -> WorkflowNode:
          """Add a new node to the workflow graph with the given task, context, and optional identifiers and labels.
          This method creates a new WorkflowNode instance and adds it to the graph, allowing for dynamic
          construction and modification of the workflow based on the tasks and interactions
          that arise during the execution of the agents."""

          node= WorkflowNode(
               task = query,
               node_key = node_key,
               node_label = node_label)

          self.graph.add_node(node)
          if node_id:
               self.graph.add_edge(node_id, node.id)
          self.set_node_attributes(node.id, task_id=task_id, context_id=context_id, query=query)
          return node

     def clear_state(self):
          """Clear the internal state of the OrchestratorAgent, including any stored results, context, and query history.
          This method can be used to reset the agent's state between different user interactions or sessions,
          ensuring that previous information does not interfere with new queries and allowing for a fresh start in handling new tasks and interactions."""
          self.graph = None
          self.results.clear()
          self.research_context.clear()
          self.query_history.clear()

     async def stream(
          self,
          query,
          context_id,
          task_id
     ) -> AsyncIterable[dict[str, Any]]:
          """Execute and stream response"""
          logger.info(
               f"Running {self.agent_name} for: \nThe session: {context_id}, \ntask: {task_id}, \nquery: {query}"
          )

          if not query:
               raise ValueError("Query cannot be empty")

          if self.context_id != context_id:
               # New session, clear the state
               self.clear_state()
               self.context_id = context_id

          self.query_history.append(query)
          start_node_id = None


          # Keep the graph ONLY if it is paused waiting for user input.
          # Any other state (RUNNING, COMPLETED, ERROR, INITIALIZED) means the
          # previous generator was abandoned or already finished — reset so the
          # next request starts clean rather than walking orphaned nodes.
          if self.graph is not None and self.graph.state != Status.PAUSED:
               logger.warning(
                    "Orchestrator: discarding graph in state=%s for context_id=%s",
                    self.graph.state, context_id,
               )
               self.clear_state()

          if not self.graph:
               self.graph = WorkflowGraph()
               # If multiple messages are in history, give the planner full context
               # so it can reconstruct the campaign request even after a state reset.
               planner_query = (
                    '\n---\n'.join(self.query_history)
                    if len(self.query_history) > 1
                    else query
               )
               planner_node = self.add_graph_node(
                    task_id=task_id,
                    context_id=context_id,
                    query=planner_query,
                    node_key='planner',
                    node_label='Planner Agent'
               )
               start_node_id = planner_node.id

          else:
               # self.graph.state == Status.PAUSED — resume from the paused node
               start_node_id = self.graph.pause_node_id
               self.set_node_attributes(node_id=start_node_id, query=query)

          # Capture a local reference so a concurrent request calling clear_state()
          # cannot set self.graph = None while this coroutine is suspended at an await.
          graph = self.graph

          pending_question: str | None = None
          node_errors: list[dict] = []
          # Track which nodes have already been auto-answered so we don't loop.
          # Each paused node gets at most one auto-answer; a second question from
          # the same node is always relayed to the user.
          auto_answered_nodes: set[str] = set()
          max_iterations = 50
          iterations = 0

          while iterations < max_iterations:
               iterations += 1
               graph.set_node_attributes(start_node_id, {
                    'task_id': task_id,
                    'context_id': context_id,
               })
               should_resume_workflow = False
               pending_question = None

               async for chunk in graph.run_workflow(start_node_id=start_node_id):
                    logger.info(
                        f"Workflow chunk: type={type(chunk).__name__}, "
                        f"has_artifact={chunk.HasField('artifact_update')}, "
                        f"has_status={chunk.HasField('status_update')}"
                    )

                    # Collect node-level errors surfaced by run_workflow
                    if isinstance(chunk, dict) and chunk.get('node_error'):
                         logger.error(f"Node error received: {chunk}")
                         node_errors.append(chunk)
                         continue

                    if isinstance(chunk, StreamResponse):

                         if chunk.HasField('status_update'):
                              task_status_event = chunk.status_update
                              chunk_context_id = task_status_event.context_id

                              if task_status_event.status.state == TaskState.TASK_STATE_COMPLETED:
                                   # Yield a progress update so the client sees the node finished.
                                   yield {
                                        'response_type': 'text',
                                        'is_task_complete': False,
                                        'require_user_input': False,
                                        'content': f'Task completed.',
                                   }
                                   continue

                              if task_status_event.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
                                   try:
                                        question = task_status_event.status.message.parts[0].text
                                   except (AttributeError, IndexError):
                                        question = "Please provide more information to proceed."
                                   try:
                                        answer = json.loads(await self.answer_user_question(question))
                                        logger.info(f"Agent Answer: {answer}")
                                        pause_node = graph.pause_node_id
                                        already_answered = pause_node in auto_answered_nodes
                                        can_answer = str(answer.get('can_answer', '')).lower() == 'yes'
                                        if can_answer and not already_answered:
                                             auto_answered_nodes.add(pause_node)
                                             query = str(answer.get('answer', ''))
                                             if not query.strip():
                                                  logger.warning("Auto-answer was 'yes' but answer text was empty — relaying to user.")
                                                  pending_question = question
                                             else:
                                                  start_node_id = pause_node
                                                  graph.set_node_attributes(start_node_id, {'query': query})
                                                  should_resume_workflow = True
                                        else:
                                             if already_answered:
                                                  logger.info(
                                                       "Node %s already auto-answered once — relaying follow-up to user.",
                                                       pause_node,
                                                  )
                                             pending_question = question
                                   except Exception as e:
                                        logger.error(f"Error cannot convert answer data: {e}")
                                        pending_question = question
                                   if should_resume_workflow:
                                        # Notify the client that we auto-answered and are continuing.
                                        yield {
                                             'response_type': 'text',
                                             'is_task_complete': False,
                                             'require_user_input': False,
                                             'content': '[auto-answered agent question, continuing workflow...]',
                                        }
                                   continue

                         if chunk.HasField('artifact_update'):
                              artifact = chunk.artifact_update.artifact
                              self.results.append(artifact)
                              if artifact.name == 'PlannerAgent-result':
                                   artifact_data = MessageToDict(artifact.parts[0].data)
                                   if artifact_data is None:
                                        error_text = artifact.parts[0].text
                                        logger.error(f"Planner returned a non-data artifact: {error_text}")
                                        yield {
                                             'response_type': 'text',
                                             'is_task_complete': True,
                                             'require_user_input': False,
                                             'content': f"Planner could not build a plan: {error_text}",
                                        }
                                        return
                                   if 'research_context' in artifact_data:
                                        self.research_context.append(artifact_data['research_context'])
                                   logger.info(
                                        f"Updating workflow with {len(artifact_data.get('tasks', []))} task nodes"
                                   )
                                   current_node_id = start_node_id
                                   for idx, task_data in enumerate(artifact_data.get('tasks', [])):
                                        node = WorkflowNode(
                                             task=task_data['description'],
                                        )
                                        graph.add_node(node)
                                        if current_node_id:
                                             graph.add_edge(current_node_id, node.id)
                                        graph.set_node_attributes(node.id, {
                                             'task_id': task_data.get('id'),
                                             'context_id': context_id,
                                             'query': task_data['description'],
                                        })
                                        current_node_id = node.id
                                        if idx == 0:
                                             should_resume_workflow = True
                                             start_node_id = node.id
                              else:
                                   # Non-Planner artifact — may contain dynamic_tasks for
                                   # agent-driven workflow routing.
                                   try:
                                        artifact = chunk.artifact_update.artifact
                                        dynamic_tasks = None
                                        if artifact.parts and artifact.parts[0].HasField('data'):
                                             artifact_data = MessageToDict(artifact.parts[0].data)
                                             dynamic_tasks = artifact_data.get('dynamic_tasks', [])

                                        if dynamic_tasks:
                                             current_node_id = graph.current_node_id
                                             first_dynamic_node_id = None
                                             for dt in dynamic_tasks:
                                                  node = self.add_graph_node(
                                                       task_id=task_id,
                                                       context_id=context_id,
                                                       query=dt['description'],
                                                       node_id=current_node_id,
                                                  )
                                                  # Set agent_name on the node for direct routing
                                                  # (skips semantic search in find_agent_for_tasks)
                                                  if dt.get('agent_name'):
                                                       node.agent_name = dt['agent_name']
                                                  current_node_id = node.id
                                                  if first_dynamic_node_id is None:
                                                       first_dynamic_node_id = node.id
                                             should_resume_workflow = True
                                             start_node_id = first_dynamic_node_id
                                             logger.info(
                                                  f"[{artifact.name}] inserted {len(dynamic_tasks)} dynamic task(s) "
                                                  f"after node {graph.current_node_id}"
                                             )
                                             yield {
                                                  'response_type': 'text',
                                                  'is_task_complete': False,
                                                  'require_user_input': False,
                                                  'content': (
                                                       f'[{artifact.name or "Task"}] completed. '
                                                       f'Dynamically added {len(dynamic_tasks)} follow-up task(s).'
                                                  ),
                                             }
                                        else:
                                             yield {
                                                  'response_type': 'text',
                                                  'is_task_complete': False,
                                                  'require_user_input': False,
                                                  'content': f'[{artifact.name or "Task"}] completed.',
                                             }
                                   except Exception as e:
                                        logger.warning(f"Failed to parse non-planner artifact for dynamic tasks: {e}")
                                        yield {
                                             'response_type': 'text',
                                             'is_task_complete': False,
                                             'require_user_input': False,
                                             'content': f'[Task] completed.',
                                        }
                                   continue

                    if not should_resume_workflow and not pending_question:
                         logger.info('No workflow resume detected, yielding chunk')
                         yield chunk

               if pending_question:
                    logger.info(f"Relaying agent question to user: {pending_question}")
                    break

               if not should_resume_workflow:
                    logger.info('Workflow iteration complete and no restart requested. Exiting main loop.')
                    break

               logger.info('Restarting workflow loop.')

          if iterations >= max_iterations:
               logger.error(
                    "Orchestrator: workflow loop exceeded max_iterations (%d) — force-exiting to prevent infinite loop.",
                    max_iterations,
               )
               self.clear_state()
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': (
                         f"The workflow ran for too many iterations ({max_iterations}) and was stopped "
                         "to prevent an infinite loop. Please try again with a more specific request."
                    ),
               }
               return

          if graph is None:
               logger.error("Orchestrator: graph is None at end of stream — this should never happen.")
               self.clear_state()
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': "An internal error occurred. Please try again.",
               }
               return

          if pending_question:
               # Workflow paused — relay the question to the user without clearing state
               yield {
                    'response_type': 'text',
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': pending_question,
               }
          elif graph.state == Status.ERROR:
               error_lines = '\n'.join(
                    f"  - {e['task'][:100]}...\n    Reason: {e['error']}"
                    for e in node_errors
               )
               logger.error(f"Workflow completed with task failures:\n{error_lines}")
               self.clear_state()
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': (
                         f"One or more tasks failed to execute. "
                         f"Please ensure all agent servers and the MCP server are running.\n\n"
                         f"Failed tasks:\n{error_lines}"
                    ),
               }
          elif graph.state == Status.COMPLETED:
               logger.info(f"Generating summary for {len(self.results)} results")
               try:
                    summary = await self.generate_summary()
               except Exception as e:
                    logger.error(f"Summary generation failed: {e}", exc_info=True)
                    summary = f"Campaign workflow completed. Unable to generate a summary: {type(e).__name__}: {e}"
               self.clear_state()
               logger.info(f"Summary: {summary}")
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': summary,
               }
          else:
               logger.warning(f"Workflow ended in non-completed state: {graph.state}")
               self.clear_state()
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': f"The workflow did not complete as expected (state: {graph.state}). Please try again.",
               }