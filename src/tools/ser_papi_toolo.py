import os

from langchain.tools import tool
from langsmith import traceable
from mcp_server.model_schemas import ResearchFinding
import requests
from config.serpapi_main_topic_config import Config as MainTopicConfig
from config.serpapi_key_aspect_config import Config as KeyAspectConfig
import serpapi
from langchain_core.tools import StructuredTool

from pydantic import BaseModel, Field


class _QueryInput(BaseModel):
     query: str = Field(description="The search query to retrieve from the serpapi search tool")

class SerpapiInput(BaseModel):
     query: str = Field(description="The search query to retrieve from the serpapi search tool")
     research_project_id: str = Field(description="The unique identifier for the research project")
     reearch_cycle_count: int = Field(description="The current research cycle count, useful for tracking and enforcing caps if needed.")
class FormattedSerpapiWebSearchResults(BaseModel):
     research_project_id: str|None = Field(description="the unique identifier for the research project")
     title: str | None = Field(description="The title of the search result", default=None)
     link: str | None = Field(description="The link to the search result", default=None)
     source: str | None = Field(description="The source of the search result", default=None)
     date: str | None = Field(description="The date of publication of the search result", default=None)
     position: int | None = Field(description="The position of the search result in the search results page", default=None)
     snippet: str | None = Field(description="The snippet of the search result", default=None)
     research_cycle_count: int | None = Field(description="The current research cycle count, useful for tracking and enforcing caps if needed.", default=None)
class SerpApiTools:
     def __init__(self):
          self.main_topic_config = MainTopicConfig()
          self.key_aspect_config = KeyAspectConfig()
          self. base_url = "https://api.semanticscholar.org/graph/v1"
          self.bulk = "/paper/search/bulk"
          self.main_topic_searcher_tool = StructuredTool.from_function(
               func=self.serpapi_main_topic_search,
               name="SerpAPI Main Topic Search Tool",
               description="""A tool to perform a web search using the SerpAPI to retrieve relevant information
               and documents related to the research topic.""",
               args_schema=SerpapiInput,
               response_format='content'
               )
          self.key_aspect_searcher_tool = StructuredTool.from_function(
               func=self.serpapi_key_aspect_search,
               name="SerpAPI Key Aspect Search Tool",
               description="""A tool to perform a web search using the SerpAPI to retrieve relevant information
               and documents related to a specific aspect of the research topic.""",
               args_schema=SerpapiInput,

               response_format='content'

               )

     # @tool("SerpAPI Main Topic Search Tool", return_direct=True)
     @traceable(run_type='tool')
     def serpapi_main_topic_search(self, query: str, research_project_id: str, research_cycle_count: int | None = None) -> dict:
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



          return self.clean_results(results, research_project_id, research_cycle_count)

     # @tool("SerpAPI Key Aspect Search Tool", return_direct=True)
     @traceable(run_type='tool')
     def serpapi_key_aspect_search(self, query: str, research_project_id: str, research_cycle_count: int | None = None) :
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

          return self.clean_results(results, research_project_id, research_cycle_count)

     def clean_results(self, results: dict, research_project_id: str, research_cycle_count: int | None = None) -> list[ResearchFinding]:
          """A helper function to clean the results returned by the SerpAPI and extract the relevant information."""
          print(f'Research Project ID: {research_project_id}')
          cleaned_results: list[ResearchFinding] = []
          for result in results.get('organic_results', []):
               if 'link' not in result:
                    continue
               raw_link = result['link']
               if isinstance(raw_link, dict):
                    link = next(
                         (v.split('&sa=U&')[0] if v.startswith('/url?q=') else v
                              for v in raw_link.values()
                              if isinstance(v, str) and (v.startswith('http') or v.startswith('/url?q='))),
                         None,
                    )
               elif raw_link.startswith('/url?q='):
                    link = raw_link.split('&sa=U&')[0]
               elif raw_link.startswith('http'):
                    link = raw_link
               else:
                    continue
               if not link:
                    continue
               record = ResearchFinding(
                    research_project_id=research_project_id,
                    title=result.get('title', ''),
                    url=link,
                    author=result.get('author', ''),
                    source=result.get('source', ''),
                    pub_date=result.get('date', ''),
                    research_cycle_count = research_cycle_count
               )
               cleaned_results.append(record)

          return cleaned_results

     def searcher(self, query):
          """A simple searcher function that can be used to perform a web search semantic scholar."""
          url = f"{self.base_url}{self.bulk}"
          query_params = {
               "query": query,
               "fields": "title, url, source, publicationDate, openAccessPdf",
               "year": "1980-"
          }

          api_key = " s2k-7He1Tmbwc9RlvTlvIfR8eet87Qt31v67bVSYrFHc"
          headers = {"x-api-key": api_key}
          response = requests.get(url, params=query_params, headers=headers).json()
          return response