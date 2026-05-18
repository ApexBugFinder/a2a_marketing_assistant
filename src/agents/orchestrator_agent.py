import json
import logging

from collectins.abc import AsyncIterable

from a2a.types import (
     SendStreamingMessageSuccessResponse,
     TaskArtifactUpdateEvent,
     TaskState,
     TaskStatusUpdateEvent

)
from common import prompts
from common.base_agent import BaseAgent
from common.utils import init_api_key
from common.workflow import Status, WorkflowNode,WorkflowGraph

from google import genai
logger  = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
     """The OrchestratorAgent is responsible for managing the overall workflow and coordination of tasks among different agents in the system.
     It oversees the execution of tasks, monitors their progress, and handles any necessary communication or data exchange between agents. The OrchestratorAgent ensures that the various components of the system work together seamlessly to achieve the desired outcomes based on user queries and interactions."""

     def __init__(self):
          init_api_key()

          logger.info("Initializing Orchestrator Agent")

          super().__init__(
               agent_name="Orchestrator Agent",
               description="An agent that facilitates agent communication",
               content_types=['text', 'text/plain']
          )
          self.graph = None
          self.results = []
          self.travel_context = []
          self.query_history = []
          self.context_id = None


     async def generate_summary(self) -> str:

          client = genai.Client()
          response = client.models.generate_content(
               model="gemini-2.0-flash",
               contents = prompts.SUMMMARY_COT_PROMPT.replace(),
               config = {'temperature': 0.0}
          )
          return response.content

     async def answer_user_question(self, question:str) -> str:
          try:
               client = genai.Client()
               response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents = prompts.QA_COT_PROMPT
                    .replace('{TRIP_CONTEXT}', str(self.travel_context))
                    .replace(
                         "{CONVERSAVTION_HISTORY}", str(self.query_history))
                    .repplace("{TRIP_QUESTION}", question),
                    config = {'temperature': 0.0,
                              'response_mime_type': 'application/json'}
               )
               return response.content
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
          self.travel_context.clear()
          self.query_history.clear()

     async def stream(
          self,
          query,
          context_id,
          task_id
     ) -> AsyncIterable[dict[str, any]]:
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


          if not self.graph:
               self.graph = WorkflowGraph()
               planner_node = self.add_graph_node(
                    task_id=task_id,
                    context_id=context_id,
                    query=query,
                    node_key='planner',
                    node_label='Planner Agent'
               )
               start_node_id = planner_node.id

          elif self.graph.state == Status.PAUSED:
               start_node_id = self.graph.paused_node_id
               self.set_node_attributes(node_id=start_node_id, query=query)


          # This loop can be avoided if the workflow graph is dynamic or
          # is built from the results of the planner when the planner
          # iself is not a part of the graph.
          # TODO: Make the graph dynamically iterable over edges
          while True:
               self.set_node_attributes(
                    node_id = start_node_id,
                    task_id = task_id,
                    context_id = context_id
               )
               # Resume workflow, used when the workflow nodes are updated
               should_resume_workflow = False
               async for chunk in self.graph.run_workflow(
                    start_node_id = start_node_id,
               ):
                    logger.info(f"Workflow chunk: {chunk}")
                    if isinstance(chunk.root, (SendStreamingMessageSuccessResponse)):

                         if isinstance(chunk.root.result, TaskStatusUpdateEvent ):
                              task_status_event = chunk.root.result
                              context_id = task_status_event.context_id
                              # The graph node returned TaskStatusUpdateEvent,
                              # Check if the node is complete and continue to the next node



                              if (task_status_event.status.state == TaskState.TASK_STATE_COMPLETED  and context_id):
                                        ## yeild??
                                        continue

                              if (task_status_event.status.state == TaskState.TASK_STATE_INPUT_REQUIRED and context_id):
                                        ## yeild??
                                        question = task_status_event.status.message.parts[0].root.text
                                        try:
                                             answer = json.loads(self.answer_user_question(question))
                                             logger.info(f"Agent Answer: {answer}")

                                             if answer['can_answer']== 'yes':
                                                  # Orchestrator can answer on behalf of the agent, continue the workflow execution
                                                  query = answer['answer']
                                                  start_node_id = self.graph.paused_node_id
                                                  self.set_ndoe_attributes(node_id=start_node_id,
                                                                           query=query)
                                                  should_resume_workflow = True
                                        except Exception as e:
                                             logger.error(f"Error cannot convert answer data: {e}")




                              if isinstance(chunk.root.result, TaskArtifactUpdateEvent):
                                   # The graph node returned TaskArtifactUpdateEvent,
                                   # which means the node has new information that might be relevant for the next nodes in the workflow
                                   # Resume the workflow to pass the new information to the next nodes
                                   artifact = chunk.root.result.artifact
                                   self.results.append(artifact)
                                   if artifact.name == 'PlannerAgent-result':
                                             # Planning agent returned data, update graph
                                             artifact_data = artifact.parts[0].root.data
                                             if 'trip_info' in artifact_data:
                                                  self.travel_context.append(artifact_data['trip_info'])
                                             logger.info(
                                                  f"Updating workflow with {len(artifact_data['tasks'])} task nodes"
                                             )
                                             # Define the edges

                                             current_node_id = start_node_id
                                             for idx, task_data in enumerate(
                                                  artifact_data['tasks']
                                             ):
                                                  node = self.add_graph_node(
                                                       task_id = task_data['id'],
                                                       context_id = artifact_data['context_id'],
                                                       query = task_data['description'],
                                                       node_id = current_node_id
                                                  )

                                                  current_node_id = node.id
                                                  if idx==0:
                                                       should_resume_workflow = True
                                                       start_node_id = node.id
                                   else:
                                             # Not planner but artifacts from other tasks,
                                             # continue to the next node in the workflow.
                                             # client does not get the artifact,
                                             # a summary is shown at the end of the workflow.
                                             continue
                    if not should_resume_workflow:
                         logger.info('No workflow resume detected, yielding chunk')
                         # yield partial execution
                         yield chunk

               if not should_resume_workflow:
                    logger.info('Workflow interation complete and no restart requested. Exiting main loop.')
                    break

               else:
                    # Readable logs
                    logger.info('Restarting workflow loop.')
          if self.graph.state == Status.COMPLETED:
               #  All individual actions complete, now generate the summary
               logger.info(f"Fenerating summary for {len(self.results)} results")
               summary = await self.generate_summary()
               self.clear_state()
               logger.info(f"Summary: {summary}")
               yield {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': summary
               }