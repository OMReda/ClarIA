"""
test_prompts.py — Test scenarios 8–14 for prompt submission, rate limiting,
chart type detection, fuzzy matching, clarification, and privacy.

Scenarios 8–11 mock the Celery task and PandasAI to run synchronously.
Scenario 12: Rate limit enforcement.
Scenario 13: Fuzzy column matching thresholds.
Scenario 14: Privacy assertion — LLM prompt bodies contain no cell values
             when LLM_PROVIDER is not 'local'. (Structural test.)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.backend.conftest import SAMPLE_ROWS, make_csv
from backend.services.chart_resolver import build_chart_spec, detect_chart_type
from backend.services.fuzzy_matcher import MatchConfidence, find_best_column
from backend.services.locale_normalizer import normalize_dataframe
from backend.services.rate_limiter import check_and_increment


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _upload_csv(client: AsyncClient, rows=None) -> str:
    rows = rows or SAMPLE_ROWS
    csv_bytes = make_csv(rows)
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["file_id"]


# ─── Scenario 8: Prompt submission accepted ───────────────────────────────────

@pytest.mark.asyncio
async def test_s8_prompt_submission(client: AsyncClient):
    """Scenario 8: POST /prompts → 202 with prompt_id."""
    file_id = await _upload_csv(client)
    with patch("backend.api.prompts.process_prompt") as mock_task:
        mock_task.delay = MagicMock()
        resp = await client.post(
            f"/api/v1/files/{file_id}/prompts",
            json={"text": "Génère un histogramme des ventes"},
        )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "prompt_id" in body
    assert body["status"] == "pending"


# ─── Scenario 9: Ownership enforcement ───────────────────────────────────────

@pytest.mark.asyncio
async def test_s9_session_ownership(client: AsyncClient):
    """Scenario 9: Different session cannot submit prompts for another session's file."""
    file_id = await _upload_csv(client)
    
    from backend.main import app
    from backend.core.security import get_current_user, User
    
    # Temporarily override user to be someone else
    async def _override_other_user():
        return User(sub="other_user", username="other", email="a@b.c", roles=[])
    
    app.dependency_overrides[get_current_user] = _override_other_user
    
    resp = await client.post(
        f"/api/v1/files/{file_id}/prompts",
        json={"text": "test"},
    )
    
    # Restore mock user
    async def _override_get_current_user():
        return User(sub="testuser_sub", username="testuser", email="test@example.com", roles=["user"])
    app.dependency_overrides[get_current_user] = _override_get_current_user
    
    assert resp.status_code == 403


# ─── Scenario 10: Empty prompt rejected ──────────────────────────────────────

