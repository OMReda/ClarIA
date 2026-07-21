"""
locale_normalizer.py — Pre-Pandas pass for French-formatted numbers and dates.

French numbers: 1 234,56  →  1234.56
French dates:   dd/mm/yyyy, dd-mm-yyyy  →  yyyy-mm-dd (ISO 8601)

Applied column-by-column before pd.read_csv / pd.read_excel so that Pandas
dtype inference sees clean values.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Patterns
_FR_NUMBER_RE = re.compile(
    r"^\s*-?\d{1,3}(?:[\s\u00a0]\d{3})*(?:,\d+)?\s*$"
)
_FR_DATE_RE = re.compile(
    r"^\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\s*$"
)


def _is_fr_number(value: str) -> bool:
    return bool(_FR_NUMBER_RE.match(value))


def _parse_fr_number(value: str) -> float:
    # Remove narrow/regular spaces (thousands separator), replace comma decimal
    cleaned = re.sub(r"[\s\u00a0]", "", value.strip())
    cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def _is_fr_date(value: str) -> bool:
    return bool(_FR_DATE_RE.match(value))


def _parse_fr_date(value: str) -> str:
    m = _FR_DATE_RE.match(value)
    if not m:
        return value
    day, month, year = m.group(1), m.group(2), m.group(3)
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def normalize_column(series: pd.Series) -> pd.Series:
    """
    Attempt French-number then French-date normalization on a string series.
    Returns the original series if neither pattern matches ≥50% of non-null values.
    """
    if series.dtype != object:
        return series

    str_series = series.dropna().astype(str)
    if len(str_series) == 0:
        return series

    # ── Try French numbers ────────────────────────────────────────────────────
    fr_num_matches = str_series.apply(_is_fr_number).sum()
    if fr_num_matches / len(str_series) >= 0.5:
        def safe_num(v: Any) -> Any:
            if pd.isna(v):
                return v
            try:
                return _parse_fr_number(str(v))
            except (ValueError, TypeError):
                return v

        return series.apply(safe_num)

    # ── Try French dates ──────────────────────────────────────────────────────
    fr_date_matches = str_series.apply(_is_fr_date).sum()
    if fr_date_matches / len(str_series) >= 0.5:
        def safe_date(v: Any) -> Any:
            if pd.isna(v):
                return v
            return _parse_fr_date(str(v))

        return series.apply(safe_date)

    return series


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply French locale normalization to every object column."""
    result = df.copy()
    for col in result.columns:
        if result[col].dtype == object:
            result[col] = normalize_column(result[col])
    return result
