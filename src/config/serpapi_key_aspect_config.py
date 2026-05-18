"""Config"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv(override=True)

@dataclass
class Config:
     """SerpAPI Tool is a tool that allows you to search the web using the SerpAPI for documents and articles.
     """
     SERP_API_KEY: str = os.getenv("SERP_API_KEY")
     ENGINE: str = "google"
     DEVICE:str = "desktop"
     HL:str = "en"
     GL:str = "us"
     START: int = 0
     NO_CACHE: bool = True
     MAX_RESULTS: int = 2
     # EXCLUDE_DOMAINS=None


     def __repr__(self):
          return f"""
SerpAPI Tool Configuration:
-------------------------
SERP_API_KEY: {self.SERP_API_KEY}
ENGINE: {self.ENGINE}
DEVICE: {self.DEVICE}
HL: {self.HL}
GL: {self.GL}
START: {self.START}
NO_CACHE: {self.NO_CACHE}
MAX_RESULTS: {self.MAX_RESULTS}

          """