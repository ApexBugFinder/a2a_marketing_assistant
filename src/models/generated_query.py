from typing import Literal

from pydantic import BaseModel, Field
import uuid
class GeneratedQuery(BaseModel):
     id: uuid | None = Field(default_factory=None, description="Unique identifier for the generated query")
     research_project_id: uuid | None = Field(default_factory=None, description="Unique identifier for the research project")
     generated_query: str = Field(..., description="The search query that was generated")
     research_cycle_count: int = Field(default_factory=lambda: 0, description="The number of research cycles this query has gone through")
     framework_category: str = Field(..., description="The Research Framework category this query belongs to")
     status: Literal["candidate", "verified", "searched"] = Field(default_factory=lambda: "candidate", description="The status of the generated query")
     created_at: int = Field(..., description="Timestamp when the query was created")
     updated_at: int = Field(..., description="Timestamp when the query was last updated")