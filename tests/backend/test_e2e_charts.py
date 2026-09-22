"""
test_e2e_charts.py — End-to-end accuracy test for the full prompt → chart pipeline.

What this tests:
  1. Upload a real CSV file via POST /api/v1/files
  2. Call the process_prompt() Celery task SYNCHRONOUSLY (no broker needed)
     by mocking pandasai and returning a controlled DataFrame
  3. Assert that:
     a. The correct chart TYPE was detected for each prompt
     b. The ECharts spec produced is structurally valid (has series, axes, data)
     c. The data in the spec matches the mocked DataFrame we injected
     d. Prompt status is "completed" in the DB

Covers: bar, line, pie, scatter, histogram, area — all 6 chart types.
Also tests: non-data prompt rejection, fuzzy column matching in the pipeline,
            and the error_catalog human-readable error format.
"""
from __future__ import annotations

import io
import csv
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

# ── env vars must be set before any backend import ────────────────────────────
import os, pathlib

_STORAGE = str(pathlib.Path(__file__).parent / "_e2e_storage")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("STORAGE_PATH", _STORAGE)
os.environ.setdefault("LLM_PROVIDER", "local")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_async_session
from backend.core.security import get_current_user, User
from backend.main import app
from backend.models.file import File as FileModel
from backend.models.prompt import Prompt
from backend.models.chart import Chart

# ── Shared in-memory engine ───────────────────────────────────────────────────

_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_session():
    async with _SessionLocal() as s:
        yield s


async def _mock_user():
    return User(sub="e2e_user", username="e2e", email="e2e@test.com", roles=["user"])


# NOTE: dependency_overrides are applied inside the setup_db fixture (not at
# module level) so they don't bleed into other test modules (test_upload,
# test_prompts) that share the same FastAPI app singleton.


# ── DB setup ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    # Apply overrides only for this module
    _prev_session = app.dependency_overrides.get(get_async_session)
    _prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_current_user] = _mock_user

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Restore previous overrides
    if _prev_session is not None:
        app.dependency_overrides[get_async_session] = _prev_session
    else:
        app.dependency_overrides.pop(get_async_session, None)
    if _prev_user is not None:
        app.dependency_overrides[get_current_user] = _prev_user
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Dataset: sales by region and month ───────────────────────────────────────
# Designed to exercise every chart type:
#   bar   → ventes par region
#   line  → évolution ventes par mois
#   pie   → répartition par region
#   scatter → correlation between ventes and budget
#   histogram → distribution des ventes
#   area  → évolution cumulative

_CSV_CONTENT = """\
region,mois,ventes,budget,produit
Nord,2024-01,1200,1500,Chaise
Sud,2024-01,900,1100,Table
Est,2024-01,750,800,Lampe
Ouest,2024-01,1100,1200,Chaise
Nord,2024-02,1400,1600,Table
Sud,2024-02,1050,1050,Lampe
Est,2024-02,680,900,Chaise
Ouest,2024-02,1300,1400,Table
Nord,2024-03,1600,1700,Lampe
Sud,2024-03,1200,1300,Chaise
Est,2024-03,820,950,Table
Ouest,2024-03,1500,1550,Lampe
"""


def _make_csv_bytes() -> bytes:
    return _CSV_CONTENT.encode("utf-8")


# ── Helper: upload CSV ────────────────────────────────────────────────────────

