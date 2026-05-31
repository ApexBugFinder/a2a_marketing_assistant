import logging
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater

from a2a.types import (
     InvalidParamsError,
     StreamResponse,
     Task,
     TaskArtifactUpdateEvent,
     TaskState,
     TaskStatusUpdateEvent,
     UnsupportedOperationError,
     )

from a2a.helpers import new_task_from_user_message, new_text_message, new_text_part, new_data_part
from common.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class GenericAgentExecutor(AgentExecutor):
     """A generic agent executor  that can execute any agent that inherits from the BaseAgent class.
     It implements the execute method to handle the execution logic for the agent,
     including processing the input, invoking the agent's capabilities, and returning the response. """

     def __init__(self, agent:BaseAgent):
          self.agent = agent

     async def execute(self,
                    request_context: RequestContext,
                    event_queue: EventQueue) -> None:
          """Execute the agent's capabilities based on the input from the request context and send the response back through the event queue."""
          logger.info(f"Executing agent {self.agent.agent_name} with request context: {request_context}")
          error = self._validate_input(request_context)
          if error:
               raise InvalidParamsError(message=error)

          query = request_context.get_user_input()
          logger.info(f"Agent {self.agent.agent_name} received query: {query}")

          task = request_context.current_task
          if not task:
               task = new_task_from_user_message(request_context.message)
               await event_queue.enqueue_event(task)

          updater = TaskUpdater(event_queue, task.id, task.context_id)

          try:
               async for item in self.agent.stream(query, task.context_id, task.id):
                    # Sub-agent StreamResponse events carry the sub-agent's task ID,
                    # not this task's ID. Re-stamp them via updater so TaskManager accepts them.
                    if isinstance(item, StreamResponse):
                         if item.HasField('status_update'):
                              state = item.status_update.status.state
                              if state == TaskState.TASK_STATE_INPUT_REQUIRED:
                                   msg = None
                                   if item.status_update.status.HasField('message'):
                                        msg = item.status_update.status.message
                                   await updater.update_status(
                                        state=TaskState.TASK_STATE_INPUT_REQUIRED,
                                        message=msg,
                                   )
                                   break
                              elif state != TaskState.TASK_STATE_COMPLETED:
                                   msg = None
                                   if item.status_update.status.HasField('message'):
                                        msg = item.status_update.status.message
                                   await updater.update_status(
                                        state=TaskState.TASK_STATE_WORKING,
                                        message=msg,
                                   )
                         elif item.HasField('artifact_update'):
                              artifact = item.artifact_update.artifact
                              await updater.add_artifact(
                                   parts=list(artifact.parts),
                                   name=artifact.name,
                              )
                         continue

                    is_task_complete = item['is_task_complete']
                    require_user_input = item['require_user_input']

                    if is_task_complete:
                         if item['response_type'] == 'data':
                              part = new_data_part(data=item['content'])
                         else:
                              part = new_text_part(text=item['content'])

                         await updater.add_artifact(
                              [part],
                              name=f"{self.agent.agent_name}-result",
                         )
                         await updater.complete()
                         break
                    content = item['content']
                    if not isinstance(content, str):
                         content = str(content)

                    if require_user_input:
                         await updater.update_status(
                              state=TaskState.TASK_STATE_INPUT_REQUIRED,
                              message=new_text_message(
                                   text=content,
                                   context_id=task.context_id,
                                   task_id=task.id,
                              ),
                         )
                         break
                    await updater.update_status(
                         state=TaskState.TASK_STATE_WORKING,
                         message=new_text_message(
                              text=content,
                              context_id=task.context_id,
                              task_id=task.id,
                         ),
                    )
          except Exception as e:
               error_msg = f"{type(e).__name__}: {e}"
               logger.error(
                    f"Agent '{self.agent.agent_name}' raised an unhandled exception: {error_msg}",
                    exc_info=True,
               )
               try:
                    await updater.update_status(
                         state=TaskState.TASK_STATE_FAILED,
                         message=new_text_message(text=f"[{self.agent.agent_name}] FAILED — {error_msg}"),
                    )
               except Exception:
                    raise e

     def _validate_input(self, request_context: RequestContext) -> bool:
          return False

     async def cancel(
          self,
          context: RequestContext,
          event_queue: EventQueue,
          ) -> None:
          raise UnsupportedOperationError(message='Cancel operation is not supported for this agent')