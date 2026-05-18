import os
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.tools import StructuredTool
from langsmith import traceable
from langchain_classic.tools.retriever import create_retriever_tool
from config.pinecone_config import Config as PineconeConfig
from utils.vector_store.pinecone import PineconeClient
from pydantic import BaseModel, Field

class _QueryInput(BaseModel):
     query: str = Field (description="The search query to retrieve relevant information")

class PineconeRetrieverTool:
     def __init__(self):
          self.pinecone_config = PineconeConfig()
          self.create_vector_store()
          self.create_retriever()
          self.create_retriever_tool()
          self.retrieve_deep_research_information_tool = StructuredTool.from_function(
               func=self._retrieve_research_information,
               name="Retrieve Deep Research Information Tool",
               description="""A tool to retrieve relevant information from the
               vector store related to the research topic.
               """,
               args_schema=_QueryInput,
               response_format='content_and_artifact')



     def create_vector_store(self):
          pinecone = PineconeClient()
          serverless_name = pinecone.client.Index(self.pinecone_config.index_name )
          self.vector_store = PineconeVectorStore(
                                                  index=serverless_name,
                                                  embedding=OpenAIEmbeddings(model=self.pinecone_config.embedding_model, openai_api_key=os.getenv("OPENAI_API_KEY")),)


     def create_retriever(self):
          self.deep_research_retriever = self.vector_store.as_retriever(search_type='similarity',
                                                                      search_kwargs={"k": 20, 'namespace': self.pinecone_config.namespace})

     def create_retriever_tool(self):
          self.retriever_tool = create_retriever_tool(
               retriever=self.deep_research_retriever,
               input_schema=_QueryInput,
               name="Deep Research Retriever Tool",
               description="""A tool to retrieve relevant information from the vector store based on a search query related to the research topic.
               The tool takes a search query as input and returns relevant information, data, facts, statistics, and insights that are stored in the vector database.
               This tool is used to gather information that can help in understanding the research topic better and provide context for further web research.""",
               response_format='content_and_artifact'
               )

     @traceable(run_type='retriever')
     def _retrieve_research_information(self, query: str):
          """Useful for retrieving relevant information from the vector store based on a search query"""
          retrieved_docs = self.deep_research_retriever.invoke(query)
          serialized = "\n\n".join(
               (f"Source: {doc.metadata}\nContent: {doc.page_content}")
               for doc in retrieved_docs
               )
          return serialized, retrieved_docs