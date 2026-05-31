import uuid
from common.types import DeliverableStatus
from pydantic import BaseModel, Field


class LinkedInPostMetadata(BaseModel):
     posted: bool = Field(default=False, description="Whether the post has been published to LinkedIn")
     post_removed: bool = Field(default=False, description="Whether the post has been removed from LinkedIn")
     post_removed_at: int | None = Field(default=None, description="Unix timestamp when the post was removed")
     ai_score: float | None = Field(default=None, description="AI quality/engagement score for the post")
     ai_feedback: str | None = Field(default=None, description="AI-generated feedback on the post content")
     user_feedback: str | None = Field(default=None, description="Feedback provided by the user on this post")
     posted_at: int | None = Field(default=None, description="Unix timestamp when the post was published")
     updated_at: int | None = Field(default=None, description="Unix timestamp of the last update")
     status: DeliverableStatus = Field(default=DeliverableStatus(status='not_started'), description="Current status of the post in its lifecycle")


class LinkedInPost(BaseModel):
     id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this post record")
     author_urn: str = Field(..., description="LinkedIn URN of the post author")
     text: str = Field(..., description="Text content of the LinkedIn post")
     hashtags: list[str] = Field(default_factory=list, description="Hashtags included in the post")
     image_url: str | None = Field(default=None, description="URL of the image attached to the post")
     linkedin_post_id: str | None = Field(default=None, description="LinkedIn's own post ID, set after publishing")
     scheduled_time: int | None = Field(default=None, description="Unix timestamp for scheduled publishing; None means publish immediately")
     research_project_id: str | None = Field(default=None, description="ID of the associated research project")
     metadata: LinkedInPostMetadata = Field(default_factory=LinkedInPostMetadata, description="Post lifecycle metadata: posting status, timestamps, AI and user feedback")
