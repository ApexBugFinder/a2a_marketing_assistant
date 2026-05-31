import boto3
import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import pdfkit
import os
from dotenv import load_dotenv
load_dotenv()
import asyncio



class DocumentSaveToS3Args(BaseModel):
     document: str = Field(description="The content of the document to be saved as a PDF.")
     filename: str = Field(description="The filename to save the PDF as.")
     object_key: str = Field(description="The S3 object key (including folder path) to save the PDF under.")

class ResearchTools:
     def __init__(self):
          self.temp_dir = os.getenv("TEMP_DIR", "temp")
          self.s3_bucket_name = os.getenv("S3_BUCKET_NAME")
          self.s3_region_name = os.getenv("S3_REGION_NAME")
          self.save_pdf_to_s3_tool = StructuredTool.from_function(
               coroutine=self._save_pdf_to_s3,
               name="Save PDF to S3 Tool",
               description="""A tool to save a PDF document to an S3 bucket.""",
               args_schema=DocumentSaveToS3Args,
               response_format='content'
          )


     async def _save_pdf_to_s3(self, document: str , filename: str, object_key: str) -> dict:
          """Saves a PDF  to an S3 bucket."""
          s3_object_key = f'{object_key}/{filename}'
          try:
               pdf_path = os.path.join(self.temp_dir, filename)
               pdfkit.from_string(document, pdf_path)
               s3_client = boto3.client('s3')
               await asyncio.to_thread(s3_client.upload_file, pdf_path, self.s3_bucket_name, s3_object_key)
               long_url = self._create_long_url(s3_object_key)
               tiny_url = await self._get_tiny_url(long_url)
               os.remove(pdf_path)
               return {
                    "long_url": long_url,
                    "tiny_url": tiny_url,
                    "metadata": {
                         "s3_bucket_name": self.s3_bucket_name,
                         "s3_object_key": s3_object_key
                    }
               }
          except Exception as e:
               return { "error": f"Failed to save PDF: {str(e)}" }

     def _create_long_url(self, object_key: str) -> str:
          """Creates a long URL for an object stored in an S3 bucket."""
          return f"https://{self.s3_bucket_name}.s3.{self.s3_region_name}.amazonaws.com/{object_key}"

     async def _get_tiny_url(self, long_url: str) -> str:
          """Gets a tiny URL for a given long URL using the TinyURL API."""
          api_url = f"http://tinyurl.com/api-create.php?url={long_url}"
          async with httpx.AsyncClient() as client:
               response = await client.get(api_url)
               if response.status_code == 200:
                    return response.text.strip()
               else:
                    raise Exception(f"Failed to get tiny URL: {response.status_code} - {response.text}")