"""
files.py — File upload, validation, sheet selection, and preview endpoints.

POST /api/v1/files              — upload + validate
POST /api/v1/files/{id}/sheet  — select sheet for multi-sheet xlsx
"""
from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.database import get_async_session
from backend.core.error_catalog import user_error
from backend.core.security import get_current_user, User
from backend.models.file import File as FileModel
from backend.models.prompt import Prompt as PromptModel
from backend.models.chart import Chart as ChartModel
from backend.services.file_validator import (
    FileValidationError,
    build_columns_metadata,
    build_preview_rows,
    check_file_size,
    check_row_count,
    detect_content_type,
    load_dataframe_from_path,
    read_csv_safe,
    read_excel_safe,
    save_upload,
)

router = APIRouter(prefix="/api/v1/files", tags=["files"])
settings = get_settings()


# ── Response schemas ──────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    missing_count: int


class FileUploadResponse(BaseModel):
    file_id: str
    status: str
    row_count: Optional[int] = None
    columns: Optional[List[ColumnInfo]] = None
    preview_rows: Optional[List[Dict[str, Any]]] = None
    # sheet_names is empty for CSVs / single-sheet Excels.
    # We use Field(default_factory=list) so it always serializes to [] instead of null.
    sheet_names: List[str] = Field(default_factory=list)


class SheetSelectBody(BaseModel):
    sheet_name: str


class FileDataResponse(BaseModel):
    data: List[Dict[str, Any]]
    is_truncated: bool
    total_rows: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ve(exc: FileValidationError) -> HTTPException:
    """Convert a FileValidationError into a user_error HTTPException."""
    # exc.details carries template format values (e.g. max_size_mb, received_rows).
    # We pass them as both details= (for the structured payload) and **fmt_kwargs
    # (for message template interpolation). Filter out any keys that overlap with
    # user_error's own named parameters to avoid TypeError on duplicate kwargs.
    _RESERVED = {"code", "http_status", "details"}
    fmt_kwargs = {k: v for k, v in exc.details.items() if k not in _RESERVED}
    return user_error(exc.code, details=exc.details, **fmt_kwargs)




# ── POST /api/v1/files ────────────────────────────────────────────────────────

