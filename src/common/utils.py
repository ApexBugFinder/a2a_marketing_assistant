import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool
from common.types import ServerConfig

logger = logging.getLogger(__name__)

def init_api_key():
     """Validate that GOOGLE_API_KEY is present; the google-genai v2 SDK reads it automatically."""
     if not os.getenv("GOOGLE_API_KEY"):
          logger.error("GOOGLE_API_KEY environment variable is not set.")
          raise EnvironmentError("GOOGLE_API_KEY environment variable is not set.")


def config_logging():
     """Configure basic logging."""
     log_level = (os.getenv("CHATBOT_A2A_LOG_LEVEL") or os.getenv('FASTMCP_LOG_LEVEL') or "INFO").upper()
     logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

def config_logger(logger):
     """Logger specific config, avoding clutter in enabling all logging."""
     logger.setLevel(getattr(logging, os.getenv("CHATBOT_A2A_LOG_LEVEL", "INFO").upper(), logging.INFO))
     console_handler = logging.StreamHandler()
     console_handler.setLevel(level=getattr(logging, os.getenv("CHATBOT_A2A_LOG_LEVEL", "INFO").upper()))

     formatter = logging.Formatter(
          '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
          )
     console_handler.setFormatter(formatter)
     logger.addHandler(console_handler)

@asynccontextmanager
async def _mcp_session(server: ServerConfig):
     """Yields an initialized ClientSession for a given ServerConfig."""
     if server.transport == 'streamable-http':
          url = f'http://{server.host}:{server.port}{server.path}'
          async with streamable_http_client(url) as (read, write, _):
               async with ClientSession(read_stream=read, write_stream=write) as session:
                    await session.initialize()
                    yield session
     elif server.transport == 'sse':
          url = f'http://{server.host}:{server.port}{server.path}'
          async with sse_client(url) as (read, write):
               async with ClientSession(read_stream=read, write_stream=write) as session:
                    await session.initialize()
                    yield session
     else:
          raise ValueError(f"Unsupported transport for tool listing: {server.transport!r}")


async def get_all_server_tools(servers: list[ServerConfig]) -> dict[str, list[Tool]]:
     """Connect to each MCP server and return all tools, keyed by 'host:port'.

     Servers that are unreachable are logged and skipped rather than raising.

     Args:
          servers: List of ServerConfig instances describing each MCP server.

     Returns:
          Dict mapping 'host:port' to the list of Tool objects from that server.
     """
     all_tools: dict[str, list[Tool]] = {}
     for server in servers:
          key = f'{server.host}:{server.port}{server.path}'
          try:
               async with _mcp_session(server) as session:
                    result = await session.list_tools()
                    all_tools[key] = result.tools
                    logger.info(f'Retrieved {len(result.tools)} tool(s) from {key}')
          except Exception as e:
               logger.error(f'Failed to get tools from {key}: {e}')
     return all_tools


def get_tools_mcp_config() -> ServerConfig:
     """Get the server configuration for the tools MCP server."""
     return ServerConfig(
          host=os.getenv("MCP_SERVER_TOOLS", "localhost"),
          port=int(os.getenv("MCP_SERVER_PORT_2", "8000")),
          transport=os.getenv("MCP_SERVER_TRANSPORT_2", "streamable-http"),
          path=os.getenv("MCP_SERVER_TOOLS_PATH", "/tools/mcp"),
     )


def get_mcp_server_config() -> ServerConfig:
     """Get the server configuration for the agents MCP server."""
     return ServerConfig(
          host=os.getenv("MCP_SERVER_AGENTS", "localhost"),
          port=int(os.getenv("MCP_SERVER_PORT", "8000")),
          transport=os.getenv("MCP_SERVER_TRANSPORT", "streamable-http"),
          path=os.getenv("MCP_SERVER_AGENTS_PATH", "/agents/mcp"),
     )


def get_all_mcp_server_configs() -> list[ServerConfig]:
     """Get the server configurations for all MCP servers."""
     return [
          ServerConfig(
               host=os.getenv("MCP_SERVER_AGENTS", "localhost"),
               port=int(os.getenv("MCP_SERVER_PORT", "8000")),
               transport=os.getenv("MCP_SERVER_TRANSPORT", "streamable-http"),
               path=os.getenv("MCP_SERVER_AGENTS_PATH", "/agents/mcp"),
          ),
          ServerConfig(
               host=os.getenv("MCP_SERVER_TOOLS", "localhost"),
               port=int(os.getenv("MCP_SERVER_PORT_2", "8000")),
               transport=os.getenv("MCP_SERVER_TRANSPORT_2", "streamable-http"),
               path=os.getenv("MCP_SERVER_TOOLS_PATH", "/tools/mcp"),
          ),
     ]