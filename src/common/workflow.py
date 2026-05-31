import json
import logging
import uuid
import os
from typing import Any

from collections.abc import AsyncIterable
from enum import Enum
from uuid import uuid4

import httpx
import networkx as nx

from a2a.client import create_client, ClientConfig
from a2a.helpers import new_text_message
from a2a.types import (
     Role,
     SendMessageRequest,
     StreamResponse,
     TaskArtifactUpdateEvent,
     TaskState,
     TaskStatusUpdateEvent,
)
from common.utils import get_mcp_server_config
from mcp_server import client_agents as client

logger = logging.getLogger(__name__)

class Status(Enum):
     """Represents the status of the workflow and its associated node."""
     READY = "READY"
     RUNNING = "RUNNING"
     COMPLETED = "COMPLETED"
     PAUSED = "PAUSED"
     ERROR = "ERROR"
     INITIALIZED = "INITIALIZED"


class WorkflowNode:
     """Represents a single node in a workflow graph.

     Each node encapsulates a specific task to be executed , such as finding
     an agent or invoking an agent's capabilities.  It manages its own state
     (e.g., READ, RUNNING, COMPLETED, PAUSED) and can execute its assigned task.
     """
     def __init__(self,
                    task: str,
                    node_key: str | None = None,
                    node_label: str | None = None,
                    agent_name: str | None = None,
                    ):
          self.id = str(uuid4())
          self.node_key = node_key
          self.node_label = node_label
          self.agent_name = agent_name
          self.task = task
          self.results = None
          self.state = Status.READY
          self.error: str | None = None

     async def get_planner_resource(self) -> str | None:
          """Fetches the planner agent URL from MCP."""
          import asyncio as _asyncio
          logger.info(f"Fetching planner resource for node {self.id}: {self.node_label} with task: \n {self.task}\n\n")
          config = get_mcp_server_config()
          last_error = None
          for attempt in range(3):
               try:
                    async with client.init_session(
                         config.host,
                         config.port,
                         config.transport,
                         config.path) as session:
                         response = await client.find_resource(
                              session, 'resource://agent_cards/planner_agent'
                         )
                         data = json.loads(response.contents[0].text)
                         return data['agent_card'][0].get('url')
               except Exception as e:
                    last_error = e
                    msg = str(e)
                    if hasattr(e, 'exceptions'):
                         inner = [str(x) for x in e.exceptions]
                         msg = '; '.join(inner)
                    logger.warning(
                         f"get_planner_resource attempt {attempt + 1}/3 failed: {msg}. "
                         f"{'Retrying in 2s...' if attempt < 2 else 'Giving up.'}"
                    )
                    if attempt < 2:
                         await _asyncio.sleep(2)
          raise RuntimeError(f"get_planner_resource failed after 3 attempts: {last_error}")

     async def find_agent_for_tasks(self) -> str | None:
          """Finds the appropriate agent URL for the task."""
          import asyncio as _asyncio
          logger.info(f"Finding agent for task: \n {self.task}\n\n")
          config = get_mcp_server_config()
          last_error = None
          for attempt in range(3):
               try:
                    async with client.init_session(
                         config.host,
                         config.port,
                         config.transport,
                         config.path) as session:
                         response = await client.find_agent(
                              session, self.task
                         )
                         # find_agent returns CallToolResult (uses .content, not .contents)
                         data = json.loads(response.content[0].text)
                         logger.debug(f"Found agent {data.get('name')} for task: \n {self.task}\n\n")
                         return data.get('url')
               except Exception as e:
                    last_error = e
                    msg = str(e)
                    # Unwrap TaskGroup exceptions to surface the real cause
                    if hasattr(e, 'exceptions'):
                         inner = [str(x) for x in e.exceptions]
                         msg = '; '.join(inner)
                    logger.warning(
                         f"find_agent attempt {attempt + 1}/3 failed: {msg}. "
                         f"{'Retrying in 2s...' if attempt < 2 else 'Giving up.'}"
                    )
                    if attempt < 2:
                         await _asyncio.sleep(2)
          raise RuntimeError(f"find_agent failed after 3 attempts: {last_error}")

     async def find_agent_by_name(self) -> str | None:
          """Looks up an agent card resource by display name and returns its URL."""
          import asyncio as _asyncio
          logger.info(f"Looking up agent by name: {self.agent_name}")
          config = get_mcp_server_config()
          resource_key = self.agent_name.lower().replace(' ', '_')
          last_error = None
          for attempt in range(3):
               try:
                    async with client.init_session(
                         config.host,
                         config.port,
                         config.transport,
                         config.path) as session:
                         response = await client.find_resource(
                              session, f'resource://agent_cards/{resource_key}'
                         )
                         data = json.loads(response.contents[0].text)
                         return data.get('url')
               except Exception as e:
                    last_error = e
                    msg = str(e)
                    if hasattr(e, 'exceptions'):
                         inner = [str(x) for x in e.exceptions]
                         msg = '; '.join(inner)
                    logger.warning(
                         f"find_agent_by_name attempt {attempt + 1}/3 failed: {msg}. "
                         f"{'Retrying in 2s...' if attempt < 2 else 'Giving up.'}"
                    )
                    if attempt < 2:
                         await _asyncio.sleep(2)
          raise RuntimeError(f"find_agent_by_name failed after 3 attempts for '{self.agent_name}': {last_error}")

     async def run_node(self, query: str, context_id: str) -> AsyncIterable[Any]:
          """Executes the node's task using the appropriate agent and yields results as they become available."""
          logger.info(f"Running node {self.id} with task: \n {self.task}\n\n")
          agent_url = None
          try:
               if self.node_key == 'planner':
                    agent_url = await self.get_planner_resource()
               elif self.agent_name:
                    agent_url = await self.find_agent_by_name()
               else:
                    agent_url = await self.find_agent_for_tasks()
          except Exception as e:
               logger.error(f"Node {self.id}: failed to resolve agent URL: {e}", exc_info=True)
               self.state = Status.ERROR
               self.error = f"Failed to find agent for task '{self.task[:80]}': {e}"
               return
          if not agent_url:
               msg = f"No agent URL found for task: {self.task[:100]}"
               logger.error(f"Node {self.id}: {msg}")
               self.state = Status.ERROR
               self.error = msg
               return
          try:
               async with httpx.AsyncClient(
                    headers={'A2A-Version': '1.0'},
                    timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
               ) as httpx_client:
                    a2a_client = await create_client(
                         agent_url,
                         client_config=ClientConfig(
                              httpx_client=httpx_client,
                              supported_protocol_bindings=['HTTP+JSON'],
                         ),
                    )
                    # role=ROLE_USER: sub-agents treat the orchestrator as their user;
                    # new_task_from_user_message rejects ROLE_AGENT messages with a 500.
                    # task_id omitted so each sub-agent creates its own task.
                    message = new_text_message(text=query, context_id=context_id, role=Role.ROLE_USER)
                    request = SendMessageRequest(message=message)
                    async for chunk in a2a_client.send_message(request):
                         logger.debug(f"Received chunk from {agent_url} for node {self.id}: \n{chunk}\n\n")
                         if chunk.HasField('artifact_update'):
                              artifact = chunk.artifact_update.artifact
                              self.results = artifact
                              logger.info(f"Node {self.id} completed with artifact result: \n {artifact}\n\n")
                         yield chunk
          except Exception as e:
               logger.error(f"Node {self.id}: agent call to {agent_url} failed: {e}", exc_info=True)
               self.state = Status.ERROR
               self.error = f"Agent at {agent_url} failed: {e}"


