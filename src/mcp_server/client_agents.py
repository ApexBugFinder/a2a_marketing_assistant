# type:ignore
import asyncio
import json
import logging
import os

from contextlib import asynccontextmanager

import click
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, ReadResourceResult

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging(log_file: str | None = None) -> None:
     fmt = logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
     root = logging.getLogger()
     root.setLevel(logging.INFO)

     console = logging.StreamHandler()
     console.setFormatter(fmt)
     root.addHandler(console)

     if log_file:
          os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)
          file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
          file_handler.setFormatter(fmt)
          root.addHandler(file_handler)
          logger.info(f'Logging to file: {log_file}')

env = {
    'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
}

# Each entry: (expected card name, query that should match it)
EXPECTED_AGENTS = [
     ('Aspectuator Agent',             'Break down a research topic into key aspects and sub-queries'),
     ('Content Strategist Agent',      'Develop a comprehensive content strategy from research findings'),
     ('Deep Research Agent',           'Conduct comprehensive web research and analysis on a topic'),
     ('Image Generation Agent',        'Generate a custom image from a text description'),
     ('LinkedIn Post Generator Agent', 'Create an engaging LinkedIn post about AI trends'),
     ('Marketing Assistant Agent',     'Manage a full marketing campaign for a product launch'),
     ('Orchestrator Agent',            'Orchestrate and coordinate task execution across multiple agents'),
     ('Planner Agent',        'Break down a complex request into actionable tasks'),
     ('SEO Blog Writer Agent',         'Write an SEO-optimized blog post on the latest AI trends'),
]


EXPECTED_TOOLS = [
     'pinecone_scrape_and_push_tool',
     'pinecone_retriever_tool',
     'create_tables_tool',
     'postgres_async_runner_tool',
     'postgres_sync_runner_tool',
     'serpapi_main_topic_search_tool',
     'serpapi_key_aspect_search_tool',
     'image_generation_tool',
     'save_to_s3_tool',
     'post_to_linkedin_tool',
     'edit_linkedin_post_tool',
     'delete_linkedin_post_tool',
     'blog_preview_tool',
     'clear_blog_preview_tool',
     'publish_blog_post_tool',
     'start_all_docker_containers_tool',
     'start_docker_container_tool',
     'restart_docker_container_tool',
     'stop_docker_container_tool',
]


@asynccontextmanager
async def init_session(host, port, transport, path='/mcp'):
     """Initializes and manages an MCP ClientSession based on the specified transport.

     Args:
          host: The hostname or IP address of the MCP server.
          port: The port number of the MCP server.
          transport: The communication transport ('streamable-http', 'sse', or 'stdio').
          path: URL path the MCP server is mounted at (default '/mcp').

     Yields:
          ClientSession: An initialized and ready-to-use MCP client session.
     """
     if transport == 'streamable-http':
          url = f'http://{host}:{port}{path}'
          async with streamable_http_client(url) as (read_stream, write_stream, _):
               async with ClientSession(
                    read_stream=read_stream, write_stream=write_stream
               ) as session:
                    logger.debug('Streamable-HTTP ClientSession created, initializing...')
                    await session.initialize()
                    logger.info('Streamable-HTTP ClientSession initialized successfully.')
                    yield session
     elif transport == 'sse':
          url = f'http://{host}:{port}{path}'
          async with sse_client(url) as (read_stream, write_stream):
               async with ClientSession(
                    read_stream=read_stream, write_stream=write_stream
               ) as session:
                    logger.debug('SSE ClientSession created, initializing...')
                    await session.initialize()
                    logger.info('SSE ClientSession initialized successfully.')
                    yield session
     elif transport == 'stdio':
          if not os.getenv('GOOGLE_API_KEY'):
               logger.error('GOOGLE_API_KEY is not set')
               raise ValueError('GOOGLE_API_KEY is not set')
          stdio_params = StdioServerParameters(
               command='uv',
               args=['run', 'a2a-mcp'],
               env=env,
          )
          async with stdio_client(stdio_params) as (read_stream, write_stream):
               async with ClientSession(
                    read_stream=read_stream,
                    write_stream=write_stream,
               ) as session:
                    logger.debug('STDIO ClientSession created, initializing...')
                    await session.initialize()
                    logger.info('STDIO ClientSession initialized successfully.')
                    yield session
     else:
          logger.error(f'Unsupported transport type: {transport}')
          raise ValueError(
               f"Unsupported transport type: {transport}. Must be 'sse', 'stdio', or 'streamable-http'."
          )


async def find_agent(session: ClientSession, query: str) -> CallToolResult:
     """Calls the 'find_agent' tool on the connected MCP server."""
     logger.info(f"Calling 'find_agent' tool with query: '{query[:60]}...'")
     return await session.call_tool(
          name='find_agent',
          arguments={'query': query},

     )


async def find_resource(session: ClientSession, resource: str) -> ReadResourceResult:
     """Reads a resource from the connected MCP server."""
     logger.info(f'Reading resource: {resource}')
     return await session.read_resource(resource)


