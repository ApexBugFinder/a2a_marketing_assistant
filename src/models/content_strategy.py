import uuid

class ContentStrategy:
     def __init__(self, id, research_project_id, content_strategy_overview, key_messages, target_audience, content_formats_and_channels, content_strategy_calendar=None):
          self.id = uuid.uuid4() if id is None else id
          self.research_project_id = research_project_id
          self.content_strategy_overview = content_strategy_overview
          self.key_messages = key_messages
          self.target_audience = target_audience
          self.content_formats_and_channels = content_formats_and_channels
          self.content_strategy_calendar = content_strategy_calendar


     def __repr__(self):
          return f"ContentStrategy(id={self.id}, research_project_id={self.research_project_id}, content_strategy_overview='{self.content_strategy_overview}', key_messages='{self.key_messages}', target_audience='{self.target_audience}', content_formats_and_channels='{self.content_formats_and_channels}', content_strategy_calendar='{self.content_strategy_calendar}')"