import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg_pool import AsyncConnectionPool, ConnectionPool

load_dotenv()

# Allow PlannerResponseFormat through msgpack deserialization even when
# LANGGRAPH_STRICT_MSGPACK=true is set. The env var alone doesn't work in this
# version — the allowlist must be passed to the serializer constructor.
_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[("common.types", "PlannerResponseFormat")]
)


def create_postgres_checkpointer() -> PostgresSaver:
    """Create a PostgresSaver backed by a connection pool.

    check=ConnectionPool.check_connection validates each connection before
    handing it out — bad or SSL-dropped connections are discarded and
    replaced automatically instead of raising mid-stream.
    """
    pool = ConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=5,
        kwargs={"autocommit": True},
        check=ConnectionPool.check_connection,
        reconnect_timeout=30,
        open=True,
    )
    checkpointer = PostgresSaver(pool, serde=_SERDE)
    checkpointer.setup()
    return checkpointer


async def create_async_postgres_checkpointer() -> AsyncPostgresSaver:
    """Async variant backed by an AsyncConnectionPool.

    check=AsyncConnectionPool.check_connection probes each connection before
    handing it out, so SSL connections dropped by Neon are discarded and
    replaced instead of raising mid-stream.
    max_lifetime/max_idle recycle connections before the server closes them.
    TCP keepalive options keep the underlying socket alive during long queries.
    """
    pool = AsyncConnectionPool(
        conninfo=os.getenv("DB_URI"),
        max_size=5,
        kwargs={"autocommit": True},
        check=AsyncConnectionPool.check_connection,
        max_lifetime=300,   # recycle connections after 5 min (before Neon kills them)
        max_idle=60,        # close connections idle for > 60 s
        reconnect_timeout=30,
        open=False,
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool, serde=_SERDE)
    await checkpointer.setup()
    return checkpointer
