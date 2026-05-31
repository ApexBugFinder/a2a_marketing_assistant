import os
from contextlib import asynccontextmanager, AsyncExitStack
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from google import genai
from tools.blog_writer_tools import (BlogNameArg,
                                   BlogPostArgs,
                                   ClearBlogPreviewArgs,
                                   PublishBlogPostArgs
                                   )
from tools.image_generation_tools import ImageGenerationArgs, ImageSaveToS3Args
from tools.linkedin_poster_tool import LinkedInEditPostArgs, LinkedInPostArgs, LinkedInRemovePostArgs
from tools.pinecone_pusher_tool import PineconePusherTool, ScrapeAndPushArgs
from tools.pinecone_retriever import _PineconeRetrieverQueryInput
from tools.postgres_tools import QueryParams
from tools.ser_papi_toolo import FormattedSerpapiWebSearchResults, _QueryInput, SerpapiInput
load_dotenv()
from mcp_server import server_api
from mcp_server.server_agents import build_agent_card_embeddings
from mcp_server.server_api import mcp as tools_mcp
from fastmcp import FastMCP

# --- Build FastMCP ASGI apps BEFORE defining the lifespan ---
# Both require their own lifespan to be started; we forward it via the combined lifespan below.

tools_mcp_asgi = tools_mcp.http_app(transport='streamable-http')

# Agents MCP: find_agent tool + agent card resources
agents_mcp = FastMCP('Marketing Assistant Agent Cards Server')
df = None

@agents_mcp.tool(name='find_agent', description='Finds the most relevant agent card based on a natural language query')
def find_agent(query: str) -> str:
     import json
     import os
     import numpy as np
     from common.utils import init_api_key
     client = genai.Client()
     embedding_model = os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001')
     query_embedding = client.models.embed_content(model=embedding_model, contents=query).embeddings[0].values
     best = int(np.argmax(np.dot(np.stack(df['card_embeddings']), query_embedding)))
     return json.dumps(df.iloc[best]['agent_card'])

@agents_mcp.resource('resource://agent_cards/list', mime_type='application/json')
def get_agent_cards():
     return {'agent_cards': df['card_uri'].to_list()}

@agents_mcp.resource('resource://agent_cards/{card_name}', mime_type='application/json')
def get_agent_card(card_name: str):
     return {'agent_card': df.loc[df['card_uri'] == f'resource://agent_cards/{card_name}', 'agent_card'].to_list()}

agents_mcp_asgi = agents_mcp.http_app(transport='streamable-http')


@asynccontextmanager
async def lifespan(_app: FastAPI):
     global df
     # Forward both FastMCP sub-app lifespans so their session managers are initialized
     async with AsyncExitStack() as stack:
          await stack.enter_async_context(tools_mcp_asgi.router.lifespan_context(_app))
          await stack.enter_async_context(agents_mcp_asgi.router.lifespan_context(_app))
          try:
               df = build_agent_card_embeddings()
               if df is None:
                    logger.warning("Agent card embeddings could not be built; find_agent will be unavailable.")
          except Exception as e:
               logger.error(f"Failed to build agent card embeddings at startup: {e}")
          yield


_version = "1.0.0"
app = FastAPI(
     title='Marketing Assistant Tools API',
     description="""API for tools used by the Marketing Assistant Agent, including web search, database management,
     and information retrieval tools.""",
     version=_version,
     lifespan=lifespan,
     redirect_slashes=False,
)
app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],
     allow_methods=["*"],
     allow_headers=["*"],
     expose_headers=["mcp-session-id", "last-event-id"],
)

# Tools MCP → MCP clients connect to /tools/mcp
app.mount('/tools', tools_mcp_asgi)
# Agents MCP → MCP clients connect to /agents/mcp
app.mount('/agents', agents_mcp_asgi)


# PINECONE TOOLS
@app.post("/pinecone/pinecone_scrape_and_push")
async def pinecone_scrape_and_push_tool(request: ScrapeAndPushArgs):
     """A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database."""
     return await server_api.pinecone_scrape_and_push_tool(result_dict=request.result_dict)

