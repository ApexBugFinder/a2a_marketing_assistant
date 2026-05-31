import uuid

class ResearchProject:
     def __init__(self, id, name, query, description):
          self.id: uuid.UUID | None = id
          self.name = name
          self.query = query
          self.description = description
          self.created_at = None
          self.updated_at = None
          self.end_date = None

     def __repr__(self):
          return f"ResearchProject(id={self.id}, name='{self.name}', query='{self.query}', description='{self.description}')"