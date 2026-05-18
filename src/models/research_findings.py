class ResearchFinding:
     def __init__(self, research_project_id, title=None, pub_date=None, source=None, url=None):
          self.research_project_id = research_project_id
          self.source = source
          self.pub_date = pub_date
          self.title = title
          self.url = url

     def __repr__(self):
          return f"<ResearchFinding(research_project_id={self.research_project_id}, title='{self.title}', pub_date='{self.pub_date}', source='{self.source}', url='{self.url}')>"


     # 'Source': 'source name',
     #                'Author': 'author name',
     #                'All Information': 'all the information collected from the source',
     #                'Date of Publication': 'date of publication',
     #                'URL': 'url of the source',