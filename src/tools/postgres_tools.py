import json
import os
import re

from langchain.tools import tool
from langsmith import traceable
from langchain_core.tools import StructuredTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import psycopg
from psycopg.rows import dict_row
import asyncpg
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

class QueryParams(BaseModel):
     query: str = Field(..., description="The SQL query to be executed.")
     params: list = Field(default_factory=list, description="The parameters to be passed to the SQL query.")
     fetch: bool = Field(default=True, description="Whether to fetch results from the query. If False, returns the number of affected rows.")

class PostgresTools:
     def __init__(self):
          load_dotenv()
          self.SQL_DIR = os.getenv('SQL_DIR')
          self.DB_URI = os.getenv('DB_URI')
          self.create_tables_tool = StructuredTool.from_function(
               func=self.create_tables,
               name="Create Tables in PostgreSQL Tool",
               description="Creates the necessary tables in the PostgreSQL database if the tables do not exist.",
               args_schema=None,
               response_format='content'
               )
          self.postgres_async_runner_tool = StructuredTool.from_function(
               func=self._run_query_async,
               name="PostgreSQL Async Query Runner Tool",
               description="Runs a SQL query against the PostgreSQL database asynchronously and returns the results.",
               args_schema=QueryParams,
               response_format='content'
               )
          self.postgres_sync_runner_tool = StructuredTool.from_function(
               func=self._run_query_sync,
               name="PostgreSQL Sync Query Runner Tool",
               description="Runs a SQL query against the PostgreSQL database synchronously and returns the results.",
               args_schema=QueryParams,
               response_format='content'
               )




     @traceable(name='tool')
     def _run_query_sync(self, query: str, params: list = [], *, fetch: bool = True) -> str:
          """A tool to run a SQL query against the PostgreSQL database and return the results.
          Run a query against Neon over psycopg v3. Returns list[dict] when fetch=True, else rowcount."""
          params = self._json_serialize_params(params)
          # SQL library files use asyncpg-style $1,$2,... — convert to psycopg %s before executing
          psycopg_query = re.sub(r'\$\d+', '%s', query)
          with psycopg.connect(self.DB_URI, row_factory=dict_row) as conn:
               with conn.cursor() as cur:
                    cur.execute(psycopg_query, params)
                    if fetch and cur.description is not None:
                         return cur.fetchall()
                    return cur.rowcount


     def _asyncpg_dsn(self, uri: str):
          """asyncpg doesn't accept libpq's sslmode= in the DSN — strip it and return (dsn, ssl_flag)."""
          parts = urlsplit(uri)
          pairs = parse_qsl(parts.query, keep_blank_values=True)
          ssl_required = any(k == "sslmode" and v in ("require", "verify-ca", "verify-full") for k, v in pairs)
          cleaned = [(k, v) for k, v in pairs if k != "sslmode"]
          dsn = urlunsplit(parts._replace(query=urlencode(cleaned)))
          return dsn, ssl_required


     @staticmethod
     def _json_serialize_params(params: list) -> list:
          """Convert any dict/list items in params to JSON strings.

          asyncpg rejects Python dicts passed for JSONB columns unless the SQL
          uses ``CAST($N AS JSONB)``.  Since we cannot guarantee every caller
          adds the CAST, we safely convert dict/list -> JSON string here.
          Plain strings, numbers, and None pass through unchanged.
          """
          if not params:
               return params or []  # preserve [] or None as-is
          converted = []
          for p in params:
               if isinstance(p, (dict, list)):
                    converted.append(json.dumps(p))
               else:
                    converted.append(p)
          return converted

     @traceable(name='tool')
     async def _run_query_async(self, query: str, params: list = [], *, fetch: bool = True):
          """Run a query against Neon over asyncpg. Returns list[dict] when fetch=True, else status string."""
          # Convert psycopg-style %s placeholders to asyncpg-style $1, $2, ...
          if '%s' in query:
               counter = 0
               def _replace(m):
                    nonlocal counter
                    counter += 1
                    return f'${counter}'
               query = re.sub(r'%s', _replace, query)
          params = self._json_serialize_params(params)
          dsn, ssl_required = self._asyncpg_dsn(self.DB_URI)
          conn = await asyncpg.connect(dsn, ssl="require" if ssl_required else None)
          try:
               if fetch:
                    rows = await conn.fetch(query, *params)
                    return [dict(r) for r in rows]
               return await conn.execute(query, *params)
          finally:
               await conn.close()

     @traceable(name='tool')
     async def create_tables(self):
          """A tool to create the necessary tables in the PostgreSQL database."""
          # Implement the logic to connect to the PostgreSQL database and create the necessary tables if they do not exist.

          # Make sure to handle any exceptions that may occur during the database operations and return an appropriate message.
          create_tables_files = sorted(os.listdir(os.path.join(self.SQL_DIR, 'CREATE')))
          for file in create_tables_files:
               with open(os.path.join(self.SQL_DIR, 'CREATE', file), 'r') as f:
                    sql_query = f.read()
                    # Execute the SQL query to create the table.
                    # fetch=False uses conn.execute() which supports multiple
                    # semicolon-separated DDL statements (CREATE EXTENSION + CREATE TABLE).
                    # conn.fetch() uses prepared statements, which reject multi-command SQL.
                    response = await self._run_query_async(sql_query, fetch=False)
                    print(f"Executed {file}: {response}")
          return 'Tables created in PostgreSQL database successfully.'



     def delete_tables(self):
          """A tool to delete the tables in the PostgreSQL database."""
          delete_tables_files = sorted(os.listdir(os.path.join(self.SQL_DIR, 'DELETE')), reverse=True)
          try:
               for file in delete_tables_files:
                    with open(os.path.join(self.SQL_DIR, 'DELETE', file), 'r') as f:
                         sql_query = f.read()
                         response = self._run_query_sync(query=sql_query, fetch=False)
                         print(f"Executed {file}: {response}")
               return 'Tables deleted from PostgreSQL database successfully.'
          except Exception as e:
               print(f"Error deleting tables: {e}")
               return f"Error deleting tables: {e}"

     @traceable(name='tool')
     def create_id(self):
          """A tool to create a unique ID using uuid.uuid4()."""
          import uuid
          return str(uuid.uuid4())

if __name__ == "__main__":
     tools = PostgresTools()
     tools.delete_tables()