"""Config"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv(override=True)

@dataclass
class PineconeConfig:
     """Pinecone configuration parameters."""
     api_key: str = os.getenv("PINECONE_API_KEY")
     environment: str = os.getenv("PINECONE_ENVIRONMENT")
     index_name: str = os.getenv("PINECONE_INDEX_NAME")
     namespace: str = os.getenv("PINECONE_NAMESPACE")
     embedding_model: str = os.getenv("EMBEDDING_MODEL")
     embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS"))
     batch_size: int = int(os.getenv("PINECONE_BATCH_SIZE", 100))  # Default to 100 if not set
     def __repr__(self):
          return f"""
          PINECONE_API_KEY: {'set' if self.api_key else 'not set'}
          PINECONE_ENVIRONMENT: {self.environment}
          PINECONE_INDEX_NAME: {self.index_name}
          PINECONE_NAMESPACE: {self.namespace}
          PINECONE_EMBEDDING_MODEL: {self.embedding_model}
          PINECONE_EMBEDDING_DIMENSIONS: {self.embedding_dimensions}
          PINECONE_BATCH_SIZE: {self.batch_size}
          """
