"""Convenience methods to start servers."""

import click

from mcp import server_agents
from mcp import app



@click.command()
@click.option('--run', 'command', default='mcp-server', help='Command to run')
@click.option(
     '--host',
     'host',
     default='localhost',
     help='Host on which the server is started or the client connects to',
)
@click.option(
     '--port',
     'port',
     default=10100,
     help='Port on which the server is started or the client connects to',
)
@click.option(
     '--transport',
     'transport',
     default='stdio',
     help='MCP Transport',
)
def main(command, host, port, transport) -> None:
     # TODO: Add other servers, perhaps dynamic port allocation
     if command == 'mcp-server':
          # run agents server
          server_agents.serve(host, port, transport)
          # run python3 app.py to start the API server
          app.run()





     else:
          raise ValueError(f'Unknown run option: {command}')