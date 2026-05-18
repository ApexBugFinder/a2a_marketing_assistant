class MarketingImage:
     def __init__(self, id, research_project_id, image_url, tiny_url=None, description=None):
          self.id = id
          self.research_project_id = research_project_id
          self.image_url = image_url
          self.tiny_url = tiny_url
          self.description = description

     def __repr__(self):
          return f"<MarketingImage(id={self.id}, research_project_id={self.research_project_id}, image_url='{self.image_url}', tiny_url='{self.tiny_url}', description='{self.description}')>"