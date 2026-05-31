import json
import logging
import re
from collections.abc import AsyncIterable
from typing import Any
import os
import uuid
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, before_sleep_log
from common import instructions
from common.base_agent import BaseAgent
from common.types import PlannerResponseFormat  # still used in get_agent_response validation
from common.utils import init_api_key
from tools.postgres_tools import PostgresTools
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from common.checkpointer import create_async_postgres_checkpointer
from langgraph.checkpoint.memory import MemorySaver
import langgraph.prebuilt as _lgp
import psycopg

logger = logging.getLogger(__name__)


@tool
def create_id(value: str | None = None) -> str:
    """Generate and return a new unique UUID4 string to use as a research_project_id.
    Do not pass any arguments — this tool always generates a fresh UUID regardless of input."""
    return str(uuid.uuid4())


@tool
def postgres_async_runner_tool(
    query: str,
    sql_params: list[str | int | float | None] = None,
    fetch: bool = True,
) -> str:
    """Run a SQL query against the PostgreSQL database and return results as a string.
    - query: the raw SQL statement with $1, $2, ... placeholders.
    - sql_params: flat list of values for $1, $2, ... IN EXACT ORDER.
      CRITICAL: the order of values in sql_params MUST match the column order in the SQL.
      For research_projects INSERT, sql_params = [id_uuid, name, query_text, description].
    - fetch: True to return rows, False for INSERT/UPDATE/DELETE.
    """
    return str(PostgresTools()._run_query_sync(query, params=sql_params or [], fetch=fetch))


_PLANNER_TOOLS = [create_id, postgres_async_runner_tool]


