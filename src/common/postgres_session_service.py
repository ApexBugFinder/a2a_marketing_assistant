import base64
import json
import logging
import os
import uuid

import asyncpg
from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import ListSessionsResponse

logger = logging.getLogger(__name__)


class _SafeJsonEncoder(json.JSONEncoder):
    """Serialise types that appear in ADK Event payloads but are not
    handled by the standard json module.

    * ``bytes``     → UTF-8 decoded string when valid; base64 string otherwise
    * ``uuid.UUID`` → canonical hyphenated string  (e.g. "xxxxxxxx-xxxx-…")
    * Anything else unknown → ``str(obj)``  (best-effort; never raises)
    """

    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return base64.b64encode(obj).decode("ascii")
        if isinstance(obj, uuid.UUID):
            return str(obj)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class PostgresSessionService(BaseSessionService):
    """ADK SessionService backed by PostgreSQL.

    Drop-in replacement for InMemorySessionService — pass it to AgentRunner
    and conversation history survives process restarts and scales across
    multiple agent server replicas.

    The adk_sessions table must exist before first use:
        src/utils/postgressql/sql_library/CREATE/5_adk_sessions.sql
    """

    def __init__(self, db_uri: str | None = None):
        self._db_uri = db_uri or os.environ["DB_URI"]
        self._pool: asyncpg.Pool | None = None

    # ------------------------------------------------------------------
    # Pool lifecycle
    # ------------------------------------------------------------------

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._db_uri, min_size=1, max_size=5)
        return self._pool

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ------------------------------------------------------------------
    # BaseSessionService interface
    # ------------------------------------------------------------------

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str | None = None,
        state: dict | None = None,
    ) -> Session:
        sid = session_id or uuid.uuid4().hex
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO adk_sessions (id, app_name, user_id, state, events)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (app_name, user_id, id) DO NOTHING
                """,
                sid,
                app_name,
                user_id,
                json.dumps(state or {}),
                json.dumps([]),
            )
        session = Session(id=sid, app_name=app_name, user_id=user_id, state=state or {})
        logger.debug("Created session %s for user %s in app %s", sid, user_id, app_name)
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config=None,
    ) -> Session | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state, events FROM adk_sessions WHERE app_name=$1 AND user_id=$2 AND id=$3",
                app_name,
                user_id,
                session_id,
            )
        if row is None:
            return None

        state = json.loads(row["state"]) if row["state"] else {}
        raw_events = json.loads(row["events"]) if row["events"] else []
        session = Session(id=session_id, app_name=app_name, user_id=user_id, state=state)

        for raw in raw_events:
            try:
                session.events.append(Event.model_validate(raw))
            except Exception as exc:
                logger.warning("Skipping undeserializable event: %s", exc)

        logger.debug("Loaded session %s (%d events)", session_id, len(session.events))
        return session

    async def list_sessions(self, *, app_name: str, user_id: str) -> ListSessionsResponse:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, state FROM adk_sessions WHERE app_name=$1 AND user_id=$2 ORDER BY updated_at DESC",
                app_name,
                user_id,
            )
        sessions = [
            Session(
                id=r["id"],
                app_name=app_name,
                user_id=user_id,
                state=json.loads(r["state"]) if r["state"] else {},
            )
            for r in rows
        ]
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM adk_sessions WHERE app_name=$1 AND user_id=$2 AND id=$3",
                app_name,
                user_id,
                session_id,
            )

    async def append_event(self, session: Session, event: Event) -> Event:
        """Persist the new event and delegate to the in-memory parent logic."""
        # Let the base class update the in-memory session state first.
        event = await super().append_event(session=session, event=event)

        # Serialise all events to JSON and upsert.
        # _SafeJsonEncoder handles bytes / uuid.UUID values that can appear
        # inside ADK tool-response payloads (e.g. asyncpg UUID columns).
        events_json = json.dumps([e.model_dump() for e in session.events], cls=_SafeJsonEncoder)
        state_json = json.dumps(session.state, cls=_SafeJsonEncoder)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE adk_sessions
                SET events = $1, state = $2, updated_at = NOW()
                WHERE app_name=$3 AND user_id=$4 AND id=$5
                """,
                events_json,
                state_json,
                session.app_name,
                session.user_id,
                session.id,
            )
        return event