import logging
import os

import google.generativeai as genai
from common.types import ServerConfig

logger = logging.getLogger(__name__)

def init_api_key():
     """Initialize the API key for the generative AI model."""

     if not os.getenv("GOOGLE_API_KEY"):
          logger.error("GOOGLE_API_KEY environment variable is not set.")
          raise EnvironmentError("GOOGLE_API_KEY environment variable is not set.")
     genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

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

def get_mcp_server_config() -> ServerConfig:
     """Get the server configuration for the MCP server."""
     return ServerConfig(
          host=os.getenv("MCP_SERVER_HOST", "localhost"),
          port=int(os.getenv("MCP_SERVER_PORT", 10101)),
          transport=os.getenv("MCP_SERVER_TRANSPORT", "http")
     )