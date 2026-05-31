from typing import Optional
import uuid
class ResearchFinding:
     def __init__(self, id, research_project_id, title=None, pub_date=None, source=None, url=None, research_cycle_count:Optional[int]=None):
          self.id = uuid.uuid4() if id is None else id
          self.research_project_id = research_project_id
          self.source = source
          self.pub_date = pub_date
          self.title = title
          self.url = url
          self.research_cycle_count = research_cycle_count

     def __repr__(self):
          return f"<ResearchFinding(id={self.id}, research_project_id={self.research_project_id}, title='{self.title}', pub_date='{self.pub_date}', source='{self.source}', url='{self.url}', research_cycle_count={self.research_cycle_count})>"


