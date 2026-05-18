import uuid
from .research_project import Research

class FormattedResearchFindings:
     def __init__(self, id, research_project_id, title, author=None,
                publication_date=None, source=None, finding_summary=None,
               relevance_to_research_topic=None, url=None, keywords_and_key_aspects=None,
               research_cycle_count=None, query=None):
          self.id = uuid.uuid7() if id is None else id
          self.research_project_id = research_project_id
          self.title = title
          self.author = author
          self.publication_date = publication_date
          self.source = source
          self.finding_summary = finding_summary
          self.relevance_to_research_topic = relevance_to_research_topic
          self.url = url
          self.keywords_and_key_aspects = keywords_and_key_aspects
          self.research_cycle_count = 0 if research_cycle_count is None else research_cycle_count
          self.query = query


     def __repr__(self):
          return f"FormattedResearchFindings(id={self.id}, research_project_id={self.research_project_id}, title='{self.title}', finding_summary='{self.finding_summary}', author='{self.author}', publication_date='{self.publication_date}', source='{self.source}', relevance_to_research_topic='{self.relevance_to_research_topic}', url='{self.url}', keywords_and_key_aspects='{self.keywords_and_key_aspects}', research_cycle_count={self.research_cycle_count}, query='{self.query}')"