@router.post("", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    # ── Read raw bytes (stream-check size first) ─────────────────────────────
    raw_bytes = await file.read()
    try:
        check_file_size(len(raw_bytes))
    except FileValidationError as exc:
        raise _ve(exc)

    # ── Check for duplicate filename ──────────────────────────────────────────
    filename = file.filename or "upload"
    stmt = select(FileModel).where(
        FileModel.owner_id == user.sub,
        FileModel.original_filename == filename,
        FileModel.status != "error"
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise user_error("DUPLICATE_FILE")

    if len(raw_bytes) == 0:
        raise user_error("EMPTY_FILE")

    # ── Content-signature validation ─────────────────────────────────────────
    try:
        file_type = detect_content_type(raw_bytes[:2048], filename=file.filename or "")
    except FileValidationError as exc:
        raise _ve(exc)

    # ── Parse file ────────────────────────────────────────────────────────────
    file_id = uuid.uuid4()
    storage_path = save_upload(raw_bytes, file.filename or "upload", str(file_id))

    sheet_names: Optional[List[str]] = None
    selected_sheet: Optional[str] = None
    df = None

    try:
        if file_type in ("xlsx", "xls"):
            df, sheet_names = read_excel_safe(raw_bytes, sheet_name=None)
            if sheet_names and len(sheet_names) > 1 and len(df.columns) == 0:
                # Multi-sheet: requires selection — persist stub record and return early
                file_record = FileModel(
                    id=file_id,
                    owner_id=user.sub,
                    original_filename=file.filename or "upload",
                    file_type=file_type,
                    size_bytes=len(raw_bytes),
                    storage_path=storage_path,
                    status="needs_sheet_selection",
                )
                db.add(file_record)
                await db.commit()
                return FileUploadResponse(
                    file_id=str(file_id),
                    status="needs_sheet_selection",
                    sheet_names=sheet_names,
                )
            # Single-sheet excel — df is already loaded
            if sheet_names:
                selected_sheet = sheet_names[0]
        else:
            df = read_csv_safe(raw_bytes)

        check_row_count(df)

    except FileValidationError as exc:
        raise _ve(exc)
    except Exception as exc:
        raise user_error("PARSE_ERROR")

    # ── Build metadata + preview ──────────────────────────────────────────────
    columns_metadata = build_columns_metadata(df)
    preview_rows = build_preview_rows(df)

    # ── Persist ───────────────────────────────────────────────────────────────
    file_record = FileModel(
        id=file_id,
        owner_id=user.sub,
        original_filename=file.filename or "upload",
        file_type=file_type,
        size_bytes=len(raw_bytes),
        row_count=len(df),
        sheet_name=selected_sheet,
        storage_path=storage_path,
        columns_metadata=columns_metadata,
        preview_rows=preview_rows,
        status="validated",
    )
    db.add(file_record)
    await db.commit()

    return FileUploadResponse(
        file_id=str(file_id),
        status="validated",
        row_count=len(df),
        columns=[ColumnInfo(**c) for c in columns_metadata],
        preview_rows=preview_rows,
        # sheet_names is empty for CSV/single-sheet Excel files.
        sheet_names=[],
    )


# ── POST /api/v1/files/{file_id}/sheet ───────────────────────────────────────

@router.post("/{file_id}/sheet", response_model=FileUploadResponse)
async def select_sheet(
    file_id: str,
    body: SheetSelectBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    # Session ownership check — compare as strings to handle GUID vs str differences
    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    # Re-parse with selected sheet (async-safe: offload blocking read to thread pool)
    try:
        raw_bytes = await asyncio.to_thread(
            lambda: Path(file_record.storage_path).read_bytes()
        )
        df, sheet_names = read_excel_safe(raw_bytes, sheet_name=body.sheet_name)
        check_row_count(df)
    except FileValidationError as exc:
        raise _ve(exc)
    except Exception as exc:
        raise user_error("PARSE_ERROR")

    columns_metadata = build_columns_metadata(df)
    preview_rows = build_preview_rows(df)

    file_record.sheet_name = body.sheet_name
    file_record.row_count = len(df)
    file_record.columns_metadata = columns_metadata
    file_record.preview_rows = preview_rows
    file_record.status = "validated"
    await db.commit()

    return FileUploadResponse(
        file_id=str(fid),
        status="validated",
        row_count=len(df),
        columns=[ColumnInfo(**c) for c in columns_metadata],
        preview_rows=preview_rows,
        # sheet_names is empty once sheet selection is finalized.
        sheet_names=[],
    )

# ── GET /api/v1/files/{file_id}/dashboard-config ─────────────────────────

@router.get("/{file_id}/dashboard-config")
async def get_dashboard_config(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    return {"dashboard_config": file_record.dashboard_config or {}}

# ── POST /api/v1/files/{file_id}/dashboard-config ────────────────────────

@router.post("/{file_id}/dashboard-config")
async def save_dashboard_config(
    file_id: str,
    config: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    # Size guard: prevent oversized dashboard configs from bloating the DB
    config_json = json.dumps(config)
    if len(config_json) > 512_000:  # 500 KB cap
        raise user_error("PAYLOAD_TOO_LARGE")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    file_record.dashboard_config = config
    flag_modified(file_record, "dashboard_config")
    await db.commit()
    return {"status": "ok"}


# ── GET /api/v1/files/{file_id}/data ─────────────────────────────────────────

@router.get("/{file_id}/data", response_model=FileDataResponse)
async def get_file_data(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    try:
        raw_bytes = await asyncio.to_thread(
            lambda: Path(file_record.storage_path).read_bytes()
        )
        if file_record.file_type in ("xlsx", "xls"):
            df, _ = read_excel_safe(raw_bytes, sheet_name=file_record.sheet_name)
        else:
            df = read_csv_safe(raw_bytes)
    except Exception as exc:
        raise user_error("PARSE_ERROR")

    total_rows = len(df)
    is_truncated = total_rows > 10000
    
    data = build_preview_rows(df, n=10000)

    return FileDataResponse(
        data=data,
        is_truncated=is_truncated,
        total_rows=total_rows
    )


# ── DELETE /api/v1/files/{file_id} ───────────────────────────────────────

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    storage_dir = Path(settings.storage_path) / str(fid)
    if storage_dir.exists() and storage_dir.is_dir():
        shutil.rmtree(storage_dir, ignore_errors=True)

    await db.delete(file_record)
    await db.commit()
    return {"status": "ok"}


# ── GET /api/v1/files/session/current ───────────────────────────────────────

class SessionHydrationResponse(BaseModel):
    files: List[Dict[str, Any]]
    prompts: List[Dict[str, Any]]

@router.get("/session/current", response_model=SessionHydrationResponse)
async def get_current_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Find user files
    result = await db.execute(select(FileModel).where(FileModel.owner_id == user.sub))
    files = result.scalars().all()
    
    file_list = []
    all_prompts = []
    
    for f in files:
        file_list.append({
            "id": str(f.id),
            "name": f"{f.original_filename} — {f.sheet_name}" if f.sheet_name else f.original_filename,
            "rowCount": f.row_count or 0,
            "columns": f.columns_metadata or [],
            "previewRows": f.preview_rows or [],
            "uploadedAt": f.created_at,
            "dashboardConfig": f.dashboard_config
        })
        
        # Get prompts for this file
        p_result = await db.execute(select(PromptModel).where(PromptModel.file_id == f.id).order_by(PromptModel.created_at))
        prompts = p_result.scalars().all()
        for p in prompts:
            c_result = await db.execute(select(ChartModel).where(ChartModel.prompt_id == p.id))
            chart = c_result.scalar_one_or_none()
            all_prompts.append({
                "id": str(p.id),
                "file_id": str(p.file_id),
                "raw_text": p.raw_text,
                "status": p.status,
                "clarification_question": p.clarification_question,
                "explanation": p.explanation,
                "error_message": p.error_message,
                "created_at": p.created_at,
                "chart": {
                    "chart_type": chart.chart_type,
                    "chart_spec": chart.chart_spec
                } if chart else None
            })
            
    return SessionHydrationResponse(files=file_list, prompts=all_prompts)

# ── GET /api/v1/files/{file_id}/unique-values ────────────────────────────

@router.get("/{file_id}/unique-values")
async def get_unique_values(
    file_id: str,
    column: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    try:
        df = await asyncio.to_thread(
            lambda: load_dataframe_from_path(file_record.storage_path, sheet_name=file_record.sheet_name)
        )
    except Exception as exc:
        raise user_error("PARSE_ERROR")

    if column not in df.columns:
        raise user_error("INVALID_COLUMN", column=column)

    # Get all unique non-null values, sorted, capped at 1000
    unique_vals = (
        df[column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    unique_vals = sorted(unique_vals)[:1000]

    return {"column": column, "values": unique_vals}


# ── GET /api/v1/files/{file_id}/aggregate ────────────────────────────────

@router.get("/{file_id}/aggregate")
async def get_aggregate(
    file_id: str,
    column: str,
    aggregation: str,
    filters: Optional[str] = None,  # JSON-encoded list of {column, operator, value}
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise user_error("INVALID_FILE_ID")

    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise user_error("FILE_NOT_FOUND", http_status=404)

    if file_record.owner_id != user.sub:
        raise user_error("FORBIDDEN", http_status=403)

    if not column or not column.strip():
        raise user_error("INVALID_COLUMN", column=column or "(empty)")

    valid_aggs = ("sum", "avg", "count", "min", "max")
    if aggregation not in valid_aggs:
        raise user_error("INVALID_AGGREGATION")

    try:
        df = await asyncio.to_thread(
            lambda: load_dataframe_from_path(file_record.storage_path, sheet_name=file_record.sheet_name)
        )
    except Exception as exc:
        raise user_error("PARSE_ERROR")

    # Apply optional filters
    if filters:
        try:
            filter_list = json.loads(filters)
            for f in filter_list:
                fcol = f.get("column")
                fop  = f.get("operator")
                fval = f.get("value", "")
                if not fcol or fcol not in df.columns:
                    continue
                col_series = df[fcol]
                try:
                    # Try numeric comparison first
                    num_val = float(fval)
                    if fop == "eq":  mask = col_series == num_val
                    elif fop == "ne": mask = col_series != num_val
                    elif fop == "gt": mask = col_series > num_val
                    elif fop == "gte": mask = col_series >= num_val
                    elif fop == "lt": mask = col_series < num_val
                    elif fop == "lte": mask = col_series <= num_val
                    else: mask = col_series.astype(str).str.contains(fval, case=False, na=False)
                except (ValueError, TypeError):
                    # Fall back to string comparison
                    str_series = col_series.astype(str)
                    if fop == "eq":  mask = str_series.str.lower() == fval.lower()
                    elif fop == "ne": mask = str_series.str.lower() != fval.lower()
                    elif fop == "contains": mask = str_series.str.contains(fval, case=False, na=False)
                    else: mask = str_series.str.lower() == fval.lower()
                df = df[mask]
        except (json.JSONDecodeError, Exception):
            pass  # ignore malformed filters, use full dataset

    if column not in df.columns:
        raise user_error("INVALID_COLUMN", column=column)

    if aggregation != "count":
        import pandas.api.types as ptypes
        if not ptypes.is_numeric_dtype(df[column]):
            raise user_error("INVALID_DTYPE", column=column)

    val = 0.0
    try:
        if aggregation == "count":
            val = float(df[column].count())
        elif aggregation == "sum":
            val = float(df[column].sum())
        elif aggregation == "avg":
            val = float(df[column].mean())
        elif aggregation == "min":
            val = float(df[column].min())
        elif aggregation == "max":
            val = float(df[column].max())

        import math
        if math.isnan(val) or math.isinf(val):
            val = 0.0
    except Exception as exc:
        raise user_error("AGGREGATION_ERROR", column=column)

    return {"value": val}
