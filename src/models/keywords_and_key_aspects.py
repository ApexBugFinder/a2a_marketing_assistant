from ast import List
import uuid
from typing import Literal
from pydantic import BaseModel, Field
import datetime
class KeywordOrKeyAspect(BaseModel):
    research_project_id: uuid.UUID = Field(..., description="Research project ID")
    id: uuid.UUID | None = Field(default_factory=None, description="ID of the keywords and key aspects")
    keyword_or_key_aspect: List[str] = Field(..., description="List of keywords and key aspects")
    research_cycle_count: int = Field(default_factory=1, description="Count of the research cycle")
    created_at: int = Field(..., description="Timestamp when the keywords or key aspects were created")
    updated_at: int = Field(..., description="Timestamp when the keywords or key aspects was last updated")

    def to_db_dict(self):
        return {
            "research_project_id": self.research_project_id,
            "id": self.id,
            "keyword_or_key_aspect": self.keyword_or_key_aspect,
            "research_cycle_count": self.research_cycle_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