@app.post("/pinecone/prep_data_for_pinecone")
def prep_data_for_pinecone_tool(results: list[FormattedSerpapiWebSearchResults]):
     """Converts a list of Formatted SerpAPI Web Search Results into the input format expected by pinecone_scrape_and_push_tool."""
     return PineconePusherTool.prep_data_for_pinecone(results).model_dump()

@app.post("/pinecone/pinecone_retriever")
async def pinecone_retriever_tool(request: _PineconeRetrieverQueryInput):
     """A tool to retrieve relevant information from the Pinecone vector database related to the research topic."""
     return await server_api.pinecone_retriever_tool(query=request.query)

# POSTGRES TOOLS
@app.post("/postgres/create_id")
def create_id_tool():
     """A tool to create a unique UUID4 string ID."""
     return server_api.create_id_tool()

@app.post("/postgres/create_tables")
async def create_tables_tool():
     """A tool to create the necessary tables in the PostgreSQL database, if the tables do not exist."""
     return await server_api.create_tables_tool()

@app.post("/postgres/postgres_async_runner")
async def postgres_async_runner_tool(request: QueryParams):
     """A tool to run a SQL query against the PostgreSQL database asynchronously and return the results."""
     return await server_api.postgres_async_runner_tool(query=request.query, params=request.params, fetch=request.fetch)

@app.post("/postgres/postgres_sync_runner")
def postgres_sync_runner_tool(request: QueryParams):
     """A tool to run a SQL query against the PostgreSQL database synchronously and return the results."""
     return server_api.postgres_sync_runner_tool(query=request.query, params=request.params, fetch=request.fetch)

# SERPAPI TOOLS
@app.post("/serpapi/serpapi_main_topic_search")
def serpapi_main_topic_search_tool(request: SerpapiInput):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to the research topic."""
     return server_api.serpapi_main_topic_search_tool(query=request.query, research_project_id=request.research_project_id)

@app.post("/serpapi/serpapi_key_aspect_search")
def serpapi_key_aspect_search_tool(request: SerpapiInput):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic."""
     return server_api.serpapi_key_aspect_search_tool(query=request.query, research_project_id=request.research_project_id)

# IMAGE GENERATION TOOLS
@app.post("/image_generation/generate_image")
async def image_generation_tool(request: ImageGenerationArgs) -> dict:
     """A tool to generate an image from a text description using the Gemini image generation model."""
     return await server_api.image_generation_tool(description=request.description)

@app.post("/image_generation/save_to_s3")
async def save_to_s3_tool(request: ImageSaveToS3Args) -> dict:
     """A tool to save image bytes to an S3 bucket and return the long_url, tiny_url, and image metadata."""
     return await server_api.save_to_s3_tool(image_data=request.image_data, filename=request.filename)

# LINKEDIN TOOLS
@app.post("/linkedin/post_to_linkedin")
async def post_to_linkedin_tool(request: LinkedInPostArgs) -> dict:
     """A tool to post content to LinkedIn using the LinkedIn API."""
     return await server_api.post_to_linkedin_tool(author_urn=request.author_urn, text=request.text, hashtags=request.hashtags, image_url=request.image_url)

@app.post("/linkedin/edit_linkedin_post")
async def edit_linkedin_post_tool(request: LinkedInEditPostArgs) -> dict:
     """A tool to edit an existing LinkedIn post using the LinkedIn API."""
     return await server_api.edit_linkedin_post_tool(linkedin_post_id=request.linkedin_post_id, text=request.text, hashtags=request.hashtags)

@app.post("/linkedin/delete_linkedin_post")
async def delete_linkedin_post_tool(request: LinkedInRemovePostArgs) -> dict:
     """A tool to delete an existing LinkedIn post using the LinkedIn API."""
     return await server_api.delete_linkedin_post_tool(linkedin_post_id=request.linkedin_post_id)

# BLOG WRITER TOOLS
@app.post("/blog_writer/blog_preview")
async def blog_preview_tool(request: BlogPostArgs) -> dict:
     """A tool to generate a preview of the blog post content based on the provided title and content."""
     return await server_api.blog_preview_tool(request=request)

