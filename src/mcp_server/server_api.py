from fastmcp import FastMCP
from tools.blog_writer_tools import (
     BlogNameArg,
     BlogPostArgs,
     BlogWriterTools,
     ClearBlogPreviewArgs,
     PublishBlogPostArgs
     )
from tools.linkedin_poster_tool import LinkedInPosterTools
from tools.pinecone_pusher_tool import LinkMetadata, PineconePusherTool
from tools.pinecone_retriever import PineconeRetrieverTool
from tools.postgres_tools import PostgresTools
from tools.ser_papi_toolo import FormattedSerpapiWebSearchResults, SerpApiTools  # noqa: F401
from tools.image_generation_tools import ImageGenerationTools
from mcp_server.model_schemas import (
    build_cheatsheet,
    get_model_schema,
    get_pydantic_schema,
    list_model_names,
    list_pydantic_model_names,
    PineconeResults,
    PineconeRetrievedDocument,
)
from dotenv import load_dotenv
import base64
import uuid
import os
load_dotenv()
USER_AGENT=os.getenv('USER_AGENT')
mcp = FastMCP('Marketing Assistant Tools Server')





# SUPPORTING  TOOLS
# PINECONE TOOLS
@mcp.tool()
async def pinecone_scrape_and_push_tool(urls: list[str]):
     """Scrape the provided URLs and push the content to the Pinecone vector database.
     Pass a plain list of URL strings extracted from the SerpAPI results' `link` field.
     Example: ["https://example.com/article-1", "https://example.com/article-2"]"""
     converted: dict[str, LinkMetadata] = {
          url: LinkMetadata(title='', author='', date='', source=url)
          for url in urls
          if isinstance(url, str) and url.startswith('http')
     }
     return await PineconePusherTool().scrape_and_push(result_dict=converted)


@mcp.tool()
def pinecone_retriever_tool(query: str):
     """A tool to retrieve relevant information from the
               vector store related to the research topic.
               """
     return PineconeRetrieverTool()._retrieve_research_information(query)


@mcp.tool()
def pinecone_retrieve_serialized_tool(query: str) -> dict:
     """Retrieve relevant research information from the Pinecone vector store
     and return it as a **single serialized string**.

     All matching document chunks are joined into one block with the format:
         Source: {metadata}
         Content: {page_content}

     per document, separated by double newlines.

     Use this when you need a compact, human-readable summary of the retrieved
     context (e.g. to inject into a prompt or display to a user).

     Returns a dict with:
       - serialized: the joined string of all documents
       - retrieved_docs: None (not populated in this variant)
     """
     result = PineconeRetrieverTool().retrieve_research_information_serialized(query)
     return PineconeResults(
         serialized=result.serialized,
         retrieved_docs=None,
     ).model_dump()


@mcp.tool()
def pinecone_retrieve_documents_tool(query: str) -> dict:
     """Retrieve relevant research information from the Pinecone vector store
     and return it as a **list of structured document objects**.

     Each document object contains:
       - page_content: the text content of the chunk
       - metadata: dict with source URL, title, chunk index, etc.

     Use this when you need to programmatically iterate over individual
     documents, inspect per-document metadata, or filter/rank results.

     Returns a dict with:
       - serialized: None (not populated in this variant)
       - retrieved_docs: list of {page_content, metadata} objects
     """
     result = PineconeRetrieverTool().retrieve_research_information_documents(query)
     docs = [
         PineconeRetrievedDocument.from_langchain_document(doc)
         for doc in (result.retrieved_docs or [])
     ]
     return PineconeResults(
         serialized=None,
         retrieved_docs=docs,
     ).model_dump()


@mcp.tool()
def prep_data_for_pinecone_tool(results: list[FormattedSerpapiWebSearchResults]) -> dict:
     """Converts a list of Formatted SerpAPI Web Search Results into the input format expected
     by pinecone_scrape_and_push_tool. Pass the output of this tool directly to
     pinecone_scrape_and_push_tool as the urls list (extract the 'result_dict' keys).
     Filters out any results whose link does not start with 'http'."""
     return PineconePusherTool.prep_data_for_pinecone(results).model_dump()


# POSTGRES TOOLS
@mcp.tool()
def create_id_tool() -> uuid.UUID:
     """A tool to create a unique UUID4 string ID."""
     return uuid.uuid4()

