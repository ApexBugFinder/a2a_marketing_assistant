import os

from langchain.tools import tool
from langsmith import traceable

from src.config.serpapi_main_topic_config import MainTopicConfig
from src.config.serpapi_key_aspect_config import KeyAspectConfig
import serpapi
from langchain_core.tools import StructuredTool

from pydantic import BaseModel, Field


class _QueryInput(BaseModel):
     query: str = Field(description="The search query to retrieve from the serpapi search tool")

class _SerpapiOutput(BaseModel):
     title: str | None = Field(description="The title of the search result", default=None)
     link: str | None = Field(description="The link to the search result", default=None)
     source: str | None = Field(description="The source of the search result", default=None)
     date: str | None = Field(description="The date of publication of the search result", default=None)
     position: int | None = Field(description="The position of the search result in the search results page", default=None)
     snippet: str | None = Field(description="The snippet of the search result", default=None)

class SerpApiTool:
     def __init__(self):
          self.main_topic_config = MainTopicConfig()
          self.key_aspect_config = KeyAspectConfig()
          self.main_topic_searcher_tool = StructuredTool.from_function(
               func=self.serpapi_main_topic_search,
               name="SerpAPI Main Topic Search Tool",
               description="""A tool to perform a web search using the SerpAPI to retrieve relevant information
               and documents related to the research topic.""",
               args_schema=_QueryInput,
               response_format='content'
               )
          self.key_aspect_searcher_tool = StructuredTool.from_function(
               func=self.serpapi_key_aspect_search,
               name="SerpAPI Key Aspect Search Tool",
               description="""A tool to perform a web search using the SerpAPI to retrieve relevant information
               and documents related to a specific aspect of the research topic.""",
               args_schema=_QueryInput,

               response_format='content'

               )

     # @tool("SerpAPI Main Topic Search Tool", return_direct=True)
     @traceable(run_type='tool')
     def serpapi_main_topic_search(self, query: str) -> dict:
          """Useful for performing a web search using the SerpAPI to retrieve relevant information and documents related to the research topic."""

          client = serpapi.Client(api_key=self.main_topic_config.SERP_API_KEY)
          params = {
               "engine": self.main_topic_config.ENGINE,
               "q": query,
               "device": self.main_topic_config.DEVICE,
               "hl": self.main_topic_config.HL,
               "gl": self.main_topic_config.GL,
               "start": self.main_topic_config.START,
               "no_cache": self.main_topic_config.NO_CACHE,
               "num": self.main_topic_config.MAX_RESULTS,
               "api_key": self.main_topic_config.SERP_API_KEY
          }
          results = client.search(params)



          return self.clean_results(results)

     # @tool("SerpAPI Key Aspect Search Tool", return_direct=True)
     @traceable(run_type='tool')
     def serpapi_key_aspect_search(self, query: str) :
          """Useful for performing a web search using the SerpAPI to retrieve relevant information and documents related to a specific aspect of the research topic."""
          client = serpapi.Client(api_key=self.key_aspect_config.SERP_API_KEY)
          params = {
               "engine": self.key_aspect_config.ENGINE,
               "q": query,
               "device": self.key_aspect_config.DEVICE,
               "hl": self.key_aspect_config.HL,
               "gl": self.key_aspect_config.GL,
               "start": self.key_aspect_config.START,
               "no_cache": self.key_aspect_config.NO_CACHE,
               "num": self.key_aspect_config.MAX_RESULTS,
               "api_key": self.key_aspect_config.SERP_API_KEY
          }
          results = client.search(params)

          return self.clean_results(results)

     def clean_results(self, results: dict) -> list[SerpapiOutput]:
          """A helper function to clean the results returned by the SerpAPI and extract the relevant information."""
          cleaned_results = []
          for result in results.get('organic_results', []):
               record = {}
               if 'link' in result:
                    record['link'] = result['link'].split('&sa=U&')[0]
               record['title'] = result.get('title', '')
               record['source'] = result.get('source', '')
               record['date'] = result.get('date', '')
               record['position'] = result.get('position', '')
               record['snippet'] = result.get('snippet', '')
               cleaned_results.append(record)

          return cleaned_results