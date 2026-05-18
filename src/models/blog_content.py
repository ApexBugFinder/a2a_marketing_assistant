# Class to manage blog content creation and scheduling based on research findings and content strategy
import uuid

class BlogContent:
     def __init__(self, id, research_project_id, title, content, seo_keywords, publication_date, status, url, keywords_and_key_aspects):
          self.id = id or str(uuid.uuid4())
          self.research_project_id = research_project_id
          self.title = title
          self.content = content
          self.seo_keywords = seo_keywords
          self.publication_date = publication_date
          self.status = status
          self.url = url
          self.keywords_and_key_aspects = keywords_and_key_aspects

     def __repr__(self):
          return f"<BlogContenter(id={self.id}, research_project_id={self.research_project_id}, title='{self.title}', content='{self.content}', seo_keywords='{self.seo_keywords}', publication_date='{self.publication_date}', status='{self.status}', url='{self.url}', keywords_and_key_aspects='{self.keywords_and_key_aspects}')>"