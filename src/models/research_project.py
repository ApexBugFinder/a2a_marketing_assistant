import uuid

class ResearchProject:
     def __init__(self, id, name, query, description):
          self.id = id or str(uuid.uuid4())
          self.name = name
          self.query = query
          self.description = description


     def __repr__(self):
          return f"ResearchProject(id={self.id}, name='{self.name}', query='{self.query}', description='{self.description}')"