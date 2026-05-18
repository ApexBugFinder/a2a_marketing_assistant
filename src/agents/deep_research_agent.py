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

logger = logging.getLogger(__name__)


class DeepResearchAgent(BaseAgent):
     """Deep Research Agentn"""

     init_api_key()
     def __init__(self):
          super().__init__()
          logger.info("Initializing Deep Research Agent")

          self.agent_runner = AgentRunner(agent=self.build_agent(), agent_name="Deep Research Agent")
     def build_agent(self) -> Agent:
          """Build the Deep Research Agent with the necessary tools and configuration."""
          logger.info("Building Deep Research Agent")

          # Initialize the LiteLlm with the appropriate model and parameters
          llm = LiteLlm(model="gpt-4o", temperature=0.7, max_tokens=2048)

          # Initialize the MCPToolset with the necessary tools for web research and information retrieval
          toolset = MCPToolset(tools=[
               # Add tools for web search, information retrieval, and data analysis here
               # For example:
               # WebSearchTool(),
               # PineconeSearchTool(),
               # ConversationHistoryAnalysisTool(),
          ])

          # Get MCP server configuration for handling tool interactions
          mcp_server_config = get_mcp_server_config()

          # Create and return the Agent with the specified LLM, toolset, and MCP server configuration
          agent = Agent(llm=llm, toolset=toolset, mcp_server_params=SseServerParams(**mcp_server_config))
          return agent