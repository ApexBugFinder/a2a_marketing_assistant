"""Deprecated — use src.mcp_server.model_schemas.{ReportInfoMetadata, SummaryInfoMetadata, ResearchProjectInformation} instead.

This module is kept for reference only. The canonical Pydantic models live in
src/mcp_server/model_schemas.py and are registered in PYDANTIC_SCHEMAS for use
with get_pydantic_schema_tool.
"""

import uuid

from pydantic import Field, BaseModel

from mcp_server.model_schemas import ReportReviewCriteria, DeliverableStatusEnum


class ReportInfoMetadata(BaseModel):
    """Metadata for the research report deliverable."""
    report_name: str = Field(..., description="The name of the research report.")
    report_tiny_url: str = Field(..., description="Shortened URL where the report can be accessed.")
    report_long_url: str = Field(..., description="The long S3 URL where the report can be accessed.")
    content: str | None = Field(
        default=None,
        description="The full HTML content of the deliverable. Stored here so the user can pull "
                    "and view it directly from the site without querying blog_content separately.",
    )
    created_at: str = Field(..., description="ISO timestamp when the report was created.")
    updated_at: str = Field(..., description="ISO timestamp when the report was last updated.")
    review_criteria: ReportReviewCriteria = Field(
        default_factory=ReportReviewCriteria,
        description="AI and user review state for the report deliverable.",
    )


class SummaryInfoMetadata(BaseModel):
    """Metadata for the research summary deliverable."""
    summary_name: str = Field(..., description="The name of the research summary.")
    summary_tiny_url: str = Field(..., description="Shortened URL where the summary can be accessed.")
    summary_long_url: str = Field(..., description="The long S3 URL where the summary can be accessed.")
    content: str | None = Field(
        default=None,
        description="The full HTML content of the deliverable. Stored here so the user can pull "
                    "and view it directly from the site without querying blog_content separately.",
    )
    created_at: str = Field(..., description="ISO timestamp when the summary was created.")
    updated_at: str = Field(..., description="ISO timestamp when the summary was last updated.")
    review_criteria: ReportReviewCriteria = Field(
        default_factory=ReportReviewCriteria,
        description="AI and user review state for the summary deliverable.",
    )


class ResearchProjectInformation:
    """Non-Pydantic research project info wrapper. Prefer the Pydantic model in model_schemas.py."""
    def __init__(self, id, research_project_id, research_topic, research_overview,
                 research_objectives, research_scope, research_framework,
                 research_cycle_count=0, bottom_count=0,
                 report_info: ReportInfoMetadata = None,
                 summary_info: SummaryInfoMetadata = None):
        self.id = id or str(uuid.uuid4())
        self.research_project_id = research_project_id
        self.research_topic = research_topic
        self.research_overview = research_overview
        self.research_objectives = research_objectives
        self.research_scope = research_scope
        self.research_framework = research_framework
        self.research_cycle_count: int = research_cycle_count
        self.bottom_count: int = bottom_count
        self.report_info = report_info
        self.summary_info = summary_info

    def __repr__(self):
        return (
            f"<ResearchProjectInformation(id={self.id}, research_project_id={self.research_project_id}, "
            f"research_topic='{self.research_topic}', research_overview='{self.research_overview}', "
            f"research_objectives='{self.research_objectives}', research_scope='{self.research_scope}', "
            f"research_framework='{self.research_framework}', research_cycle_count={self.research_cycle_count}, "
            f"bottom_count={self.bottom_count}, report_info='{self.report_info}', "
            f"summary_info='{self.summary_info}')>"
        )
