import os
import json
import traceback
from pathlib import Path
import google.generativeai as genai
import requests
import pandas as pd
import numpy as np

from src.tools.pinecone_retriever import PineconeRetrieverTool
from tools.pinecone_pusher_tool import PineconePusherTool
from src.tools.postgres_tools import PostgresTools
from src.tools.ser_papi_toolo import SerpApiTool
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
from common.utils import init_api_key
logger = get_logger(__name__)
AGENT_CARDS_DIR = 'agent_cards'
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# a2a AGENT FUNCTIONS
def generate_embeddings(text):
     """Generates embeddings for the given text using the Gemini embedding model."""


     return genai.embed_content(
          model=EMBEDDING_MODEL,
          content=text,
          task_type='retrieval_document'
     )['embedding']


def load_agent_cards():
     """Loads agent card data from JSON files within a specified directory.

     Returns:
          A list containing JSON data from an agent card file found in the specified directory.
          Returns an empty list  if the firectory is empty, contains no '.json' files,
          or if all '.json' files encounter errors during processing

     """
     cards_uris = []
     agent_cards = []
     AGENT_CARDS_DIR = os.getenv("AGENT_CARDS_DIR", AGENT_CARDS_DIR)
     dir_path = Path(AGENT_CARDS_DIR)
     if not dir_path.is_dir():
          logger.error(f"Agent cards directory {AGENT_CARDS_DIR} does not exist or is not a directory.")
          return agent_cards

     logger.info(f'Loading agent cards from the card repo: {AGENT_CARDS_DIR}')

     for filename in os.listdir(AGENT_CARDS_DIR):
          if filename.lower().endswith('.json'):
               file_path = dir_path / filename
               try:
                    if file_path.is_file():
                         logger.info(f"Processing agent card file: {filename}")
                         with open(file_path, 'r', encoding='utf-8') as f:
                              card_data = json.load(f)
                              agent_cards.append(card_data)
                              cards_uris.append(
                                   f'resource://agent_cards/{Path(filename).stem}'
                              )
                              logger.info(f"Loaded agent card: {filename} with URI: {card_data.get('card_uri')}")
               except json.JSONDecodeError as jde:
                    logger.error(f"JSON decode error in file {filename}: {jde}")
                    logger.debug(traceback.format_exc())
               except OSError as ose:
                    logger.error(f"OS error when processing file {filename}: {ose}")
                    logger.debug(traceback.format_exc())
               except Exception as e:
                    logger.error(f"Error loading agent card from file {filename}: {e}")
                    logger.debug(traceback.format_exc())

     logger.info(
          f"Finished loading agent cards. Total cards loaded: {len(agent_cards)}.\nCard URIs: {'\n'.join(cards_uris)}"
     )
     return cards_uris, agent_cards


def build_agent_card_embeddings() -> pd.DataFrame:
     """Loads agent cards, generates embeddings for them, and returns a DataFrame.

     Returns:
          Optional[pd.DataFrame]: A Pandas DataFrame containing the original
          'agent_card' data and their corresponding 'Embeddings'. Returns None
          if no agent cards were loaded initially or if an exception occurred
          during the embedding generation process.
     """
     card_uris, agent_cards = load_agent_cards()
     logger.info('Generating Embeddings for agent cards')
     try:
          if agent_cards:
               df = pd.DataFrame(
                    {'card_uri': card_uris, 'agent_card': agent_cards}
               )
               df['card_embeddings'] = df.apply(
                    lambda row: generate_embeddings(json.dumps(row['agent_card'])),
                    axis=1,
               )
               return df
          logger.info('Done generating embeddings for agent cards')
     except Exception as e:
          logger.error(f'An unexpected error occurred : {e}.', exc_info=True)
          return None


def serve (host, port, transport):
     """Initializes and runs the Agent Cards MCP server.

     Args:
          host: The hostname or IP address to bind the server to.
          port: The port number to bind the server to.
          transport: The transport mechanism for the MCP server (e.g., 'stdio', 'sse').

     Raises:
          ValueError: If the 'GOOGLE_API_KEY' environment variable is not set.
     """
     init_api_key()
     logger.info('Starting Agent Cards MCP Server')
     mcp = FastMCP('Marketing Assistant Server Agent Cards MCP Server', host=host, port=port)
     df = build_agent_card_embeddings()

     @mcp.tool(
          name='find_agent',
          description= 'Finds the most relevant agent card based on a natural language query',
     )
     def find_agent(query: str) -> str:
          """Finds the most relevant agent card based on a query strng.

          This function takes a user quer, typically a natural language question or a task generated by an agent,
          generates its embedding, and compares it against the pre-computed embeddings of teh loaded agent cards.
          It uses teh dot product to measure similarity and identifies teh agent card with the highest
          similarity score.

          Args:
               query: A string representing the user's query or task description.

          Returns:
               The json representing the agent card deemed most relevant to the input query based on embedding similarity.

          """
          query_embedding = genai.embed_content(
               model=EMBEDDING_MODEL,
               content=query,
               task_type='retrieval_query'
          )
          dot_products = np.dot(
               np.stack(df['card_embeddings']),
               query_embedding['embedding']
          )
          best_match_index = np.argmax(dot_products)
          logger.debug(
               f'Found best match at index {best_match_index} with similarity score {dot_products[best_match_index]} \nfor query: {query}'
          )
          return df.iloc[best_match_index]['agent_card']



     # AGENTS
     @mcp.resource('resource//agent_cards/list', mime_type='application/json')
     def get_agent_cards():
          """Retrieves all loaded agent cards as a json / dictionary for the MCP resource endpoint.

          This function serves as the handler for the MCP resource identified by
          the URI 'resource://agent_cards/list'.

          Returns:
               A json / dictionary structured as {'agent_cards': [...]}, where the value is a
               list containing all the loaded agent card dictionaries. Returns
               {'agent_cards': []} if the data cannot be retrieved.
          """
          resources = {}
          logger.info('Starting read resources')
          resources['agent_cards'] = df['card_uri'].to_list()
          return resources


     @mcp.resource(
          'resource://agent_cards/{card_name}', mime_type='application/json'
     )
     def get_agent_card(card_name:str)->dict:
          """Retrieves an agent card as a json / dictionary for the MCP resource endpoint.

          This function serves as the handler for the MCP resource identified by
          the URI 'resource://agent_cards/{card_name}'.

          Returns:
               A json / dictionary
          """
          resources = {}
          logger.info(f'Starting read resource for card: resource://agent_cards/{card_name}')
          resources['agent_card'] = (
               df.loc[
                    df['card_uri'] == f'resource://agent_cards/{card_name}', 'agent_card'
               ]
          ).to_list()
          return resources
     logger.info(f'Agent cards MCP Server at {host}:{port} is starting with transport: {transport}')

     mcp.run(transport=transport)