from fastmcp import FastMCP
from src.tools.pinecone_retriever import PineconeRetrieverTool
from tools.pinecone_pusher_tool import PineconePusherTool
from src.tools.postgres_tools import PostgresTools
from src.tools.ser_papi_toolo import SerpApiTool

mcp = FastMCP('Marketing Assistant Server')

# PINECONE TOOLS
@mcp.tool()
def pinecone_scrape_and_push_tool(result_dict: dict[str, str]):
     """A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database."""
     return PineconePusherTool().scrape_and_push_tool(result_dict)


@mcp.tool()
def pinecone_retriever_tool(query: str):
     """A tool to retrieve relevant information from the
               vector store related to the research topic.
               """
     return PineconeRetrieverTool().retrieve_deep_research_information_tool(query)


# POSTGRES TOOLS
@mcp.tool()
def create_tables_tool():
     """A tool to create the necessary tables in the PostgreSQL database, if the tables do not exist."""
     return PostgresTools().create_tables_tool()


@mcp.tool()
async def postgres_async_runner_tool(query: str, params=None, fetch: bool = True):

     """A tool to run a SQL query against the PostgreSQL database asynchronously and return the results."""
     return await PostgresTools()._run_query_async(query, params=params, fetch=fetch)


@mcp.tool()
def postgres_sync_runner_tool(query: str, params=None, fetch: bool = True):
     """A tool to run a SQL query against the PostgreSQL database synchronously and return the results."""
     return PostgresTools()._run_query_sync(query, params=params, fetch=fetch)


# SERPAPI TOOLS
@mcp.tool()
def serpapi_main_topic_search_tool(query: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to the research topic."""
     return SerpApiTool().serpapi_main_topic_search(query)

@mcp.tool()
def serpapi_key_aspect_search_tool(query: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic."""
     return SerpApiTool().serpapi_key_aspect_search(query)


#
if __name__ == "__main__":
     print('Starting MCP Server...')
     mcp.run(transport='streamable-http', host='0.0.0.0', port=8020)