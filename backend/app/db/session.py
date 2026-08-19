"""Database engine, session factory, and FastAPI dependency.

Uses SQLAlchemy async (asyncpg driver). The engine reads DATABASE_URL from
the Settings singleton so the same code works locally, in Docker, and in CI.

Startup:
    Call `await init_db()` once at application startup (done in main.py via
    the FastAPI lifespan hook). It runs schema.sql so the tables always exist
    without needing a separate migration step for development.

Unit tests:
    Tests do NOT need Postgres — the pipeline, gate, and agents are all pure
    functions with no DB dependency. Only the router layer uses get_db().
"""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from ..config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine — created once at import time; reused for the lifetime of the process.
# Convert postgres:// → postgresql+asyncpg:// if needed.
# ---------------------------------------------------------------------------
_raw_url = settings.database_url
if _raw_url.startswith("postgresql://"):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    _async_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    _async_url = _raw_url  # already has the right prefix

engine = create_async_engine(
    _async_url,
    echo=settings.debug,
    pool_pre_ping=True,       # drop stale connections before use
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # avoid lazy-load errors after commit
)

# ---------------------------------------------------------------------------
# Startup helper — idempotent, safe to call on every restart.
# ---------------------------------------------------------------------------
_SCHEMA_SQL = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    """Execute schema.sql to ensure all tables exist.

    Uses CREATE TABLE IF NOT EXISTS throughout, so this is safe to call on a
    database that already has the correct schema (no-op). Logs a warning and
    continues if the DB is unreachable (lets the app start so /health works
    even when Postgres is still coming up).
    """
    try:
        schema = _SCHEMA_SQL.read_text(encoding="utf-8")
        async with engine.begin() as conn:
            await conn.execute(text(schema))
        log.info("init_db: schema applied / verified OK")
    except Exception as exc:  # noqa: BLE001
        log.warning("init_db: could not reach DB — %s. Continuing without schema init.", exc)


# ---------------------------------------------------------------------------
# FastAPI dependency — inject into route handlers via Depends(get_db).
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:  # type: ignore[return]
    """Yield an async DB session; commit on success, rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