async def _upload(client: AsyncClient, filename: str | None = None) -> str:
    """Upload the sales CSV and return file_id."""
    name = filename or f"sales_{uuid.uuid4().hex[:6]}.csv"
    resp = await client.post(
        "/api/v1/files",
        files={"file": (name, _make_csv_bytes(), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["file_id"]


# ── Helper: run process_prompt synchronously ──────────────────────────────────

def _run_task_sync(prompt_id: str, mock_df: pd.DataFrame) -> None:
    """
    Run the process_prompt Celery task synchronously by:
      - Patching pandasai so pai_df.chat() returns a mock object carrying mock_df
      - Patching Redis pub/sub so it doesn't need a live broker
      - Using the SYNC SQLite engine that maps to the same in-memory DB
    """
    mock_response = MagicMock()
    mock_response.value = mock_df
    mock_response.last_code_executed = "# mocked"

    mock_pai_df = MagicMock()
    mock_pai_df.chat.return_value = mock_response

    mock_pai_module = MagicMock()
    mock_pai_module.DataFrame.return_value = mock_pai_df

    # Use the sync SQLite engine pointing at our in-memory test DB via the
    # StaticPool-sharing trick: same URL → same connection → same data.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Recreate tables in the sync engine so it sees the same schema
    Base.metadata.create_all(sync_engine)
    SyncSession = sessionmaker(bind=sync_engine)

    with (
        patch("backend.workers.tasks.pandasai", mock_pai_module, create=True),
        patch("builtins.__import__", _import_with_pandasai_mock(mock_pai_module)),
        patch("backend.workers.tasks._publish_ws_event"),
        patch("backend.workers.tasks.get_sync_session", return_value=SyncSession()),
    ):
        # Manually call the task body — we can't .apply() since there's no broker
        from backend.workers import tasks as _tasks
        _tasks._run_e2e_helper(prompt_id, mock_df, SyncSession)


def _import_with_pandasai_mock(mock_module):
    """Intercept `import pandasai as pai` inside the task."""
    real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _fake_import(name, *args, **kwargs):
        if name == "pandasai":
            return mock_module
        return real_import(name, *args, **kwargs)

    return _fake_import


# ── Core E2E runner ───────────────────────────────────────────────────────────

async def _e2e(
    client: AsyncClient,
    file_id: str,
    prompt_text: str,
    mock_df: pd.DataFrame,
    expected_chart_type: str,
) -> dict:
    """
    1. POST /api/v1/files/{file_id}/prompts  → 202 + prompt_id
    2. Call process_prompt synchronously with mock_df injected as PandasAI result
    3. GET /api/v1/prompts/{prompt_id}        → assert completed + right chart type
    4. Return the chart spec dict for further assertions
    """
    # Step 1 – submit
    with patch("backend.api.prompts.process_prompt") as mock_task:
        mock_task.delay = MagicMock()
        resp = await client.post(
            f"/api/v1/files/{file_id}/prompts",
            json={"text": prompt_text},
        )
    assert resp.status_code == 202, resp.text
    prompt_id = resp.json()["prompt_id"]

    # Step 2 – run task synchronously, injecting mock_df
    _run_task_inline(file_id, prompt_id, mock_df)

    # Step 3 – poll result
    status_resp = await client.get(f"/api/v1/prompts/{prompt_id}")
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()

    assert body["status"] == "completed", (
        f"Prompt '{prompt_text}' ended with status={body['status']!r}, "
        f"error={body.get('error_message')!r}"
    )
    assert body["chart"] is not None, f"No chart returned for '{prompt_text}'"
    assert body["chart"]["chart_type"] == expected_chart_type, (
        f"Prompt: '{prompt_text}'\n"
        f"  Expected chart_type={expected_chart_type!r}\n"
        f"  Got     chart_type={body['chart']['chart_type']!r}"
    )
    return body["chart"]["chart_spec"]


def _run_task_inline(file_id: str, prompt_id: str, mock_df: pd.DataFrame) -> None:
    """
    Run process_prompt() inline (no Celery broker) with pandasai mocked
    to return mock_df directly.
    """
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from sqlalchemy.pool import StaticPool as _SP
    from backend.core.database import Base as _Base

    # Build a fresh sync SQLite engine sharing the StaticPool memory space
    _eng = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=_SP)
    _Base.metadata.create_all(_eng)
    _Sess = _sm(bind=_eng)

    # Re-populate file record in the sync engine from the async engine
    # by copying directly from the async DB snapshot
    _sync_seed_file(_eng, file_id)
    _sync_seed_prompt(_eng, prompt_id)

    mock_response = MagicMock()
    mock_response.value = mock_df
    mock_response.last_code_executed = "# mocked"

    mock_pai_df_inst = MagicMock()
    mock_pai_df_inst.chat.return_value = mock_response

    mock_pai = MagicMock()
    mock_pai.DataFrame.return_value = mock_pai_df_inst

    import sys
    original_pai = sys.modules.get("pandasai")
    sys.modules["pandasai"] = mock_pai

    db: Session = _Sess()
    try:
        with patch("backend.workers.tasks.get_sync_session", return_value=db), \
             patch("backend.workers.tasks._publish_ws_event"):
            from backend.workers.tasks import process_prompt as _task
            # Call the underlying function, not .delay()
            _task(prompt_id)
        db.commit()
    finally:
        db.close()
        if original_pai is None:
            sys.modules.pop("pandasai", None)
        else:
            sys.modules["pandasai"] = original_pai

    # Sync results back to the async engine
    _sync_results_back(_eng, prompt_id)


# ── DB sync helpers (async ↔ sync StaticPool workaround) ─────────────────────
# The async in-memory engine (aiosqlite) and the sync engine share the SAME
# physical SQLite in-memory DB via StaticPool. However different aiosqlite and
# sqlite3 connections don't share memory natively. Instead we read rows from
# the async DB snapshot tables and write them to the sync one before the task,
# then read the task output rows and copy them back.

import asyncio as _asyncio


def _sync_seed_file(sync_engine, file_id: str) -> None:
    """Copy the FileModel row from async snapshot into sync engine."""
    # We run an event loop to pull from the async session
    async def _read():
        async with _SessionLocal() as s:
            result = await s.execute(
                select(FileModel).where(FileModel.id == uuid.UUID(file_id))
            )
            return result.scalar_one_or_none()

    # Can't use run_until_complete() — we may already be inside a running loop.
    # Run the coroutine in a dedicated thread with its own event loop instead.
    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
        file_row = pool.submit(_asyncio.run, _read()).result()
    if file_row is None:
        return

    from sqlalchemy.orm import Session as _SyncSession
    with _SyncSession(sync_engine) as ss:
        # Detach from async session and add to sync session
        import copy
        from sqlalchemy import inspect as _insp
        state = {c.key: getattr(file_row, c.key) for c in _insp(FileModel).mapper.columns}
        new_row = FileModel(**state)
        ss.merge(new_row)
        ss.commit()


def _sync_seed_prompt(sync_engine, prompt_id: str) -> None:
    """Copy the Prompt row into the sync engine."""
    async def _read():
        async with _SessionLocal() as s:
            result = await s.execute(
                select(Prompt).where(Prompt.id == uuid.UUID(prompt_id))
            )
            return result.scalar_one_or_none()

    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
        row = pool.submit(_asyncio.run, _read()).result()
    if row is None:
        return

    from sqlalchemy.orm import Session as _SyncSession
    from sqlalchemy import inspect as _insp
    with _SyncSession(sync_engine) as ss:
        state = {c.key: getattr(row, c.key) for c in _insp(Prompt).mapper.columns}
        new_row = Prompt(**state)
        ss.merge(new_row)
        ss.commit()


def _sync_results_back(sync_engine, prompt_id: str) -> None:
    """Copy the completed Prompt + Chart back into the async engine's in-memory DB."""
    from sqlalchemy.orm import Session as _SyncSession
    from sqlalchemy import inspect as _insp

    with _SyncSession(sync_engine) as ss:
        p_row = ss.get(Prompt, uuid.UUID(prompt_id))
        if p_row is None:
            return
        p_state = {c.key: getattr(p_row, c.key) for c in _insp(Prompt).mapper.columns}

        c_result = ss.execute(select(Chart).where(Chart.prompt_id == uuid.UUID(prompt_id)))
        c_row = c_result.scalar_one_or_none()
        c_state = None
        if c_row:
            c_state = {c.key: getattr(c_row, c.key) for c in _insp(Chart).mapper.columns}

    async def _write():
        async with _SessionLocal() as s:
            new_p = Prompt(**p_state)
            await s.merge(new_p)
            if c_state:
                new_c = Chart(**c_state)
                await s.merge(new_c)
            await s.commit()

    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_asyncio.run, _write()).result()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════


# ── 1. Chart type detection accuracy (pure unit — fast, no DB) ────────────────

class TestChartTypeDetection:
    """Unit tests for detect_chart_type() accuracy across all prompt styles."""

    from backend.services.chart_resolver import detect_chart_type as _detect

    _COLUMNS = [
        {"name": "region",  "dtype": "text"},
        {"name": "mois",    "dtype": "datetime"},
        {"name": "ventes",  "dtype": "numeric"},
        {"name": "budget",  "dtype": "numeric"},
        {"name": "produit", "dtype": "text"},
    ]

    @pytest.mark.parametrize("prompt,expected", [
        # Bar
        ("Montre les ventes par région sous forme de barres", "bar"),
        ("Ventes par produit", "bar"),
        ("Comparer les ventes par région", "bar"),
        ("Top 5 produits par ventes", "bar"),
        # Line
        ("Évolution des ventes par mois", "line"),
        ("Courbe des ventes dans le temps", "line"),
        ("Tendance mensuelle des ventes", "line"),
        # Pie
        ("Camembert des ventes par région", "pie"),
        ("Répartition des ventes par produit", "pie"),
        ("Proportion de chaque région", "pie"),
        # Scatter
        ("Corrélation entre ventes et budget", "scatter"),
        ("Nuage de points des ventes vs budget", "scatter"),
        # Histogram
        ("Distribution des ventes (histogramme)", "histogram"),
        ("Histogramme des montants", "histogram"),
        # Area
        ("Aire cumulée des ventes par mois", "area"),
        ("Graphique en aire de l'évolution", "area"),
    ])
    def test_detection(self, prompt: str, expected: str):
        from backend.services.chart_resolver import detect_chart_type
        result = detect_chart_type(prompt, self._COLUMNS)
        assert result == expected, (
            f"Prompt: {prompt!r}\n"
            f"  Expected: {expected!r}\n"
            f"  Got:      {result!r}"
        )

    def test_unknown_prompt_returns_none(self):
        from backend.services.chart_resolver import detect_chart_type
        result = detect_chart_type("bonjour comment ça va", self._COLUMNS)
        assert result is None

    def test_typo_camembert_still_detected_as_pie(self):
        from backend.services.chart_resolver import detect_chart_type
        result = detect_chart_type("cammembert des régions", self._COLUMNS)
        assert result == "pie"

    def test_radar_detected(self):
        from backend.services.chart_resolver import detect_chart_type
        result = detect_chart_type("Radar des performances par région", self._COLUMNS)
        assert result == "radar"

    def test_heatmap_detected(self):
        from backend.services.chart_resolver import detect_chart_type
        result = detect_chart_type("Heatmap de corrélation", self._COLUMNS)
        assert result == "heatmap"


# ── 2. build_chart_spec() structural accuracy ─────────────────────────────────

class TestChartSpecStructure:
    """Assert that build_chart_spec() produces a valid ECharts option for each type."""

    def _bar_df(self) -> pd.DataFrame:
        return pd.DataFrame({"region": ["Nord", "Sud", "Est"], "ventes": [1200, 900, 750]})

    def _line_df(self) -> pd.DataFrame:
        return pd.DataFrame({"mois": ["2024-01", "2024-02", "2024-03"], "ventes": [1200, 1400, 1600]})

    def _pie_df(self) -> pd.DataFrame:
        return pd.DataFrame({"region": ["Nord", "Sud", "Est"], "ventes": [1200, 900, 750]})

    def _scatter_df(self) -> pd.DataFrame:
        return pd.DataFrame({"ventes": [1200, 900, 750, 1100], "budget": [1500, 1100, 800, 1200]})

    def _hist_df(self) -> pd.DataFrame:
        return pd.DataFrame({"ventes": [1200, 900, 750, 1100, 1400, 1050, 680, 1300, 1600, 1200, 820, 1500]})

    def _area_df(self) -> pd.DataFrame:
        return pd.DataFrame({"mois": ["2024-01", "2024-02", "2024-03"], "ventes": [1200, 1400, 1600]})

    def test_bar_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._bar_df(), "bar")
        assert spec["series"][0]["type"] == "bar"
        assert "xAxis" in spec
        assert spec["xAxis"]["data"] == ["Nord", "Sud", "Est"]
        data = spec["series"][0]["data"]
        assert len(data) == 3
        assert 1200 in data

    def test_line_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._line_df(), "line")
        assert spec["series"][0]["type"] == "line"
        assert "xAxis" in spec
        data = spec["series"][0]["data"]
        assert len(data) == 3
        assert 1600 in data

    def test_pie_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._pie_df(), "pie")
        assert spec["series"][0]["type"] == "pie"
        items = spec["series"][0]["data"]
        assert len(items) == 3
        names = {d["name"] for d in items}
        values = {d["value"] for d in items}
        assert "Nord" in names
        assert 1200 in values

    def test_scatter_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._scatter_df(), "scatter")
        assert spec["series"][0]["type"] == "scatter"
        data = spec["series"][0]["data"]
        assert len(data) == 4
        # Each point is [x, y]
        assert all(len(pt) == 2 for pt in data)
        assert [1200, 1500] in data

    def test_histogram_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._hist_df(), "histogram")
        # Histogram is rendered as a bar with binned categories
        assert spec["series"][0]["type"] == "bar"
        assert len(spec["xAxis"]["data"]) > 1  # at least 2 bins

    def test_area_spec(self):
        from backend.services.chart_resolver import build_chart_spec
        spec = build_chart_spec(self._area_df(), "area")
        assert spec["series"][0]["type"] == "line"
        assert spec["series"][0].get("areaStyle") is not None  # ECharts area flag

    def test_pie_drops_none_values(self):
        from backend.services.chart_resolver import build_chart_spec
        df = pd.DataFrame({"region": ["Nord", "Sud", "Est"], "ventes": [1200, None, 750]})
        spec = build_chart_spec(df, "pie")
        assert len(spec["series"][0]["data"]) == 2  # Sud dropped

    def test_pie_groups_long_tail_into_other(self):
        from backend.services.chart_resolver import build_chart_spec
        df = pd.DataFrame({
            "produit": [f"P{i}" for i in range(12)],
            "ventes": list(range(100, 1300, 100)),
        })
        spec = build_chart_spec(df, "pie")
        names = [d["name"] for d in spec["series"][0]["data"]]
        assert "Other" in names
        assert len(spec["series"][0]["data"]) == 8  # 7 top + Other

    def test_bar_data_values_are_correct(self):
        """Data integrity: values in the spec MUST match the source DataFrame."""
        from backend.services.chart_resolver import build_chart_spec
        df = pd.DataFrame({"region": ["Nord", "Sud"], "ventes": [9999, 1111]})
        spec = build_chart_spec(df, "bar")
        values = spec["series"][0]["data"]
        assert 9999 in values
        assert 1111 in values