class PlannerAgent(BaseAgent):
    """The PlannerAgent generates a sequential plan of tasks based on a user's query.
    It is backed by LangGraph with a PostgreSQL checkpointer (falls back to in-memory if unavailable)."""

    def __init__(self):
        init_api_key()
        load_dotenv()
        logger.info("Initializing Planner Agent")

        super().__init__(
            agent_name="PlannerAgent",
            description="An agent that generates a sequential plan of tasks based on a user's query.",
            content_types=['text', 'text/plain'],
        )
        model_name = os.getenv('LITE_LLM_AGENT')
        self.model = ChatGoogleGenerativeAI(
            model = model_name,
            # model=os.getenv('LITE_LLM_PLANNER', os.getenv('LITE_LLM_AGENT', 'gemini-2.0-flash')),
            temperature=0.2,
            max_tokens=60537,

        )

        # Graph is built lazily on first stream() call so the async postgres
        # checkpointer can be awaited in the correct event loop.
        self.memory = None
        self.graph = None

    async def _ensure_graph(self) -> None:
        """Build the LangGraph agent on first use, in the running async event loop."""
        if self.graph is not None:
            return
        try:
            memory = await create_async_postgres_checkpointer()
            logger.info("Planner Agent: async PostgreSQL checkpointer initialized.")
        except Exception as e:
            logger.warning(f"Planner Agent: PostgreSQL unavailable, falling back to MemorySaver: {e}")
            memory = MemorySaver()
        self.memory = memory
        self.graph = _lgp.create_react_agent(
            model=self.model,
            tools=_lgp.ToolNode(_PLANNER_TOOLS, handle_tool_errors=True),
            checkpointer=self.memory,
            prompt=instructions.PLANNER_AGENT_COT_INSTRUCTION,
        )

    def _use_memory_fallback(self) -> None:
        """Switch the agent to an in-memory checkpointer after a postgres failure."""
        logger.warning("Planner Agent: switching to MemorySaver (postgres unavailable).")
        self.memory = MemorySaver()
        self.graph = _lgp.create_react_agent(
            model=self.model,
            tools=_lgp.ToolNode(_PLANNER_TOOLS, handle_tool_errors=True),
            checkpointer=self.memory,
            prompt=instructions.PLANNER_AGENT_COT_INSTRUCTION,
        )

    @staticmethod
    def _extract_text(content) -> str:
        """Extract plain text from an AIMessage content value.

        Handles str, list-of-dicts (some Gemini versions),
        and list-of-objects with a .text attribute (other Gemini versions).
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(block.get('text') or block.get('content') or '')
                elif hasattr(block, 'text'):
                    parts.append(block.text or '')
            return ' '.join(p for p in parts if p)
        return str(content) if content else ''

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=30, max=120),
        retry=retry_if_exception(
            lambda e: 'RESOURCE_EXHAUSTED' in str(e) or '429' in str(e)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _run_astream(self, inputs: dict, config: dict) -> list[str]:
        """Run the graph and collect non-empty AIMessage text chunks."""
        chunks = []
        async for item in self.graph.astream(inputs, config, stream_mode='values'):
            if not item.get('messages'):
                continue
            message = item['messages'][-1]
            if not isinstance(message, AIMessage):
                continue
            text = self._extract_text(message.content)
            if text:
                logger.debug("Planner chunk (%d chars): %.80s", len(text), text)
                chunks.append(text)
        return chunks

    async def _collect_astream(self, inputs: dict, config: dict) -> list[str]:
        """Run the graph, falling back to MemorySaver on postgres/SSL errors."""
        try:
            return await self._run_astream(inputs, config)
        except Exception as e:
            msg = str(e).lower()
            is_pg = isinstance(e, psycopg.Error) or any(
                kw in msg for kw in ('ssl', 'connection', 'operationalerror', 'consuming input')
            )
            if not is_pg:
                raise
            logger.warning("Planner Agent: postgres/SSL error (%s); retrying with MemorySaver.", e)
            self._use_memory_fallback()
            return await self._run_astream(inputs, config)

    async def invoke(self, query: str, sessionId: str, task_id: str) -> dict[str, Any]:
        config = {'configurable': {'thread_id': sessionId}}
        logger.info(f"Invoking Planner Agent — sessionId={sessionId}, task_id={task_id}")
        if self.graph is None:
            raise RuntimeError("PlannerAgent graph not initialized — call stream() first.")
        await self.graph.ainvoke({'messages': [('user', query)]}, config=config)
        return await self.get_agent_response(config)

    async def stream(
        self, query: str, sessionId: str, task_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': sessionId}}
        logger.info(f"Streaming Planner Agent — sessionId={sessionId}, task_id={task_id}")

        try:
            await self._ensure_graph()
            chunks = await self._collect_astream(inputs, config)
        except Exception as e:
            logger.error(f"Planner Agent stream error: {e!r}", exc_info=True)
            yield {
                'response_type': 'text',
                'is_task_complete': True,
                'require_user_input': False,
                'content': f"Planner Agent encountered an error: {type(e).__name__}: {e!r}",
            }
            return

        # Stream intermediate chunks (reasoning steps) to the user.
        for content in chunks[:-1]:
            yield {
                'response_type': 'text',
                'is_task_complete': False,
                'require_user_input': False,
                'content': content,
            }

        yield await self.get_agent_response(config, last_chunk=chunks[-1] if chunks else None)

    def _build_response(self, structured: PlannerResponseFormat) -> dict[str, Any]:
        project_id = structured.research_project_id or (
            structured.content.research_project_id if structured.content else ''
        )
        if structured.status == 'input_required':
            return {
                'response_type': 'text',
                'is_task_complete': False,
                'require_user_input': True,
                'research_project_id': project_id,
                'content': structured.question or "What topic would you like me to research?",
            }
        if structured.status == 'completed':
            return {
                'response_type': 'data',
                'is_task_complete': True,
                'require_user_input': False,
                'research_project_id': project_id,
                'content': structured.content.model_dump() if structured.content else {},
            }
        return {
            'response_type': 'text',
            'is_task_complete': True,
            'require_user_input': False,
            'research_project_id': project_id,
            'content': str(structured.question or "Planner encountered an error."),
        }

    def _try_parse_chunk(self, text: str) -> PlannerResponseFormat | None:
        """Try to parse a text chunk as PlannerResponseFormat JSON.

        Handles three forms the model may emit:
        1. Bare JSON object
        2. JSON wrapped in a ```json ... ``` code fence
        3. JSON embedded anywhere inside prose text
        """
        candidates: list[str] = []

        # 1. Bare text or fully-fenced block
        stripped = re.sub(r'```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        stripped = re.sub(r'```', '', stripped).strip()
        candidates.append(stripped)

        # 2. Every {...} span in the original text (finds embedded JSON)
        for m in re.finditer(r'\{', text):
            candidates.append(text[m.start():])

        for candidate in candidates:
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return PlannerResponseFormat.model_validate(obj)
            except Exception:
                pass
            # Also try decoding only the first valid JSON object from the candidate
            try:
                obj, _ = json.JSONDecoder().raw_decode(candidate)
                if isinstance(obj, dict):
                    return PlannerResponseFormat.model_validate(obj)
            except Exception:
                pass

        return None

    async def get_agent_response(self, config: dict, last_chunk: str | None = None) -> dict[str, Any]:
        """Return the final structured response.

        Priority:
        1. Parse last_chunk text directly as PlannerResponseFormat JSON.
        2. Scan all AIMessages in state for a parseable JSON.
        3. structured_response stored in LangGraph state (legacy, kept as last resort).
        """
        try:
            current_state = await self.graph.aget_state(config)
            state_values = current_state.values if current_state else {}
        except Exception as e:
            logger.warning("PlannerAgent: aget_state failed (%s)", e)
            state_values = {}

        # Path 1: LangGraph structured_response (response_format enforces the schema)
        logger.debug("PlannerAgent state structured_response: %s", state_values.get('structured_response'))
        structured = state_values.get('structured_response')
        if isinstance(structured, PlannerResponseFormat):
            logger.info("PlannerAgent: using structured_response from graph state (status=%s, tasks=%d).",
                        structured.status,
                        len(structured.content.tasks) if structured.content else 0)
            return self._build_response(structured)

        # Path 2: parse the last collected AIMessage chunk
        if last_chunk:
            parsed = self._try_parse_chunk(last_chunk)
            if parsed:
                logger.info("PlannerAgent: parsed response from last_chunk.")
                return self._build_response(parsed)

        # Path 3: scan all messages in state for any parseable AIMessage
        for msg in reversed(state_values.get('messages', [])):
            if isinstance(msg, AIMessage):
                text = self._extract_text(msg.content)
                if text:
                    parsed = self._try_parse_chunk(text)
                    if parsed:
                        logger.info("PlannerAgent: parsed response from message history.")
                        return self._build_response(parsed)

        logger.warning(
            "PlannerAgent: no parseable response found.\n"
            "  last_chunk (first 500 chars): %s\n"
            "  message count in state: %d",
            (last_chunk or "")[:500],
            len(state_values.get('messages', [])),
        )
        return {
            'response_type': 'text',
            'is_task_complete': False,
            'require_user_input': True,
            'research_project_id': None,
            'content': "What topic would you like me to research?",
        }
