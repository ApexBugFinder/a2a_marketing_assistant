import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MarketingImageMetadata(BaseModel):
    created_at: datetime | None = Field(default=None, description="Timestamp when the image generation request was initiated")
    saved_to_s3_at: datetime | None = Field(default=None, description="Timestamp when the image was successfully uploaded to S3")
    size_bytes: int | None = Field(default=None, description="Size of the image file in bytes")
    img_dimensions: str | None = Field(default=None, description="Image dimensions as a string, e.g. '1024x1024'")
    updated_at: datetime | None = Field(default=None, description="Timestamp of the last update to this image record")


class MarketingImage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this image record")
    research_project_id: str = Field(..., description="ID of the associated research project")
    image_url: str = Field(..., description="The long S3 URL where the image is stored")
    tiny_url: str | None = Field(default=None, description="The shortened URL for the image")
    description: str | None = Field(default=None, description="The text description used to generate the image")
    metadata: MarketingImageMetadata = Field(default_factory=MarketingImageMetadata, description="Image lifecycle metadata: timestamps, file size, and dimensions")