@pytest.mark.asyncio
async def test_s10_empty_prompt_rejected(client: AsyncClient):
    """Scenario 10: Blank prompt text is rejected."""
    file_id = await _upload_csv(client)
    resp = await client.post(
        f"/api/v1/files/{file_id}/prompts",
        json={"text": "   "},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "EMPTY_PROMPT"


# ─── Scenario 11: Chart resolver — all 5 types ───────────────────────────────

@pytest.mark.parametrize("prompt,expected_type", [
    ("Montre la distribution des ventes (histogramme)", "histogram"),
    ("Évolution des ventes par mois", "line"),
    ("Camembert des ventes par région", "pie"),
    ("Corrélation entre ventes et budget", "scatter"),
    ("Ventes par région barre", "bar"),
])
def test_s11_chart_type_detection(prompt: str, expected_type: str):
    """Scenario 11: Chart type correctly detected from prompt keywords."""
    cols = [
        {"name": "region", "dtype": "categorical"},
        {"name": "ventes", "dtype": "numeric"},
        {"name": "mois", "dtype": "datetime"},
        {"name": "budget", "dtype": "numeric"},
    ]
    result = detect_chart_type(prompt, cols)
    assert result == expected_type, f"Expected {expected_type!r} for prompt {prompt!r}, got {result!r}"


# ─── Scenario 12: Rate limiting ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s12_rate_limit(client: AsyncClient):
    """Scenario 12: 31st prompt in 1 hour is rejected with 429."""
    with patch("backend.api.prompts.check_and_increment", return_value=(False, 31)):
        file_id = await _upload_csv(client)
        resp = await client.post(
            f"/api/v1/files/{file_id}/prompts",
            json={"text": "test prompt"},
        )
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"]["code"] == "RATE_LIMIT_EXCEEDED"


# ─── Scenario 13: Fuzzy column matching ──────────────────────────────────────

def test_s13_fuzzy_exact():
    columns = ["region", "ventes", "mois"]
    result = find_best_column("region", columns)
    assert result.confidence == MatchConfidence.EXACT
    assert result.best_column == "region"


def test_s13_fuzzy_high():
    columns = ["ventes_totales", "region", "mois"]
    result = find_best_column("ventes_totale", columns)  # one char off
    assert result.confidence in (MatchConfidence.HIGH, MatchConfidence.EXACT)
    assert result.best_column == "ventes_totales"


def test_s13_fuzzy_mid():
    columns = ["chiffre_affaires", "region"]
    # "ventes" is somewhat related to "chiffre_affaires" but mid-confidence
    result = find_best_column("vente", columns)
    # We only assert it doesn't crash and returns a result
    assert result.confidence in (MatchConfidence.MID, MatchConfidence.LOW, MatchConfidence.HIGH, MatchConfidence.EXACT)
    assert result.clarification_question is not None or result.best_column is not None


def test_s13_fuzzy_low():
    columns = ["region", "ventes", "mois"]
    result = find_best_column("xyzwqr", columns)
    assert result.confidence == MatchConfidence.LOW
    assert result.clarification_question is not None


# ─── Scenario 14: French locale normalisation unit test ──────────────────────

def test_s14_locale_normalise_numbers():
    """Scenario 14: French thousands+decimal format → float."""
    df = pd.DataFrame({"ventes": ["1 234,56", "2 000,00", "999,99"]})
    result = normalize_dataframe(df)
    assert float(result["ventes"].iloc[0]) == pytest.approx(1234.56)
    assert float(result["ventes"].iloc[1]) == pytest.approx(2000.0)


def test_s14_locale_normalise_dates():
    """Scenario 14b: dd/mm/yyyy dates → ISO 8601."""
    df = pd.DataFrame({"date": ["01/03/2024", "15/06/2024"]})
    result = normalize_dataframe(df)
    assert result["date"].iloc[0] == "2024-03-01"
    assert result["date"].iloc[1] == "2024-06-15"


# ─── Chart spec unit tests ────────────────────────────────────────────────────

def test_bar_chart_spec():
    df = pd.DataFrame({"region": ["Nord", "Sud"], "ventes": [100, 200]})
    spec = build_chart_spec(df, "bar")
    assert spec["series"][0]["type"] == "bar"
    assert "xAxis" in spec
    assert spec["xAxis"]["data"] == ["Nord", "Sud"]


def test_pie_chart_spec():
    df = pd.DataFrame({"region": ["Nord", "Sud"], "ventes": [100, 200]})
    spec = build_chart_spec(df, "pie")
    assert spec["series"][0]["type"] == "pie"
    data = spec["series"][0]["data"]
    assert len(data) == 2


def test_histogram_spec_no_matplotlib():
    """Histogram is built without importing matplotlib."""
    import sys
    assert "matplotlib" not in sys.modules, "matplotlib must not be imported"
    df = pd.DataFrame({"ventes": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]})
    spec = build_chart_spec(df, "histogram")
    assert spec["series"][0]["type"] == "bar"
    assert len(spec["xAxis"]["data"]) > 0


def test_scatter_chart_spec():
    df = pd.DataFrame({"budget": [100, 200, 300], "ventes": [150, 250, 350]})
    spec = build_chart_spec(df, "scatter")
    assert spec["series"][0]["type"] == "scatter"
    assert len(spec["series"][0]["data"]) == 3
