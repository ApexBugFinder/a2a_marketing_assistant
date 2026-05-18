from pinecone import Pinecone, ServerlessSpec

from src.config.pinecone_config import PineconeConfig


class PineconeClient():
     def __init__(self):
          self.pinecone_config = PineconeConfig()
          self.pinecone_api_key = self.pinecone_config.api_key
          self.pinecone_environment = self.pinecone_config.environment

          self.client = Pinecone(api_key=self.pinecone_api_key, environment=self.pinecone_environment)
          self.pc = Pinecone(api_key=self.pinecone_api_key, environment=self.pinecone_environment)
          self.serverless_index = self.pc.Index(self.pinecone_config.index_name)