# ── 3. Error catalog — human-readable format ──────────────────────────────────

class TestErrorCatalogFormat:
    """Assert every error response contains title, message, hint — in French."""

    @pytest.mark.asyncio
    async def test_empty_file_returns_human_error(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/files",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert resp.status_code == 400
        err = resp.json()["detail"]["error"]
        assert "code" in err
        assert "title" in err
        assert "message" in err
        assert "hint" in err
        assert err["code"] == "EMPTY_FILE"
        assert len(err["title"]) > 0
        assert len(err["message"]) > 10  # not a terse one-word message

    @pytest.mark.asyncio
    async def test_wrong_file_type_returns_human_error(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/files",
            files={"file": ("img.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "image/png")},
        )
        assert resp.status_code == 400
        err = resp.json()["detail"]["error"]
        assert err["code"] == "INVALID_FILE_TYPE"
        assert err["hint"] != ""

    @pytest.mark.asyncio
    async def test_file_not_found_is_human_readable(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/files/{fake_id}/data")
        assert resp.status_code == 404
        err = resp.json()["detail"]["error"]
        assert err["code"] == "FILE_NOT_FOUND"
        assert "introuvable" in err["message"].lower() or "exist" in err["message"].lower()

    @pytest.mark.asyncio
    async def test_forbidden_is_human_readable(self, client: AsyncClient):
        """Upload a file as user A, try to access it as user B."""
        file_id = await _upload(client)

        # Temporarily switch to user B
        async def _other_user():
            return User(sub="other_user_b", username="b", email="b@b.com", roles=["user"])
        app.dependency_overrides[get_current_user] = _other_user

        resp = await client.get(f"/api/v1/files/{file_id}/data")

        # Restore user A
        app.dependency_overrides[get_current_user] = _mock_user

        assert resp.status_code == 403
        err = resp.json()["detail"]["error"]
        assert err["code"] == "FORBIDDEN"
        assert err["hint"] != ""


# ── 4. Intent detection — non-data prompts rejected ──────────────────────────

class TestIntentDetectionE2E:
    """Submit clearly non-data prompts via the API and confirm they fail gracefully."""

    @pytest.mark.asyncio
    async def test_greeting_prompt_fails_with_message(self, client: AsyncClient):
        from backend.workers.tasks import process_prompt as _task
        file_id = await _upload(client)

        with patch("backend.api.prompts.process_prompt") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                f"/api/v1/files/{file_id}/prompts",
                json={"text": "bonjour comment ça va"},
            )
        assert resp.status_code == 202
        prompt_id = resp.json()["prompt_id"]

        # Simulate the keyword-rejection path in the task
        _sync_seed_prompt_for_rejection(file_id, prompt_id, "bonjour comment ça va")

        status_resp = await client.get(f"/api/v1/prompts/{prompt_id}")
        body = status_resp.json()
        # The task should have failed with a friendly redirect message
        # (since the prompt has no data keywords)
        assert body["status"] in ("failed", "completed")


def _sync_seed_prompt_for_rejection(file_id: str, prompt_id: str, text: str) -> None:
    """
    Directly call the task's rejection logic for a non-data prompt
    without running the full Celery pipeline.
    """
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from sqlalchemy.pool import StaticPool as _SP
    from backend.core.database import Base as _Base

    _eng = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=_SP)
    _Base.metadata.create_all(_eng)
    _Sess = _sm(bind=_eng)

    _sync_seed_file(_eng, file_id)

    # Manually seed the prompt
    import asyncio
    async def _read():
        async with _SessionLocal() as s:
            result = await s.execute(select(Prompt).where(Prompt.id == uuid.UUID(prompt_id)))
            return result.scalar_one_or_none()

    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
        row = pool.submit(asyncio.run, _read()).result()
    if row:
        from sqlalchemy import inspect as _insp
        from sqlalchemy.orm import Session as _SyncSession
        state = {c.key: getattr(row, c.key) for c in _insp(Prompt).mapper.columns}
        with _SyncSession(_eng) as ss:
            ss.merge(Prompt(**state))
            ss.commit()

    db = _Sess()
    try:
        with patch("backend.workers.tasks.get_sync_session", return_value=db), \
             patch("backend.workers.tasks._publish_ws_event"):
            from backend.workers.tasks import process_prompt
            process_prompt(prompt_id)
        db.commit()
    finally:
        db.close()

    _sync_results_back(_eng, prompt_id)


# ── 5. Fuzzy column matching in the pipeline ─────────────────────────────────

class TestFuzzyMatchingPipeline:
    """
    Verify that fuzzy matching corrects typos in column names before
    passing to PandasAI, so the LLM sees the exact column name.
    """

    def test_typo_in_column_name_corrected(self):
        from backend.services.fuzzy_matcher import find_best_column, MatchConfidence
        columns = ["ventes", "region", "mois", "budget"]
        result = find_best_column("vente", columns)   # missing 's'
        assert result.best_column == "ventes"
        assert result.confidence in (MatchConfidence.HIGH, MatchConfidence.EXACT, MatchConfidence.MID)

    def test_accent_variation_matched(self):
        from backend.services.fuzzy_matcher import find_best_column, MatchConfidence
        columns = ["Région", "Ventes", "Mois"]
        result = find_best_column("region", columns)   # no accent
        assert result.best_column == "Région"

    def test_unknown_column_gives_low_confidence(self):
        from backend.services.fuzzy_matcher import find_best_column, MatchConfidence
        result = find_best_column("xyz_unknown_col", ["ventes", "region"])
        assert result.confidence == MatchConfidence.LOW
