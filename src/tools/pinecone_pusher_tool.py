import asyncio
import os
import uuid
from langsmith import traceable
import requests
from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import PineconeAsyncio
from pinecone.exceptions import PineconeException
from langchain_community.document_loaders import WebBaseLoader
from tools.ser_papi_toolo import FormattedSerpapiWebSearchResults

from src.config.pinecone_config import PineconeConfig
from src.utils.vector_store.pinecone import PineconeClient


class LinkMetadata(BaseModel):
     title: str
     author: str
     date: str
     source: str

class PineconeMetadata(BaseModel):
     source: str | None = Field(description="The source of the information, e.g the 'New York Times', 'TechCrunch', etc.")
     link: str | None = Field(description="The URL of the information source.")
     title: str | None = Field(description="The title of the information, article, paper, etc.")
     text: str | None = Field(description="The main text content of the information.")
     publication_date: str | None = Field(description="The publication date of the information.")
     author: str | None = Field(description="The author of the information.")
class PineconeRecord(BaseModel):
     id: str

     metadata: PineconeMetadata

class ScrapeAndPushArgs(BaseModel):
     result_dict: dict[str, LinkMetadata] = Field(
          description="Mapping of 'link' to its metadata (title, author, date, source) for each link to scrape and index."
     )

class PineconePusherTool:
     def __init__(self):
          self.pinecone_config = PineconeConfig()
          self.pinecone = PineconeClient()
          self.embeddings = OpenAIEmbeddings(model=self.pinecone_config.embedding_model, openai_api_key=os.getenv("OPENAI_API_KEY"))
          self.scrape_and_push_tool = StructuredTool.from_function(
               coroutine=self.scrape_and_push,
               name="Scrape and Push to Pinecone Tool",
               description="""A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database.""",
               args_schema=ScrapeAndPushArgs,
               response_format='content'
               )

     @traceable(run_type='tool')
     async def scrape_and_push(self, result_dict: dict[str, LinkMetadata]) -> str:
          """A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database."""
          records = []
          number_of_links = len(result_dict)
          for link, meta in result_dict.items():
               try:
                    chunks = await asyncio.wait_for(
                         asyncio.to_thread(self.scrape, link),
                         timeout=20.0,
                    )
                    texts = [chunk.page_content for chunk in chunks]
                    embeddings = self.embeddings.embed_documents(texts)
                    for text, embedding in zip(texts, embeddings):
                         record = {
                              "id": str(uuid.uuid4()),
                              "values": embedding,
                              "metadata": {
                                   "source": meta.source,
                                   "link": link,
                                   "title": meta.title,
                                   "text": text,
                                   "publication_date": meta.date,
                                   "author": meta.author,
                              },
                         }
                         records.append(record)
               except Exception as e:
                    print(f"Error processing {link}: {e}")
          try:
               await self.push_to_pinecone(records)
          except Exception as e:
               print(f"Error pushing to Pinecone: {e}")
               return f"Error pushing to Pinecone: {e}"
          return f"Successfully processed and pushed {len(records)} records from {number_of_links} links to Pinecone."


     def scrape(self, link: str, timeout: int = 15):
          """Scrape the content of the provided link with a per-request timeout."""
          try:
               session = requests.Session()
               session.request = lambda method, url, **kwargs: requests.Session.request(
                    session, method, url, timeout=timeout, **kwargs
               )
               loader = WebBaseLoader(link)
               loader.session = session
               documents = loader.load()
               text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
               chunks = text_splitter.split_documents(documents)
               return chunks
          except Exception as e:
               print(f"Error scraping site {link} or splitting documents: {e}")
               return []


     async def push_to_pinecone(self, records: list[dict]):
          """Batch and push records to Pinecone concurrently using the async client."""
          if not records:
               return
          batch_size = self.pinecone_config.batch_size
          batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]
          try:
               async with PineconeAsyncio(api_key=self.pinecone_config.api_key) as pc:
                    description = await pc.describe_index(name=self.pinecone_config.index_name)
                    async with pc.IndexAsyncio(host=description.host) as idx:
                         await asyncio.gather(*(idx.upsert(vectors=batch, namespace=self.pinecone_config.namespace) for batch in batches))
          except PineconeException as e:
               print(f"Error pushing to Pinecone: {e}")
          return records

     def prep_data_for_pinecone(results: list) -> ScrapeAndPushArgs:
          """Convert a list of FormattedSerpapiWebSearchResults into ScrapeAndPushArgs for scrape_and_push_tool."""
          converted: dict[str, LinkMetadata] = {
               record.link: LinkMetadata(
                    title=record.title or '',
                    author='',
                    date=record.date or '',
                    source=record.source or '',
               )
               for record in results
               if hasattr(record, 'link') and isinstance(record.link, str) and record.link.startswith('http')
          }
          return ScrapeAndPushArgs(result_dict=converted)