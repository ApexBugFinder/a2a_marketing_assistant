import asyncio
import os
from datetime import datetime, timezone
from io import BytesIO

import boto3
import dotenv
import httpx
from PIL import Image
from google import genai
from google.genai import types as genai_types
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from models.marketing_images import MarketingImage, MarketingImageMetadata

dotenv.load_dotenv()


class ImageGenerationArgs(BaseModel):
    description: str = Field(description="Text description of the image to generate.")


class ImageSaveToS3Args(BaseModel):
    image_data: bytes = Field(description="The binary data of the image to be saved.")
    filename: str = Field(description="The filename to save the image as.")


class ImageGenerationTools:
    def __init__(self):
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        self.s3_region_name = os.getenv("S3_REGION_NAME")
        self.gemini_image_model = os.getenv("GEMINI_IMAGE_GENERATION_MODEL")
        self._genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        self.image_generation_tool = StructuredTool.from_function(
            coroutine=self.generate_image,
            name="Image Generation Tool",
            description="Generates an image from a text description using the Gemini image generation model. Returns the image as bytes along with its dimensions and size.",
            args_schema=ImageGenerationArgs,
            response_format="content",
        )
        self.save_to_s3_bucket_tool = StructuredTool.from_function(
            coroutine=self.save_image_to_s3,
            name="Save to S3 Tool",
            description="Saves image bytes to S3 and returns the long_url, tiny_url, and image metadata (size_bytes, img_dimensions, saved_to_s3_at).",
            args_schema=ImageSaveToS3Args,
            response_format="content",
        )

    def create_long_url(self, object_key: str) -> str:
        return f"https://{self.s3_bucket_name}.s3.{self.s3_region_name}.amazonaws.com/{object_key}"

    async def generate_image(self, description: str) -> dict:
        """Generates an image from a text description using the Gemini image generation model."""
        try:
            response = await asyncio.to_thread(
                self._genai_client.models.generate_content,
                model=self.gemini_image_model,
                location='us-west1',    
                contents=description,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    image = Image.open(BytesIO(image_bytes))
                    width, height = image.size
                    return {
                        "image_data": image_bytes,
                        "size_bytes": len(image_bytes),
                        "img_dimensions": f"{width}x{height}",
                    }
            return {"error": "No image data returned by the model."}
        except Exception as e:
            return {"error": f"Image generation failed: {str(e)}"}

    async def save_image_to_s3(self, image_data: bytes, filename: str) -> dict:
        """Saves image bytes to S3. Returns long_url, tiny_url, and image metadata."""
        s3_object_key = f"images/{filename}"
        try:
            image = Image.open(BytesIO(image_data))
            width, height = image.size
            size_bytes = len(image_data)

            buffer = BytesIO()
            image.save(buffer, format=image.format or "PNG")
            buffer.seek(0)

            s3_client = boto3.client("s3")
            await asyncio.to_thread(
                s3_client.upload_fileobj, buffer, self.s3_bucket_name, s3_object_key
            )

            long_url = self.create_long_url(s3_object_key)
            tiny_url = await self.get_tiny_url(long_url)
            saved_to_s3_at = datetime.now(timezone.utc)

            return {
                "long_url": long_url,
                "tiny_url": tiny_url,
                "size_bytes": size_bytes,
                "img_dimensions": f"{width}x{height}",
                "saved_to_s3_at": saved_to_s3_at.isoformat(),
                "metadata": {
                    "s3_bucket_name": self.s3_bucket_name,
                    "s3_object_key": s3_object_key,
                },
            }
        except Exception as e:
            return {"error": f"Failed to save image to S3: {str(e)}"}

    async def get_tiny_url(self, image_url: str) -> str:
        """Generates a tiny URL for a given long URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://tinyurl.com/api-create.php?url={image_url}"
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            return f"Failed to generate tiny URL: {str(e)}"
