import json
import logging
import re

from collections.abc import AsyncIterable
from typing import Any

from common.agent_runner import AgentRunner
from common.base_agent import BaseAgent
from common.utils import get_mcp_server_config, init_api_key
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.genai import types as genai_types
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class MarketingAssistantAgent(BaseAgent):
     """Marketing Assistant Agent is backed by ADK and is responsible for providing marketing insights and recommendations
     based on the research findings provided by the Deep Research Agent. It analyzes the research findings, identifies key trends,
     and offers marketing strategies that effectively communicate the key messages to the target audience.
     The agent also collaborates with the marketing team to ensure that the strategies proposed are actionable and aligned with the overall marketing goals,
     while also being adaptable and able to evolve based on new research
     insights and the ongoing market dynamics."""


     def __init__(self, agent_name:str, description: str, instructions: str):
          init_api_key()
          super().__init__(
               agent_name=agent_name,
               description=description,
               content_types=['text', 'text/plain']
          )
          logger.info(f"Initializing Agent with name: {agent_name}")


          self.instructions = instructions
          self.agent = None

     async def init_agent(self):
          """Initialize the agent with the necessary tools and configurations."""
          logger.info("Initializing Content Strategist Agent metadata...")
          config = get_mcp_server_config()
          logger.info(f'MCP url={config.url}')
          tools = await MCPToolset(
               connection_params = SseServerParams(url=config.url)
          ).get_tools()

          for tool in tools:
               logger.info(f"Tool Loaded: {tool.name}")
          generate_content_config = genai_types.GenerateContentConfig(
               max_output_tokens=2048,
               temperature=0.0,
          )
          LITELLM_MODEL = os.getenv("LITELLM_MODEL", "gemini-3.1-flash-lite")
          self.agent = Agent(
               name=self.agent_name,
               instruction=self.instructions,
               model=LiteLlm(model=LITELLM_MODEL),
               tools=tools,
               disallow_transfer_to_parent=True,
               disallow_transfer_to_peers=True,
               generate_content_config=generate_content_config,
          )
          self.runner = AgentRunner()

     async def invoke(self, query, session_id) -> dict:
          logger.info(f'Running {self.agent_name} for session {session_id} for query: \n{query}')

          raise NotImplementedError("The invoke method is not implemented. Please use the streaming function.")


     async def stream(self, query, context_id, task_id) ->AsyncIterable[dict[str, Any]]:
          """Stream the response from the agent as it is generated."""
          logger.info(
               f'Running {self.agent_name} in streaming mode for session {context_id} and task {task_id} \nfor query: \t{query}'
          )
          if not query:
               logger.error("No query provided to the agent.")
               raise ValueError("Query cannot be empty.")

          if not self.agent:
               await self.init_agent()
          async for chunk in self.runner.run_stream(agent=self.agent, query=query, session_id=context_id):
               logger.info(f"Received chunk from agent: {chunk}")
               if isinstance(chunk, dict) and chunk.get('type') == 'final_result':
                    response = chunk.get('response')
                    logger.info(f"Final result received from agent: {response}")
                    yield self.get_agent_response(response)
               else:
                    yield {
                         'is_task_complete': False,
                         'require_user_input': False,
                         'content': f'{self.agent_name} is processing the request...'
                    }

     def format_response(self, chunk):
          """Format the response from the agent to ensure it is consistent and can be easily parsed by the client."""
          patterns = [
               r'```\n(.*?)\n```',
               r'```json\s*(.*?)\s*```',
               r'```tool_outputs\s*(.*?)\s*```',
          ]

          for pattern in patterns:
               match = re.search(pattern, chunk, re.DOTALL)
               if match:
                    content = match.group(1)
                    try:
                         return json.loads(content)
                    except json.JSONDecodeError as e:
                         logger.error(f"JSON decoding error: {e}")
                         return content
          return chunk

     def get_agent_response(self, chunk):
          logger.info(f'Response Type: {type(chunk)}')
          data = self.format_response(chunk)
          logger.info(f'Formatted agent response: {data}')
          try:
               if isinstance(data,dict):
                    if 'status' in data and data['status'] == 'input_required':
                         return {
                              'response_type': 'text',
                              'is_task_complete': False,
                              'require_user_input': True,
                              'content': data['question']
                         }
                    return {
                         'response_type': 'data',
                         'is_task_complete': True,
                         'require_user_input': False,
                         'content': data
                    }
               return_type = 'data'
               try:
                    data = json.loads(data)
                    return_type = 'data'
               except Exception as json_e:
                    logger.error(f'Json parsing error: {json_e}. Returning raw text response.')
                    return_type = 'text'
               return {
                    'response_type': return_type,
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': data
               }
          except Exception as e:
               logger.error(f"Error in processing agent response: {e}. Returning raw response.")
               return {
                    'response_type': 'text',
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': 'Could not complete task due to an error in processing the agent response. Please try again'
               }