@mcp.tool()
def create_multiple_uuid_tool(num: int) -> list[str]:
     """Create multiple UUID4s at once. Pass `num` (positive integer) to get
     that many UUID strings back. Useful when batch-inserting records that each
     need their own ID — avoids calling create_id_tool in a loop."""
     if num < 1:
          return []
     return [str(uuid.uuid4()) for _ in range(num)]

@mcp.tool()
def get_model_schema_tool(model_name: str) -> dict:
     """Return the full database schema, field descriptions, and parameter-by-parameter
     SQL templates for a given model. Call this BEFORE running any SQL against a table
     to ensure you use the correct column names, parameter order, and data types.

     Pass one of the available model names:
     research_project, research_project_information, formatted_research_findings,
     generated_query, content_strategy, blog_content, linkedin_post,
     linkedin_account, marketing_image.

     The response includes:
     - fields: list of {name, type, pg_type, description} for every column
     - sql: dict of SQL operation → [query_template, param_docs] for read/insert/update/delete
     - table_name: the fully-qualified PostgreSQL table name
     - primary_key: the primary key column name

     Use the exact SQL template strings returned — copy-paste them as the `query` argument
     to postgres_async_runner_tool. Do NOT pass file paths as queries."""
     return get_model_schema(model_name)

@mcp.tool()
def list_database_models_tool() -> list[str]:
     """List all available database model names that can be passed to get_model_schema_tool."""
     return list_model_names()


@mcp.tool()
def get_pydantic_schema_tool(model_name: str) -> dict:
     """Return the complete Pydantic model JSON schema, field list, and descriptions
     for a given model name. Call this to understand the expected data shapes before
     constructing tool arguments or parsing agent responses.

     Pass one of the available model names:
     ResearchProject, BlogContent, LinkedInPost, MarketingImage, ContentStrategy,
     PlannerResponseFormat, AgentResponse, DeepResearchReport, GeneratedQuery,
     KeywordsAndKeyAspects, WorkflowGraphSchema, PineconeResults, PineconeRetrievedDocument, and many more.

     The response includes:
     - json_schema: the full JSON Schema (https://json-schema.org) for the model
     - fields: list of {name, type, required, description} for every field

     Use this to validate or construct data that will be passed between agents and tools."""
     return get_pydantic_schema(model_name)


@mcp.tool()
def list_pydantic_models_tool() -> list[str]:
     """List all available Pydantic model names that can be passed to get_pydantic_schema_tool."""
     return list_pydantic_model_names()


@mcp.tool()
async def create_tables_tool():
     """A tool to create the necessary tables in the PostgreSQL database, if the tables do not exist."""
     return await PostgresTools().create_tables()


_SQL_KEYWORDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "WITH", "TRUNCATE"}

def _validate_sql(query: str) -> str | None:
     """Return an error string if query does not look like SQL, else None."""
     first_word = query.strip().split()[0].upper() if query.strip() else ""
     if first_word not in _SQL_KEYWORDS:
          return (
               f"Invalid query: the 'query' parameter must be a SQL statement "
               f"(e.g. SELECT, INSERT, UPDATE, DELETE). Received: {query[:120]!r}"
          )
     return None


def _normalize_params(sql_params: list) -> list:
     """Unwrap any {'value': x} dicts the LLM may produce, returning a flat list of values."""
     result = []
     for p in (sql_params or []):
          if isinstance(p, dict) and "value" in p and len(p) == 1:
               result.append(p["value"])
          else:
               result.append(p)
     return result


@mcp.tool()
async def postgres_async_runner_tool(query: str, sql_params: list = [], fetch: bool = True):
     """A tool to run a SQL query against the PostgreSQL database asynchronously and return the results.
     - query: the SQL statement to execute (SELECT, INSERT, UPDATE, DELETE, etc.) — NOT a file path.
     - sql_params: flat list of positional values bound to $1, $2, ... placeholders. Pass plain values, not dicts.
     - fetch: True to return rows, False to return the status/rowcount.
     Do NOT pass file paths, markdown, or natural language as the query."""
     if err := _validate_sql(query):
          return {"error": err}
     return await PostgresTools()._run_query_async(query, params=_normalize_params(sql_params), fetch=fetch)


@mcp.tool()
def postgres_sync_runner_tool(query: str, sql_params: list = [], fetch: bool = True):
     """A tool to run a SQL query against the PostgreSQL database synchronously and return the results.
     - query: the SQL statement to execute (SELECT, INSERT, UPDATE, DELETE, etc.) — NOT a file path.
     - sql_params: flat list of positional values bound to $1, $2, ... placeholders. Pass plain values, not dicts.
     - fetch: True to return rows, False to return the status/rowcount.
     Do NOT pass file paths, markdown, or natural language as the query."""
     if err := _validate_sql(query):
          return {"error": err}
     return PostgresTools()._run_query_sync(query, params=_normalize_params(sql_params), fetch=fetch)


