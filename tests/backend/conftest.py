"""
conftest.py — Shared fixtures for backend tests.

Uses an in-memory SQLite database (via aiosqlite) for speed.
The DATABASE_URL env vars are set BEFORE any app imports to ensure
the module-level engine in database.py uses SQLite.
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

# ── Set env vars BEFORE any backend imports ───────────────────────────────────
_TEST_STORAGE = str(Path(__file__).parent / "_test_storage")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["STORAGE_PATH"] = _TEST_STORAGE
os.environ["LLM_PROVIDER"] = "local"

# ── Now safe to import backend modules ────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_async_session
from backend.core.security import get_current_user, User
from backend.main import app

# Re-create a test-specific engine with StaticPool so all connections share
# the same in-memory database across the session
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


# Override the dependency in the app
async def _override_get_session():
    async with _TestSessionLocal() as session:
        yield session

async def _override_get_current_user():
    return User(
        sub="testuser_sub",
        username="testuser",
        email="test@example.com",
        roles=["user"]
    )

app.dependency_overrides[get_async_session] = _override_get_session
app.dependency_overrides[get_current_user] = _override_get_current_user


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables once per session using the test engine."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def session_id() -> str:
    return str(uuid.uuid4())


# ── File factories ────────────────────────────────────────────────────────────

def make_csv(rows: list[dict]) -> bytes:
    import csv
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def make_csv_french_numbers() -> bytes:
    """CSV with French-formatted numbers and dates (semicolon separator)."""
    content = "region;ventes;date\nNord;1 234,56;01/03/2024\nSud;2 000,00;15/06/2024\n"
    return content.encode("latin-1")


def make_csv_latin1() -> bytes:
    """CSV with Latin-1 encoding and accented characters."""
    content = "nom;prenom;ville\nDupont;Fran\xe7ois;Orl\xe9ans\n"
    return content


def make_csv_too_large(mb: int = 11) -> bytes:
    """CSV that exceeds the file size limit."""
    header = b"col1,col2\n"
    row = b"a" * 1000 + b"," + b"b" * 1000 + b"\n"
    needed = (mb * 1024 * 1024 - len(header)) // len(row) + 1
    return header + row * needed


def make_png_bytes() -> bytes:
    """Minimal valid PNG header bytes (wrong file type)."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def make_excel_bytes(sheets: dict) -> bytes:
    """Create a minimal xlsx bytes object."""
    import pandas as pd
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, rows in sheets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet, index=False)
    return buf.getvalue()


SAMPLE_ROWS = [
    {"region": "Nord", "ventes": 100, "mois": "2024-01"},
    {"region": "Sud", "ventes": 200, "mois": "2024-02"},
    {"region": "Est", "ventes": 150, "mois": "2024-03"},
]
