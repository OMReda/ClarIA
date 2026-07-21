from __future__ import annotations

import uuid
from sqlalchemy import create_engine, TypeDecorator, CHAR
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import get_settings

settings = get_settings()

def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


# ── Async engine (FastAPI routes) ─────────────────────────────────────────────
_async_engine_kwargs: dict = {"pool_pre_ping": True}
if not _is_sqlite(settings.database_url):
    _async_engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

async_engine = create_async_engine(settings.database_url, **_async_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# ── Sync engine (Celery tasks) ────────────────────────────────────────────────
_sync_engine_kwargs: dict = {"pool_pre_ping": True}
if not _is_sqlite(settings.database_url_sync):
    _sync_engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

sync_engine = create_engine(settings.database_url_sync, **_sync_engine_kwargs)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses PostgreSQL's UUID natively, stores as CHAR(36) on SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return str(value)
        return str(value) if isinstance(value, uuid.UUID) else str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(str(value))


class Base(DeclarativeBase):
    pass


async def get_async_session():
    """FastAPI dependency — async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_session() -> Session:
    """Celery tasks — sync DB session (context manager)."""
    return SyncSessionLocal()
