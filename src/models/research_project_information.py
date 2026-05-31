import uuid
from common.types import DeliverableStatus

from pydantic import Field, BaseModel

class ReportInfoMetadata(BaseModel):
     report_name: str = Field(..., description="the name of the research report")
     report_tiny_url: str = Field(..., description="the URL where the research report can be accessed")
     report_long_url: str = Field(..., description="the long URL where the research report can be accessed on S3")
     created_at: str = Field(..., description="date report was created")
     updated_at: str = Field(..., description="date report was last updated")
     ai_score: float = Field(..., description="a score that represents the quality and comprehensiveness of the research report based on the research objectives and the research framework")
     ai_feedback: str = Field(..., description="feedback on the research report based on the research objectives and the research framework")
     user_feedback: str = Field(..., description="feedback from the user on the research report")
     user_approved: bool = Field(..., description="a boolean value that indicates whether the user has approved the research report")
     status: DeliverableStatus = Field(default=DeliverableStatus(status='not_started'), description="Current status of the research report in its lifecycle")


class SummaryInfoMetadata(BaseModel):
     summary_name: str = Field(..., description="the name of the research summary")
     summary_tiny_url: str = Field(..., description="the URL where the research summary can be accessed")
     summary_long_url: str = Field(..., description="the long URL where the research summary can be accessed on S3")
     created_at: str = Field(..., description="date summary was created")
     updated_at: str = Field(..., description="date summary was last updated")
     ai_score: float = Field(..., description="a score that represents the quality and comprehensiveness of the research summary based on the research objectives and the research framework")
     ai_feedback: str = Field(..., description="feedback on the research summary based on the research objectives and the research framework")
     user_feedback: str = Field(..., description="feedback from the user on the research summary")
     user_approved: bool = Field(..., description="a boolean value that indicates whether the user has approved the research summary")
     status: DeliverableStatus = Field(default=DeliverableStatus(status='not_started'), description="Current status of the research summary in its lifecycle")

class ResearchProjectInformation:
     def __init__(self, id, research_project_id, research_topic, research_overview, research_objectives, research_scope, research_framework, research_cycle_count=0, bottom_count=0, report_info: ReportInfoMetadata, summary_info: SummaryInfoMetadata):
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
          return f"<ResearchProjectInformation(id={self.id}, research_project_id={self.research_project_id}, research_topic='{self.research_topic}', research_overview='{self.research_overview}', research_objectives='{self.research_objectives}', research_scope='{self.research_scope}', research_framework='{self.research_framework}', research_cycle_count={self.research_cycle_count}, bottom_count={self.bottom_count}, report_info='{self.report_info}', summary_info='{self.summary_info}')>"