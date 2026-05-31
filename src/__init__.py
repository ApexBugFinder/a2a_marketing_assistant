# """Convenience methods to start servers."""

# from dotenv import load_dotenv
# load_dotenv()

# import click

# from mcp_server.server_agents import serve
# from mcp_server import app



# @click.command()
# @click.option('--run', 'command', default='mcp-server', help='Command to run')
# @click.option(
#      '--host',
#      'host',
#      default='localhost',
#      help='Host on which the server is started or the client connects to',
# )
# @click.option(
#      '--port',
#      'port',
#      default=10100,
#      help='Port on which the server is started or the client connects to',
# )
# @click.option(
#      '--transport',
#      'transport',
#      default='stdio',
#      help='MCP Transport',
# )
# def main(command, host, port, transport) -> None:
#      # TODO: Add other servers, perhaps dynamic port allocation
#      if command == 'mcp-server':
#           # run agents server
#           serve(host, port, transport)
#           # run python3 app.py to start the API server
#           app.run()





     # else:
     #      raise ValueError(f'Unknown run option: {command}')