from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from src.tools.pinecone_pusher_tool import PineconePusherTool
from src.tools.pinecone_retriever import PineconeRetrieverTool
from src.tools.postgres_tools import PostgresTools
from src.tools.ser_papi_toolo import SerpApiTool

_version = "1.0.0"
app = FastAPI(title='Marketing Assistant Tools API',
          description="""API for tools used by the Marketing Assistant Agent, including web search, database management,
          and information retrieval tools.""",
          version=_version)

# PINECONE TOOLS
@app.post("/pinecone/pinecone_scrape_and_push")
async def pinecone_scrape_and_push_tool(result_dict: dict[str, str]):
     """A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database."""
     return await PineconePusherTool().scrape_and_push_tool(result_dict)

@app.post("/pinecone/pinecone_retriever")
async def pinecone_retriever_tool(query: str):
     """A tool to retrieve relevant information from the Pinecone vector database related to the research topic."""
     return await PineconeRetrieverTool().retrieve_tool(query)

#PoSTGRES TOOLS
@app.post("/postgres/create_tables")
async def create_tables_tool():
     """A tool to create the necessary tables in the PostgreSQL database, if the tables do not exist."""
     return await PostgresTools().create_tables()

@app.post("/postgres/postgres_async_runner")
async def postgres_async_runner_tool(query: str, params: list = None, fetch: bool = True):
     """A tool to run a SQL query against the PostgreSQL database asynchronously and return the results."""
     return await PostgresTools()._run_query_async(query, params=params, fetch=fetch)

@app.post("/postgres/postgres_sync_runner")
def postgres_sync_runner_tool(query: str, params: list = None, fetch: bool = True):
     """A tool to run a SQL query against the PostgreSQL database synchronously and return the results."""
     return PostgresTools()._run_query_sync(query, params=params, fetch=fetch)

# SERPAPI TOOLS
@app.post("/serpapi/serpapi_main_topic_search")
def serpapi_main_topic_search_tool(query: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to the research topic."""
     return SerpApiTool().serpapi_main_topic_search(query)

@app.post("/serpapi/serpapi_key_aspect_search")
def serpapi_key_aspect_search_tool(query: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic."""
     return SerpApiTool().serpapi_key_aspect_search(query)





@app.get("/")
async def root():
     return {
          "message": "Welcome to the First Agent Tools API. Use the defined endpoints to access the tools.",
          "version": _version,
          "endpoints": {
               "/serpapi/serpapi_main_topic_search": "Endpoint to perform a web search using the SerpAPI to retrieve relevant information and documents related to the research topic.",
               "/serpapi/serpapi_key_aspect_search": "Endpoint to perform a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic.",
               "/postgres/create_tables": "Endpoint to create the necessary tables in the PostgreSQL database, if the tables do not exist.",
               "/postgres/postgres_async_runner": "Endpoint to run a SQL query against the PostgreSQL database asynchronously and return the results.",
               "/postgres/postgres_sync_runner": "Endpoint to run a SQL query against the PostgreSQL database synchronously and return the results.",
               "/pinecone/pinecone_pusher": "Endpoint to scrape the content of the provided links and push the relevant information to the Pinecone vector database.",
               "/pinecone/scrape_and_push": "Endpoint to scrape the content of the provided links and push the relevant information to the Pinecone vector database.",
               "/pinecone/pinecone_retriever": "Endpoint to retrieve relevant information from the Pinecone vector database related to the research topic."}
          }

if __name__ == "__main__":
     import uvicorn
     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

