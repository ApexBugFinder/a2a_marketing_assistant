import json
import logging
import re

from collections.abc import AsyncIterable
from typing import Any
from google.genai import types
from common.agent_runner import AgentRunner
from common.base_agent import BaseAgent
from common.utils import get_tools_mcp_config, init_api_key
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.genai import types as genai_types
import os
from langsmith import traceable
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
          logger.info("Initializing Marketing Assistant Agent metadata...")
          config = get_tools_mcp_config()
          url = f'http://{config.host}:{config.port}{config.path}'
          logger.info(f'MCP url={url}')
          try:
               tools = await MCPToolset(
                    connection_params=StreamableHTTPServerParams(url=url)
               ).get_tools()
          except Exception as e:
               logger.error(
                    f"[{self.agent_name}] Failed to connect to MCP tools server at {url}. "
                    f"Ensure 'poetry run python -m mcp_server' is running. Error: {type(e).__name__}: {e}",
                    exc_info=True,
               )
               raise RuntimeError(
                    f"{self.agent_name}: MCP tools server unreachable at {url} — {type(e).__name__}: {e}"
               ) from e

          for tool in tools:
               logger.info(f"Tool Loaded: {tool.name}")

          generate_content_config = genai_types.GenerateContentConfig(
               max_output_tokens=10048,
              
               temperature=0.0,
               safety_settings = [types.SafetySetting(
                              category="HARM_CATEGORY_HATE_SPEECH",
                              threshold="BLOCK_ONLY_HIGH"
                         ),types.SafetySetting(
                              category="HARM_CATEGORY_DANGEROUS_CONTENT",
                              threshold="BLOCK_ONLY_HIGH"
                         ),types.SafetySetting(
                              category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                              threshold="BLOCK_ONLY_HIGH"
                         ),types.SafetySetting(
                              category="HARM_CATEGORY_HARASSMENT",
                              threshold="BLOCK_ONLY_HIGH"
                         )])
          sql_dir = os.getenv("SQL_DIR", "")
          if not sql_dir:
               logger.warning(f"[{self.agent_name}] SQL_DIR env var is not set; SQL library paths in instructions will be empty.")
          # Replace all template variables the ADK would otherwise treat as missing context variables.
          self.instructions = (
               self.instructions
               .replace("{SQL_DIR}", sql_dir)
               .replace("{CONVERSATION_HISTORY}", "the current conversation context")
               .replace("{keyword}", "KEYWORD")
               .replace("{topic}", "TOPIC")
          )
          if self.agent_name == 'MarketingAssistantAgent':
               LITELLM_MODEL = os.getenv("LITE_LLM_AGENT")

          elif self.agent_name == 'ContentStrategistAgent':
               LITELLM_MODEL = os.getenv("LITE_LLM_AGENT",)

          elif self.agent_name == 'DeepResearchAgent':
               LITELLM_MODEL = os.getenv("LITE_LLM_AGENT")

          elif self.agent_name == 'AspectuatorAgent':
               LITELLM_MODEL = os.getenv("LITE_LLM_AGENT")

          else:
               LITELLM_MODEL = os.getenv("LITE_LLM_AGENT")

          # # Force LiteLLM to route through Google AI Studio (generativelanguage.googleapis.com)
          # # rather than Vertex AI (aiplatform.googleapis.com). Without this prefix, LiteLLM
          # # picks up the gcloud Application Default Credentials and routes to Vertex AI, which
          # # blocks API-key auth with 403 PERMISSION_DENIED.
          # if '/' not in LITELLM_MODEL:
          #      LITELLM_MODEL = f'gemini/{LITELLM_MODEL}'

          self.agent = Agent(
               name=self.agent_name,
               instruction=self.instructions,
               model=LITELLM_MODEL,
               tools=tools,
               disallow_transfer_to_parent=True,
               disallow_transfer_to_peers=True,
               generate_content_config=generate_content_config,
          )
          self.runner = AgentRunner()

     async def invoke(self, query, session_id) -> dict:
          logger.info(f'Running {self.agent_name} for session {session_id} for query: \n{query}')

          raise NotImplementedError("The invoke method is not implemented. Please use the streaming function.")

     @traceable(name='agent')
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
               if not isinstance(chunk, dict):
                    yield {'is_task_complete': False, 'require_user_input': False,
                           'content': f'{self.agent_name} is processing...'}
                    continue
               chunk_type = chunk.get('type')
               if chunk_type == 'final_result':
                    response = chunk.get('response')
                    logger.info(f"Final result received from agent: {response}")
                    yield self.get_agent_response(response)
               elif chunk_type == 'streaming_text':
                    # Intermediate text turn — forward directly so the user sees
                    # agent status messages, questions, and progress updates.
                    text = chunk.get('response', '')
                    logger.info(f"[{self.agent_name}] streaming text ({len(text)} chars)")
                    yield {
                         'is_task_complete': False,
                         'require_user_input': False,
                         'content': text,
                    }
               else:
                    yield {
                         'is_task_complete': False,
                         'require_user_input': False,
                         'content': f'{self.agent_name} is processing...'
                    }

     def format_response(self, chunk):
          """Format the response from the agent to ensure it is consistent and can be easily parsed by the client."""
          if not isinstance(chunk, str):
               return chunk
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
               if not data or not (isinstance(data, str) and data.strip()):
                    logger.warning(f'{self.agent_name} returned an empty response.')
                    return {
                         'response_type': 'text',
                         'is_task_complete': False,
                         'require_user_input': False,
                         'content': f'{self.agent_name} is processing the request...',
                    }
               return_type = 'data'
               try:
                    data = json.loads(data)
                    return_type = 'data'
               except Exception as json_e:
                    logger.debug(f'Response is not JSON ({json_e}). Returning as raw text.')
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