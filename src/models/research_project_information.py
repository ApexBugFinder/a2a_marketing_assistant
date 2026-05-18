import uuid

class ResearchProjectInformation:
     def __init__(self, id, research_project_id, research_topic, research_overview, research_objectives, research_scope, research_framework):
          self.id = id or str(uuid.uuid4())
          self.research_project_id = research_project_id
          self.research_topic = research_topic
          self.research_overview = research_overview
          self.research_objectives = research_objectives
          self.research_scope = research_scope
          self.research_framework = research_framework
     def __repr__(self):
          return f"<ResearchProjectInformation(id={self.id}, research_id={self.research_id}, research_topic='{self.research_topic}', research_overview='{self.research_overview}', research_objectives='{self.research_objectives}', research_scope='{self.research_scope}', research_framework='{self.research_framework}')>"