# SERPAPI TOOLS
@mcp.tool()
def serpapi_main_topic_search_tool(query: str, research_project_id: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to the research topic."""
     return SerpApiTools().serpapi_main_topic_search(query, research_project_id)

@mcp.tool()
def serpapi_key_aspect_search_tool(query: str, research_project_id: str):
     """A tool to perform a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic."""
     return SerpApiTools().serpapi_key_aspect_search(query, research_project_id)

# IMAGE GENERATION TOOLS
@mcp.tool()
async def image_generation_tool(description: str) -> dict:
     """A tool to generate an image from a text description using the Gemini image generation model.
     Returns image_data (base64-encoded string), size_bytes, and img_dimensions."""
     result = await ImageGenerationTools().generate_image(description=description)
     if isinstance(result.get('image_data'), bytes):
          result['image_data'] = base64.b64encode(result['image_data']).decode('utf-8')
     return result

@mcp.tool()
async def save_to_s3_tool(image_data: str, filename: str) -> dict:
     """A tool to save an image to an S3 bucket and return the long_url, tiny_url, and image metadata.
     Pass image_data as the base64-encoded string returned by image_generation_tool."""
     raw_bytes = base64.b64decode(image_data)
     return await ImageGenerationTools().save_image_to_s3(image_data=raw_bytes, filename=filename)


# LINKEDIN TOOLS
@mcp.tool()
async def post_to_linkedin_tool(author_urn: str, text: str, hashtags: list[str] = [], image_url: str = None) -> dict:
     """A tool to post content to LinkedIn using the LinkedIn API."""
     return await LinkedInPosterTools().post_to_linkedin(author_urn=author_urn, text=text, hashtags=hashtags, image_url=image_url)

@mcp.tool()
async def edit_linkedin_post_tool(linkedin_post_id: str, text: str, hashtags: list[str] = []) -> dict:
     """A tool to edit the text content and hashtags of an existing LinkedIn post."""
     return await LinkedInPosterTools().edit_linkedin_post(linkedin_post_id=linkedin_post_id, text=text, hashtags=hashtags)

@mcp.tool()
async def delete_linkedin_post_tool(linkedin_post_id: str) -> dict:
     """A tool to delete a published LinkedIn post by its post ID."""
     return await LinkedInPosterTools().remove_linkedin_post(linkedin_post_id=linkedin_post_id)

# BLOG WRITER TOOLS
@mcp.tool()
async def blog_preview_tool(request: BlogPostArgs) -> dict:
     """A tool to generate a preview of the blog post content based on the provided title and content."""
     return await BlogWriterTools().write_blog_post_preview(blog_content=request.blog_content, title=request.title, research_project_id=request.research_project_id)

@mcp.tool()
async def clear_blog_preview_tool(request: ClearBlogPreviewArgs) -> dict:
     """A tool to clear the blog post preview content."""
     return await BlogWriterTools().clear_blog_post_preview(research_project_id=request.research_project_id)

@mcp.tool()
async def publish_blog_post_tool(request: PublishBlogPostArgs) -> dict:
     """A tool to publish a blog post by Docker and returns an object with the URL, title and blog_content."""
     return await BlogWriterTools().publish_blog_post(blog_content=request.blog_content, title=request.title,
                                                  research_project_id=request.research_project_id, port=request.port, blog_name=request.blog_name)

@mcp.tool()
def start_all_docker_containers_tool() -> dict:
     """A tool to start all Docker containers for previously published blog posts."""
     return BlogWriterTools()._start_all_docker_containers()

@mcp.tool()
def start_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to start a Docker container for a published blog post by its blog name."""
     return BlogWriterTools()._start_docker_container_sync(blog_name=request.blog_name)

@mcp.tool()
def restart_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to restart a Docker container for a published blog post by its blog name."""
     return BlogWriterTools()._restart_docker_container(blog_name=request.blog_name)

@mcp.tool()
def stop_docker_container_tool(request: BlogNameArg) -> dict:
     """A tool to stop and remove a Docker container for a published blog post by its blog name."""
     return BlogWriterTools()._stop_docker_container(blog_name=request.blog_name)


if __name__ == "__main__":


     print('Starting MCP Server...')
     mcp.run(transport='streamable-http', host='0.0.0.0', port=8020)