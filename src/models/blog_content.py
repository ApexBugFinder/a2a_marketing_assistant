# Class to manage blog content creation and scheduling based on research findings and content strategy
import uuid
from pydantic import BaseModel, Field
from common.types import DeliverableStatus
class BlogContentMetadata(BaseModel):
     ai_score: float | None = Field(default=None, description="AI quality/engagement score for the blog content")
     ai_feedback: str | None = Field(default=None, description="AI-generated feedback on the blog content")
     user_feedback: str | None = Field(default=None, description="Feedback provided by the user on the blog content")
     created_at: int | None = Field(default=None, description="Unix timestamp when the blog content was created")
     updated_at: int | None = Field(default=None, description="Unix timestamp of the last update to the blog content")
     output_folder: str | None = Field(default=None, description="The output folder where the blog content files are stored")
     port: int | None = Field(default=None, description="The port number where the blog post is hosted after publishing")
     blog_name: str | None = Field(default=None, description="The name of the blog post, used for the URL and Docker container name when published")
     status:   DeliverableStatus = Field(default=DeliverableStatus(status='not_started'), description="Current status of the blog content in its lifecycle")
     long_url: str | None = Field(default=None, description="The long URL where the blog content can be accessed on S3")
     tiny_url: str | None = Field(default=None, description="The tiny URL where the blog content can be accessed, typically generated after publishing the blog post and hosting it on a server or platform that provides URL shortening services")

class BlogContent(BaseModel):
     id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this blog content record")
     research_project_id: str = Field(..., description="ID of the associated research project")
     title: str = Field(..., description="Title of the blog post")
     content: str = Field(..., description="Main content of the blog post, which should be well-structured and formatted for readability and engagement")
     seo_keywords: list[str] = Field(default_factory=list, description="List of SEO keywords that are relevant to the blog content and should be incorporated into the content to optimize it for search engines")
     publication_date: int | None = Field(default=None, description="Unix timestamp representing the scheduled publication date and time for the blog post; if None, the blog post is not scheduled for publication yet")
     keywords_and_key_aspects: list[str] = Field(default_factory=list, description="List of keywords and key aspects related to the research topic that should be highlighted in the blog content to effectively communicate the key messages derived from the research findings and align with the overall content strategy")
     metadata: BlogContentMetadata = Field(default_factory=BlogContentMetadata, description="Metadata for the blog content, including AI and user feedback, timestamps, status, URLs, and other relevant information about the lifecycle of the blog content")
