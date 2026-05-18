import asyncio
import os
import uuid

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.tools import StructuredTool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import PineconeAsyncio
from pinecone.exceptions import PineconeException
from pydantic import BaseModel, Field

from src.config.pinecone_config import PineconeConfig
from src.utils.vector_store.pinecone import PineconeClient


class LinkMetadata(BaseModel):
     title: str
     author: str
     date: str
     source: str


class ScrapeAndPushArgs(BaseModel):
     result_dict: dict[str, LinkMetadata] = Field(
          description="Mapping of URL to its metadata (title, author, date, source) for each link to scrape and index."
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

     async def scrape_and_push(self, result_dict: dict[str, LinkMetadata]) -> str:
          """A tool to scrape the content of the provided links and push the relevant information to the Pinecone vector database."""
          records = []
          number_of_links = len(result_dict)
          for link, meta in result_dict.items():
               try:
                    chunks = self.scrape(link)
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

          await self.push_to_pinecone(records)

          return f'Scrape and push to Pinecone completed successfully for {number_of_links} links.  Created {len(records)} records in the vector database.'


     def scrape(self, link: str) :
          """A tool to scrape the content of the provided link."""
          try:
               loader = WebBaseLoader(link)
               documents = loader.load()
               text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
               chunks = text_splitter.split_documents(documents)
               return chunks
          except Exception as e:
               print(f"Error scraping site  {link} or splitting  documents: {e}")
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
                         await asyncio.gather(*(idx.upsert(vectors=batch) for batch in batches))
          except PineconeException as e:
               print(f"Error pushing to Pinecone: {e}")