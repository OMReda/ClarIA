"""
test_upload.py — Test scenarios 1–5 (file upload + validation pipeline).

Scenario 1: Valid UTF-8 CSV → 201 + preview rows
Scenario 2: File too large → 400 FILE_TOO_LARGE
Scenario 3: Wrong file type (PNG) → 400 INVALID_FILE_TYPE
Scenario 4: French locale numbers + dates are normalised
Scenario 5: Latin-1 encoding is detected and parsed correctly
Scenario 6: Multi-sheet Excel → 201 needs_sheet_selection + sheet list
Scenario 7: Sheet selection → 200 + full preview

Note: tests share a session-scoped in-memory SQLite DB. Each test that
uploads a file uses a unique filename to avoid DUPLICATE_FILE 400 errors.
"""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.backend.conftest import (
    SAMPLE_ROWS,
    make_csv,
    make_csv_french_numbers,
    make_csv_latin1,
    make_csv_too_large,
    make_excel_bytes,
    make_png_bytes,
)


@pytest.mark.asyncio
async def test_s1_valid_csv_upload(client: AsyncClient):
    """Scenario 1: Valid UTF-8 CSV → 201 with columns and preview."""
    csv_bytes = make_csv(SAMPLE_ROWS)
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("ventes.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "validated"
    assert body["row_count"] == 3
    assert len(body["columns"]) == 3
    col_names = [c["name"] for c in body["columns"]]
    assert "region" in col_names
    assert "ventes" in col_names
    assert len(body["preview_rows"]) == 3
    assert body["preview_rows"][0]["region"] == "Nord"


@pytest.mark.asyncio
async def test_s2_file_too_large(client: AsyncClient):
    """Scenario 2: File exceeds 10MB → 400 FILE_TOO_LARGE."""
    big_bytes = make_csv_too_large(mb=11)
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("huge.csv", big_bytes, "text/csv")},
    )
    assert resp.status_code == 400
    err = resp.json()["detail"]["error"]
    assert err["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_s3_wrong_file_type(client: AsyncClient):
    """Scenario 3: PNG uploaded → 400 INVALID_FILE_TYPE."""
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("image.png", make_png_bytes(), "image/png")},
    )
    assert resp.status_code == 400
    err = resp.json()["detail"]["error"]
    assert err["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_s4_french_locale_normalisation(client: AsyncClient):
    """Scenario 4: French numbers (1 234,56) and dates (dd/mm/yyyy) are normalised."""
    csv_bytes = make_csv_french_numbers()
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("fr_ventes.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "validated"
    # After normalisation, ventes column values should be numeric
    preview = body["preview_rows"]
    assert len(preview) >= 1
    # The value 1 234,56 should become 1234.56
    ventes_val = preview[0].get("ventes")
    assert ventes_val is not None
    assert float(ventes_val) == pytest.approx(1234.56, rel=1e-3)


@pytest.mark.asyncio
async def test_s5_latin1_encoding(client: AsyncClient):
    """Scenario 5: Latin-1 encoded CSV is detected and parsed without error."""
    csv_bytes = make_csv_latin1()
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("latin1.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "validated"
    assert body["row_count"] == 1
    # "Dupont" must appear somewhere in the preview (no encoding crash)
    preview_text = str(body["preview_rows"])
    assert "Dupont" in preview_text



@pytest.mark.asyncio
async def test_s6_multisheet_excel(client: AsyncClient):
    """Scenario 6: Multi-sheet Excel → needs_sheet_selection with sheet list."""
    xlsx_bytes = make_excel_bytes({
        "Ventes 2023": SAMPLE_ROWS,
        "Ventes 2024": SAMPLE_ROWS,
    })
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("rapport.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "needs_sheet_selection"
    assert "Ventes 2023" in body["sheet_names"]
    assert "Ventes 2024" in body["sheet_names"]


@pytest.mark.asyncio
async def test_s7_sheet_selection(client: AsyncClient):
    """Scenario 7: After multi-sheet upload, selecting a sheet returns full preview."""
    unique_name = f"rapport_{uuid.uuid4().hex[:8]}.xlsx"
    xlsx_bytes = make_excel_bytes({
        "Ventes 2023": SAMPLE_ROWS,
        "Ventes 2024": SAMPLE_ROWS,
    })
    # Upload
    upload_resp = await client.post(
        "/api/v1/files",
        files={"file": (unique_name, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    file_id = upload_resp.json()["file_id"]

    # Select sheet
    select_resp = await client.post(
        f"/api/v1/files/{file_id}/sheet",
        json={"sheet_name": "Ventes 2023"},
    )
    assert select_resp.status_code == 200, select_resp.text
    body = select_resp.json()
    assert body["status"] == "validated"
    assert body["row_count"] == 3
    assert len(body["columns"]) == 3


@pytest.mark.asyncio
async def test_session_auto_created(client: AsyncClient):
    """Session is auto-created on first upload even if X-Session-ID is new."""
    unique_name = f"test_{uuid.uuid4().hex[:8]}.csv"
    csv_bytes = make_csv(SAMPLE_ROWS)
    resp = await client.post(
        "/api/v1/files",
        files={"file": (unique_name, csv_bytes, "text/csv")},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_empty_file_rejected(client: AsyncClient):
    """Empty file bytes → rejected."""
    resp = await client.post(
        "/api/v1/files",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400