@app.post("/blog_writer/clear_blog_preview")
async def clear_blog_preview_tool(request: ClearBlogPreviewArgs) -> dict:
     """A tool to clear the blog post preview content."""
     return await server_api.clear_blog_preview_tool(research_project_id=request.research_project_id)

@app.post("/blog_writer/publish_blog_post")
async def publish_blog_post_tool(request: PublishBlogPostArgs) -> dict:
     """A tool to publish a blog post by Docker and returns an object with the URL, title and blog_content."""
     return await server_api.publish_blog_post_tool(request=request)

@app.post("/blog_writer/start_all_docker_containers")
def start_all_docker_containers_tool() -> dict:
     """A tool to start all Docker containers for previously published blog posts."""
     return server_api.start_all_docker_containers_tool()

@app.post("/blog_writer/start_docker_container")
def start_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to start a Docker container for a published blog post by its blog name."""
     return server_api.start_docker_container_tool(request=request)

@app.post("/blog_writer/restart_docker_container")
def restart_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to restart a Docker container for a published blog post by its blog name."""
     return server_api.restart_docker_container_tool(request=request)

@app.post("/blog_writer/stop_docker_container")
def stop_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to stop and remove a Docker container for a published blog post by its blog name."""
     return server_api.stop_docker_container_tool(request=request)

# ── Blog preview serving ────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles

# Mount the blog_preview directory so the frontend can load /blog_preview/output.html
_blog_preview_dir = os.path.dirname(os.path.join(
     os.getenv("BLOG_POST_PREVIEW_FILE_PATH", "blog_preview/output.html")
))
if not os.path.isdir(_blog_preview_dir):
     os.makedirs(_blog_preview_dir, exist_ok=True)
app.mount("/blog_preview", StaticFiles(directory=_blog_preview_dir, html=True), name="blog_preview")

@app.get("/")
async def root():
     return {
          "message": "Welcome to the Marketing Assistant Tools API.",
          "version": _version,
          "mcp_endpoints": {
               "/tools/mcp": "Tools MCP server (Pinecone, Postgres, SerpAPI, LinkedIn, Blog, Images)",
               "/agents/mcp": "Agents MCP server (find_agent, agent card resources)",
          },
          "rest_endpoints": {
               "/serpapi/serpapi_main_topic_search": "Web search for a research topic",
               "/serpapi/serpapi_key_aspect_search": "Web search for a key aspect",
               "/postgres/create_id": "Create a unique UUID4 string ID",
               "/postgres/create_tables": "Create PostgreSQL tables",
               "/postgres/postgres_async_runner": "Run async SQL query",
               "/postgres/postgres_sync_runner": "Run sync SQL query",
               "/pinecone/pinecone_scrape_and_push": "Scrape links and push to Pinecone",
               "/pinecone/pinecone_retriever": "Retrieve from Pinecone vector store",
               "/image_generation/generate_image": "Generate an image from a text description",
               "/image_generation/save_to_s3": "Save image bytes to S3 and return URLs",
               "/linkedin/post_to_linkedin": "Post content to LinkedIn",
               "/linkedin/edit_linkedin_post": "Edit an existing LinkedIn post",
               "/linkedin/delete_linkedin_post": "Delete a LinkedIn post by ID",
               "/blog_writer/blog_preview": "Preview blog post content as HTML",
               "/blog_writer/clear_blog_preview": "Clear the blog post preview",
               "/blog_writer/publish_blog_post": "Publish a blog post via Docker",
               "/blog_writer/start_all_docker_containers": "Start all blog Docker containers",
               "/blog_writer/start_docker_container": "Start a blog Docker container by name",
               "/blog_writer/restart_docker_container": "Restart a blog Docker container by name",
               "/blog_writer/stop_docker_container": "Stop and remove a blog Docker container by name",
               "/blog_preview/output.html": "Serve the current blog preview HTML",
          }
     }

if __name__ == "__main__":
     import uvicorn
     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
