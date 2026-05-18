import logging
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater

from a2a.types import (
     DataPart,
     InvalidParamsError,
     SendStreamingMessageSuccessResponse,
     Task,
     TaskArtifactUpdateEvent,
     TaskState,
     TaskStatusUpdateEvent,
     TextPart,
     UnsupportedOperationError
     )

from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
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
               raise ServerError(error=InvalidParamsError(message=error))

          query = request_context.get_user_input()
          logger.info(f"Agent {self.agent.agent_name} received query: {query}")

          task = request_context.current_task
          if not task:
               task = new_task(request_context.message)
               await event_queue.enqueue(task)

          updater = TaskUpdater(event_queue, task.id, task.context_id)

          async for item in self.agent.stream(query, task.context_id, task.id):
               # Agent to Agent call will return events
               # Update teh relevant ids to proxy back.
               if hasattr(item, 'root')  and isinstance(item.root, SendStreamingMessageSuccessResponse):
                    event = item.root.result
                    if isinstance(event, (TaskStatusUpdateEvent | TaskArtifactUpdateEvent)):
                         await event_queue.enqueue_event(event)
                    continue

               is_task_complete = item['is_task_complete']
               require_user_input = item['require_user_input']


               if is_task_complete:
                    if item['response_type'] == 'data':
                         part = DataPart(data=item['content'])
                    else:
                         part = TextPart(text=item['content'])

                    await updater.add_artifact(
                         [part],
                         name=f"{self.agent.agent_name}-result",
                    )
                    await updater.complete()
                    break
               if require_user_input:
                    await updater.update_status(
                         status = TaskState.TASK_STATE_INPUT_REQUIRED,
                         message= new_agent_text_message(
                              item['content'],
                              task.context_id,
                              task.id
                         ),
                         final=True
                    )
                    break
               await updater.update_status(
                    status = TaskState.TASK_STATE_WORKING,
                    message= new_agent_text_message(
                         item['content'],
                         task.context_id,
                         task.id
                    ),

               )
     def _validate_input(self, request_context: RequestContext) -> bool:
          return False

     async def cancel(
          self,
          request: RequestContext,
          event_queue: EventQueue
          )  -> Task| None:

          raise ServerError(error=UnsupportedOperationError(message="Cancel operation is not supported for this agent"))