class WorkflowGraph:
     """Represents a workflow as a directed graph of WorkflowNodes.

     The WorkflowGraph manages the execution flow between nodes, ensuring that
     tasks are executed in the correct order based on their dependencies. It
     provides methods to add nodes, define edges (dependencies), and execute the
     workflow while tracking the state of each node.
     """
     def __init__(self):
          self.graph = nx.DiGraph()
          self.nodes = {}
          self.latest_node = None
          self.node_type = None
          self.state = Status.INITIALIZED
          self.pause_node_id = None
          self.current_node_id: str | None = None

     def add_node(self, node: WorkflowNode) -> None:
          """Adds a WorkflowNode to the graph."""
          self.graph.add_node(node.id, query=node.task)
          self.nodes[node.id] = node
          self.latest_node = node.id

     def add_edge(self, from_node_id: str, to_node_id: str) -> None:
          """Defines a directed edge (dependency) between two nodes."""
          if from_node_id in self.graph.nodes and to_node_id in self.graph.nodes:
               self.graph.add_edge(from_node_id, to_node_id)
          else:
               logger.error(f"Cannot add edge from {from_node_id} to {to_node_id}: One or both nodes not found in the graph.")
               raise ValueError(f"Cannot add edge from {from_node_id} to {to_node_id}: One or both nodes not found in the graph.")

     async def run_workflow(self, start_node_id: str|None = None) -> AsyncIterable[dict[str, Any]]:
          """Executes the workflow"""
          logger.info(f"Executing workflow graph starting from node {start_node_id}")
          if not start_node_id or start_node_id not in self.nodes:
               start_nodes = [n for n, d in self.graph.in_degree() if d == 0]
          else:
               start_nodes = [start_node_id]

          applicable_graph = set()

          for node_id in start_nodes:
               applicable_graph.add(node_id)
               applicable_graph.update(nx.descendants(self.graph, node_id))

          complete_graph = list(nx.topological_sort(self.graph))
          sub_graph  = [n for n in complete_graph if n in applicable_graph]
          logger.info(f"Sub graph {sub_graph} size {len(sub_graph)}")
          self.state = Status.RUNNING

          for node_id in sub_graph:
               self.current_node_id = node_id
               node = self.nodes[node_id]
               node.state = Status.RUNNING
               query = self.graph.nodes[node_id].get('query')
               context_id = self.graph.nodes[node_id].get('context_id')

               logger.info(f"Running node {node_id} with task: \n {node.task}\n\n")

               async for chunk in node.run_node(query, context_id):
                    # when the workflow node is paused, do not yield any chunks
                    # but, let the loop complete
                    if node.state != Status.PAUSED:
                         if isinstance(chunk, StreamResponse) and chunk.HasField('status_update'):
                              task_status_event = chunk.status_update
                              context_id = task_status_event.context_id
                              if task_status_event.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
                                   logger.info(f"Pausing node {node_id} due to input required event with context id {context_id}")
                                   node.state = Status.PAUSED
                                   self.state = Status.PAUSED
                                   self.pause_node_id = node_id
                              elif task_status_event.status.state == TaskState.TASK_STATE_FAILED:
                                   try:
                                        error_text = task_status_event.status.message.parts[0].text
                                   except (AttributeError, IndexError):
                                        error_text = "Agent reported failure with no message."
                                   logger.error(f"Node {node_id} received TASK_STATE_FAILED: {error_text}")
                                   node.state = Status.ERROR
                                   node.error = error_text
                         yield chunk
                    if self.state == Status.PAUSED:
                         break
               if node.state == Status.RUNNING:
                    node.state = Status.COMPLETED
                    logger.info(f"Node {node_id} completed successfully.")
               elif node.state == Status.ERROR:
                    logger.error(f"Node {node_id} failed: {node.error}")
                    yield {'node_error': True, 'task': node.task, 'error': node.error or 'Unknown error'}
               if self.state == Status.PAUSED:
                    break

          # Determine final graph state after all nodes have run
          failed_nodes = [n for n in sub_graph if self.nodes[n].state == Status.ERROR]
          if failed_nodes:
               self.state = Status.ERROR
          elif self.state == Status.RUNNING:
               self.state = Status.COMPLETED

     def set_node_attribute(self,node_id, attribute, value) -> None:
          nx.set_node_attributes(self.graph, {node_id: value}, attribute)

     def set_node_attributes(self, node_id, attr_val) -> None:
          nx.set_node_attributes(self.graph, {node_id: attr_val})

     def is_empty(self) -> bool:
          return len(self.graph.nodes) == 0