"""
file_validator.py — Content-signature validation, size/row limits, preview,
CSV encoding detection, and multi-sheet Excel handling.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chardet
try:
    import magic as _magic
    _MAGIC_AVAILABLE = True
except (ImportError, OSError):
    # libmagic not available on this platform (common on Windows without DLL)
    _MAGIC_AVAILABLE = False
    _magic = None  # type: ignore
import pandas as pd

from backend.core.config import get_settings
from backend.services.locale_normalizer import normalize_dataframe

settings = get_settings()

# Allowed MIME types keyed by our internal file_type
_ALLOWED_MIME = {
    "text/csv": "csv",
    "text/plain": "csv",          # some systems report CSV as text/plain
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
    "application/zip": "xlsx",    # xlsx is a zip internally; magic may report this
}

_DTYPE_MAP = {
    "int64": "numeric",
    "int32": "numeric",
    "float64": "numeric",
    "float32": "numeric",
    "bool": "categorical",
    "object": "text",
    "category": "categorical",
    "datetime64[ns]": "datetime",
    "datetime64[ns, UTC]": "datetime",
}


class FileValidationError(Exception):
    """Raised when a file fails validation. Carries an error code."""

    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def detect_content_type(header_bytes: bytes, filename: str = "") -> str:
    """
    Detect MIME type from file header bytes (content signature, not extension).
    Falls back to filename extension when libmagic is unavailable (e.g. Windows dev).
    Returns our internal file_type: 'csv' or 'xlsx'.
    Raises FileValidationError for unknown/disallowed types.
    """
    mime: str | None = None

    if _MAGIC_AVAILABLE:
        mime = _magic.from_buffer(header_bytes, mime=True)  # type: ignore[union-attr]
    else:
        # Extension-based fallback (dev / CI without libmagic)
        ext = Path(filename).suffix.lower()
        ext_map = {
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
        }
        mime = ext_map.get(ext)

    if mime is None:
        # Last resort: sniff header bytes manually
        if header_bytes[:4] == b"PK\x03\x04":  # ZIP / xlsx
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif header_bytes[:2] in (b"\xd0\xcf", ):  # OLE2 / xls
            mime = "application/vnd.ms-excel"
        else:
            try:
                header_bytes[:512].decode("utf-8")
                mime = "text/csv"
            except UnicodeDecodeError:
                pass

    file_type = _ALLOWED_MIME.get(mime or "")
    if file_type is None:
        raise FileValidationError(
            code="INVALID_FILE_TYPE",
            message=f"File type not allowed (detected: {mime}). Only CSV and Excel files are accepted.",
            details={"detected_mime": mime},
        )
    return file_type


def check_file_size(size_bytes: int) -> None:
    """Raise if file exceeds the configured limit."""
    max_bytes = settings.max_file_size_bytes
    if size_bytes > max_bytes:
        raise FileValidationError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds the {settings.max_file_size_mb}MB limit.",
            details={
                "max_size_mb": settings.max_file_size_mb,
                "received_size_mb": round(size_bytes / (1024 * 1024), 2),
            },
        )


def detect_encoding(raw_bytes: bytes) -> str:
    """Detect encoding using chardet, fall back to utf-8."""
    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding") or "utf-8"
    # Normalise common aliases
    return encoding.lower().replace("-", "_")


def read_csv_safe(raw_bytes: bytes) -> pd.DataFrame:
    """Read CSV with encoding + separator detection + locale normalization."""
    encoding = detect_encoding(raw_bytes)
    df = None

    def _try_read(enc: str) -> "pd.DataFrame | None":
        try:
            # sep=None uses Python's csv.Sniffer to detect delimiter (comma, semicolon, tab…)
            return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, sep=None, engine="python")
        except (UnicodeDecodeError, Exception):
            return None

    df = _try_read(encoding)

    if df is None:
        for enc in ("latin-1", "windows-1252", "utf-8-sig"):
            df = _try_read(enc)
            if df is not None:
                break

    if df is None:
        raise FileValidationError(
            code="UNREADABLE_ENCODING",
            message="Could not decode the file. Please save it as UTF-8 or Latin-1 and try again.",
        )

    return normalize_dataframe(df)



def read_excel_safe(raw_bytes: bytes, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    Read Excel file. Returns (df, sheet_list).
    If sheet_name is None and there are multiple sheets, df is empty and sheet_list has names.
    """
    xl = pd.ExcelFile(io.BytesIO(raw_bytes))
    sheet_list = xl.sheet_names

    if sheet_name is None:
        if len(sheet_list) == 1:
            sheet_name = sheet_list[0]
        else:
            # Multi-sheet: return empty df to trigger sheet selection
            return pd.DataFrame(), sheet_list

    df = xl.parse(sheet_name)
    df = normalize_dataframe(df)
    return df, sheet_list


def check_row_count(df: pd.DataFrame) -> None:
    """Raise if dataframe exceeds the row limit or is empty."""
    if len(df) == 0:
        raise FileValidationError(
            code="EMPTY_FILE",
            message="The file contains no readable rows.",
        )
    if len(df) > settings.max_rows:
        raise FileValidationError(
            code="TOO_MANY_ROWS",
            message=f"File has {len(df):,} rows which exceeds the {settings.max_rows:,} row limit.",
            details={"max_rows": settings.max_rows, "received_rows": len(df)},
        )


def infer_dtype_label(dtype) -> str:
    """Map pandas dtype to our simplified label."""
    dtype_str = str(dtype)
    for key, label in _DTYPE_MAP.items():
        if dtype_str.startswith(key):
            return label
    if "datetime" in dtype_str:
        return "datetime"
    if "int" in dtype_str or "float" in dtype_str:
        return "numeric"
    return "text"


def build_columns_metadata(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Build the columns_metadata list stored in DB and returned in preview."""
    # Try to infer datetimes after normalization
    df_typed = df.copy()
    for col in df_typed.select_dtypes(include="object").columns:
        try:
            df_typed[col] = pd.to_datetime(df_typed[col], format="mixed", dayfirst=False)
        except (ValueError, TypeError):
            pass

    metadata = []
    for col in df_typed.columns:
        metadata.append(
            {
                "name": str(col),
                "dtype": infer_dtype_label(df_typed[col].dtype),
                "missing_count": int(df_typed[col].isna().sum()),
            }
        )
    return metadata


def build_preview_rows(df: pd.DataFrame, n: int = 20) -> List[Dict[str, Any]]:
    """Return first n rows as list of dicts (JSON-serializable)."""
    preview = df.head(n).copy()
    # Convert non-serialisable types
    for col in preview.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        preview[col] = preview[col].astype(str)
    return preview.where(pd.notnull(preview), None).to_dict(orient="records")


def save_upload(raw_bytes: bytes, filename: str, file_id: str) -> str:
    """Persist raw bytes to disk and return the storage path."""
    storage_dir = Path(settings.storage_path) / file_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    dest = storage_dir / filename
    dest.write_bytes(raw_bytes)
    return str(dest)


def load_dataframe_from_path(storage_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Load a stored file back into a DataFrame (used by Celery tasks)."""
    raw_bytes = Path(storage_path).read_bytes()
    ext = Path(storage_path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        df, _ = read_excel_safe(raw_bytes, sheet_name=sheet_name)
    else:
        df = read_csv_safe(raw_bytes)
    return df
