import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
load_dotenv(override=True)
import uuid

class ChatHistory:
     def __init__(self):
          self.db_connection = os.getenv('DB_URI')
          self. conn = Connection.connect(self.db_connection)

     def get_thread_ids(self):
          """Retrieve all past thread ids from the Postgres database."""
          with PostgresSaver.from_conn_string(self.db_connection  ) as checkpointer:
               all_checkpoints = list(checkpointer.list(config=None))
               unique_thread_ids = set(c.config['configurable']['thread_id'] for c in all_checkpoints if 'thread_id' in c.config.get('configurable', {}))

               for thread_id in unique_thread_ids:
                    print(thread_id)
               return unique_thread_ids


     def get_thread_ids_with_checkpointer(self, checkpointer):
          """Retrieve all past thread ids from the Postgres database using an existing checkpointer."""
          all_checkpoints = list(checkpointer.list(config=None))
          unique_thread_ids = set(c.config['configurable']['thread_id'] for c in all_checkpoints if 'thread_id' in c.config.get('configurable', {}))


          return unique_thread_ids

     def get_latest_thread_id(self, checkpointer):
          """Retrieve the latest thread id from the Postgres database using a provided checkpointer."""
          # with PostgresSaver.from_conn_string(self.db_connection) as checkpointer:
          all_checkpoints = list(checkpointer.list(config=None))

          if not all_checkpoints:
               return None

          latest_thread_id = all_checkpoints[0].config['configurable'].get('thread_id') if 'thread_id' in all_checkpoints[0].config.get('configurable', {}) else None
          # latest_thread_id = latest_checkpoint.config['configurable'].get('thread_id')
          return latest_thread_id

     def create_new_thread_id(self):
          """Create a new thread id for a new conversation."""
          unique_thread_ids = self.get_thread_ids()
          new_thread_id = str(uuid.uuid4())
          while new_thread_id in unique_thread_ids:
               new_thread_id = str(uuid.uuid4())
          return new_thread_id


     def delete_thread(self, thread_id):
          """Delete a thread from the Postgres database using the provided thread_id."""
          with PostgresSaver.from_conn_string(self.db_connection) as checkpointer:
               checkpointer.delete_thread(thread_id)
               return f"Thread {thread_id} deleted successfully."