async def test_agents_present(session: ClientSession) -> bool:
     """Verifies all expected agents are registered on the server.

     Reads the agent card list resource and checks each expected agent
     has a corresponding registered URI.

     Returns:
          True if all expected agents are present, False otherwise.
     """
     logger.info('--- Test: agents present ---')
     result = await find_resource(session, 'resource://agent_cards/list')
     data = json.loads(result.contents[0].text)
     registered_uris: list[str] = data.get('agent_cards', [])
     logger.info(f'Server reports {len(registered_uris)} registered agent(s).')

     # Map expected names to expected URI stems (e.g. "Deep Research Agent" → "deep_research_agent")
     all_present = True
     for name, _ in EXPECTED_AGENTS:
          expected_stem = name.lower().replace(' ', '_')
          expected_uri = f'resource://agent_cards/{expected_stem}'
          if expected_uri in registered_uris:
               logger.info(f'  PASS  {name}')
          else:
               logger.error(f'  FAIL  {name!r} not found (expected URI: {expected_uri})')
               logger.debug(f'        Registered URIs: {registered_uris}')
               all_present = False

     return all_present


async def test_agents_callable(session: ClientSession) -> bool:
     """Verifies each agent is reachable via the find_agent embedding search.

     For each expected agent, issues a natural language query that should
     semantically match that agent and checks the returned card's name.

     Returns:
          True if every query returns the expected agent, False otherwise.
     """
     logger.info('--- Test: agents callable ---')
     all_callable = True
     for expected_name, query in EXPECTED_AGENTS:
          result = await find_agent(session, query)
          if not result.content:
               logger.error(f'  FAIL  {expected_name!r}: tool returned empty content')
               all_callable = False
               continue
          logger.debug(f'  raw result: {result.content[0]}')
          card = json.loads(result.content[0].text)
          actual_name = card.get('name', '<no name>')
          if actual_name == expected_name:
               logger.info(f'  PASS  {expected_name}')
          else:
               logger.warning(
                    f'  WARN  query for {expected_name!r} returned {actual_name!r} '
                    f'(may indicate overlapping embeddings)'
               )
               all_callable = False

     return all_callable


async def test_tools_present(session: ClientSession) -> bool:
     """Verifies all expected tools are registered on the tools MCP server.

     Returns:
          True if all expected tools are present, False otherwise.
     """
     logger.info('--- Test: tools present ---')
     result = await session.list_tools()
     registered_names = {t.name for t in result.tools}
     logger.info(f'Server reports {len(registered_names)} registered tool(s).')

     all_present = True
     for name in EXPECTED_TOOLS:
          if name in registered_names:
               logger.info(f'  PASS  {name}')
          else:
               logger.error(f'  FAIL  {name!r} not found on server')
               all_present = False

     return all_present


async def list_tools(session: ClientSession) -> bool:
     """Lists all tools registered on the connected MCP server."""
     logger.info('--- Tools list ---')
     result = await session.list_tools()
     if not result.tools:
          logger.warning('  No tools found on this server.')
          return False
     for t in result.tools:
          logger.info(f'  {t.name}: {t.description or ""}')
     logger.info(f'--- {len(result.tools)} tool(s) total ---')
     return True


async def main(host, port, transport, path, query, resource, tool, run_tests, list_tools_flag):
     """Main async entry point — connects to the MCP server and dispatches commands."""
     logger.info('Starting MCP client...')
     async with init_session(host, port, transport, path) as session:
          if list_tools_flag:
               await list_tools(session)

          if run_tests:
               overall = True
               if path.startswith('/tools'):
                    overall = await test_tools_present(session)
               elif path.startswith('/agents'):
                    present = await test_agents_present(session)
                    callable_ = await test_agents_callable(session)
                    overall = present and callable_
               else:
                    logger.warning(f'--test requires --path /tools/mcp or --path /agents/mcp; got {path!r}')
               status = 'ALL PASSED' if overall else 'SOME FAILED'
               logger.info(f'--- Test results: {status} ---')

          if query:
               result = await find_agent(session, query)
               data = json.loads(result.content[0].text)
               logger.info(json.dumps(data, indent=2))

          if resource:
               result = await find_resource(session, resource)
               data = json.loads(result.contents[0].text)
               logger.info(json.dumps(data, indent=2))


@click.command()
@click.option('--host',      default='localhost',       help='MCP server host')
@click.option('--port',      default='8000',            help='MCP server port')
@click.option('--transport', default='streamable-http', help='MCP transport (streamable-http, sse, stdio)')
@click.option('--path',      default='/tools/mcp',      help='URL path the MCP server is mounted at')
@click.option('--find_agent', 'query',    default=None, help='Natural language query to find an agent (agents MCP only)')
@click.option('--resource',               default=None, help='URI of the resource to read')
@click.option('--tool',                   default=None, help='Tool name to execute')
@click.option('--list-tools', 'list_tools_flag', is_flag=True, default=False, help='List all tools on the server')
@click.option('--test', 'run_tests', is_flag=True, default=False, help='Run agent presence and callability tests (agents MCP only)')
@click.option('--log-file', 'log_file', default=None, help='Path to write log output (appends; directory created if needed)')
def cli(host, port, transport, path, query, resource, tool, list_tools_flag, run_tests, log_file):
        """Command-line client for the Marketing Assistant MCP servers."""
        setup_logging(log_file)
        asyncio.run(main(host, port, transport, path, query, resource, tool, run_tests, list_tools_flag))


if __name__ == '__main__':
    cli()