"""
chart_resolver.py — Maps a result DataFrame + detected chart type → ECharts option JSON.

Pipeline:
  1. detect_chart_type() — keyword + column-type heuristics → one of 5 types or None
  2. build_chart_spec()  — converts aggregated result DataFrame → ECharts option dict

PandasAI is asked to return aggregated data as a DataFrame (not a plot).
This module then translates that DataFrame into interactive ECharts JSON.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

SUPPORTED_CHART_TYPES = {"bar", "line", "pie", "scatter", "histogram", "area", "radar", "heatmap"}

# ─── Keyword lists (French + English) ────────────────────────────────────────
_HISTOGRAM_KW = [
    "distribution", "histogramme", "histogram", "fréquence", "frequence",
    "répartition des valeurs", "repartition des valeurs",
]
_LINE_KW = [
    "courbe", "ligne", "évolution", "evolution", "tendance", "trend",
    "dans le temps", "line", "temporal", "timeline", "par date",
    "par mois", "par an", "over time", "time series",
]
_AREA_KW = [
    "aire", "cumulé", "cumulatif", "area"
]
_PIE_KW = [
    "camembert", "pie", "proportion", "part de", "pourcentage",
    "percentage", "répartition par", "repartition par", "répartition", "repartition", "donut", "part"
]
# Bare 'répartition'/'repartition' is ambiguous: it resolves to pie when categorical
# columns are present, but falls through to histogram disambiguation when the dataset
# is numeric-only. See detect_chart_type() for the guard logic.
_REPARTITION_BARE_KW = ["répartition des valeurs", "repartition des valeurs", "répartition", "repartition"]
_SCATTER_KW = [
    "nuage", "nuages", "scatter", "dispersion", "correlation", "correlat",
    "relation entre", "nuage de points", "nuages de points",
]
_BAR_KW = [
    "barres", "barre", "histogramme des", "bar", "par region", "par categorie",
    "groupe", "groupees", "groupes",
]
_RADAR_KW = [
    "radar", "toile d'araignee", "araignee", "spider", "web chart",
    "polygone", "radial",
]
_HEATMAP_KW = [
    "heatmap", "carte de chaleur", "chaleur", "matrice de correlation",
    "intensite", "densite par", "correlation matrix", "carte thermique",
]

# Issue 4: comparison keywords — mapped to line (temporal) or bar (categorical)
_COMPARE_KW = [
    "compare", "comparer", "versus", "vs", "comparaison",
    "par rapport", "between", "entre",
]

# Strong aggregate/ranking signals — when these appear the user wants a bar even
# if the dataset has a date column (e.g. "top 5 des ventes par produit cette annee")
_AGGREGATE_KW = [
    "top", "flop", "meilleur", "meilleurs", "meilleures",
    "pire", "pires", "worst", "best",
    "classement", "ranking", "rang", "podium",
    "nombre de", "count of", "how many", "combien de",
    "total par", "somme par", "sum by", "total by",
]

# Time-unit words — when present alongside "par"/"by" the user is grouping
# by a time dimension, which means line is the right default.
_TIME_UNIT_KW = [
    "mois", "month", "an", "annee", "year",
    "trimestre", "quarter", "semaine", "week",
    "jour", "day", "heure", "hour",
    "date", "periode", "period",
]

# Matches patterns like "2004-2005", "2004–2005", "between 2004 and 2010", "de 2004 à 2010"
_YEAR_RANGE_RE = re.compile(
    r"(\b\d{4}\s*[-\u2013]\s*\d{4}\b|between\s+\d{4}\s+and\s+\d{4}|de\s+\d{4}\s+[\u00e0a]\s+\d{4})",
    re.IGNORECASE,
)

import unicodedata

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _contains_word(text: str, keywords: List[str]) -> bool:
    text_norm = _strip_accents(text.lower())
    for kw in keywords:
        kw_norm = _strip_accents(kw.lower())
        if re.search(rf"\b{re.escape(kw_norm)}\b", text_norm):
            return True
    return False

import logging

logger = logging.getLogger(__name__)

def detect_chart_type(
    prompt_text: str,
    columns_metadata: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Determine chart type from prompt keywords + column dtype composition.
    Returns one of: 'bar', 'line', 'pie', 'scatter', 'histogram', 'area', or None.
    """
    numeric_cols = [c for c in columns_metadata if c["dtype"] == "numeric"]
    categorical_cols = [c for c in columns_metadata if c["dtype"] == "categorical"]
    datetime_cols = [c for c in columns_metadata if c["dtype"] == "datetime"]
    text_cols = [c for c in columns_metadata if c["dtype"] == "text"]

    def _check_and_log(chart_type: str, keywords: List[str]) -> bool:
        if _contains_word(prompt_text, keywords):
            logger.info(f"Chart detection: explicit keyword matched for '{chart_type}'. Prompt: '{prompt_text}'")
            return True
        return False

    # ── Keyword-first matching ────────────────────────────────────────────────
    # Only scan the raw prompt text for explicit chart types
    if _check_and_log("histogram", _HISTOGRAM_KW) and not _contains_word(prompt_text, _LINE_KW):
        return "histogram"
    if _check_and_log("area", _AREA_KW):
        return "area"
    # Check heatmap BEFORE line — "carte de chaleur par mois" has "par mois" which is a line keyword
    if _check_and_log("heatmap", _HEATMAP_KW):
        return "heatmap"
    if _check_and_log("radar", _RADAR_KW):
        return "radar"
    if _check_and_log("line", _LINE_KW):
        return "line"
    if _contains_word(prompt_text, _PIE_KW):
        # Disambiguation: bare 'répartition' on a numeric-only column means histogram,
        # not pie. Only resolve to pie when categorical columns are present OR when an
        # unambiguous pie keyword (camembert, pie, proportion, part de, donut) is used.
        _UNAMBIGUOUS_PIE_KW = [
            "camembert", "pie", "proportion", "part de", "pourcentage", "percentage", "donut"
        ]
        is_bare_repartition = (
            _contains_word(prompt_text, _REPARTITION_BARE_KW)
            and not _contains_word(prompt_text, _UNAMBIGUOUS_PIE_KW)
        )
        if is_bare_repartition and len(categorical_cols) == 0 and len(numeric_cols) >= 1:
            logger.info(
                "Chart detection: bare 'répartition' with numeric-only columns → histogram "
                "(no categorical columns to form pie slices). Prompt: '%s'", prompt_text
            )
            return "histogram"
        logger.info("Chart detection: explicit keyword matched for 'pie'. Prompt: '%s'", prompt_text)
        return "pie"
    if _check_and_log("scatter", _SCATTER_KW):
        return "scatter"
    if _check_and_log("bar", _BAR_KW):
        return "bar"
    if _check_and_log("heatmap", _HEATMAP_KW):
        return "heatmap"

    # Issue 4: comparison keywords with year-range → line (temporal) or bar (categorical)
    prompt_norm = _strip_accents(prompt_text.lower())
    is_comparison = any(
        re.search(rf"\b{re.escape(_strip_accents(kw))}\b", prompt_norm)
        for kw in _COMPARE_KW
    ) or bool(_YEAR_RANGE_RE.search(prompt_text))

    if is_comparison:
        if len(datetime_cols) >= 1:
            logger.info(
                "Chart detection: comparison + datetime columns → 'line'. Prompt: '%s'", prompt_text
            )
            return "line"
        if len(categorical_cols) + len(text_cols) >= 1:
            logger.info(
                "Chart detection: comparison + categorical/text columns → 'bar'. Prompt: '%s'", prompt_text
            )
            return "bar"

    # ── Semantic fallback: infer from prompt intent + column types ──────────
    # Instead of a fixed "date = line" rule, read the prompt to understand what
    # the user actually wants before picking a chart type.
    n_num = len(numeric_cols)
    n_cat = len(categorical_cols)
    n_dt  = len(datetime_cols)
    n_text = len(text_cols)

    fallback_type = None

    # 1. Only numerics → histogram (no grouping axis)
    if n_num == 1 and n_cat == 0 and n_dt == 0 and n_text == 0:
        fallback_type = "histogram"

    # 2. Two numerics, no categories → scatter (relationship between two measures)
    elif n_num >= 2 and n_cat == 0 and n_dt == 0:
        fallback_type = "scatter"

    # 3. Date column present — decide between line (trend) and bar (aggregate)
    elif n_dt >= 1 and n_num >= 1:
        # 3a. Ranking / count / aggregate signal → bar even with dates
        #     e.g. "top 5 des produits cette annee"
        if _contains_word(prompt_text, _AGGREGATE_KW):
            logger.info(
                "Chart detection: aggregate/ranking signal with date cols -> 'bar'. Prompt: '%s'",
                prompt_text,
            )
            fallback_type = "bar"

        # 3b. Dataset also has categorical columns AND prompt groups by a category
        #     (not by a time unit) → bar   e.g. "ventes par produit cette annee"
        elif n_cat >= 1:
            groups_by_time = _contains_word(prompt_text, _TIME_UNIT_KW)
            groups_by_category = _contains_word(prompt_text, ["par", "by", "selon", "per"])
            if groups_by_category and not groups_by_time:
                logger.info(
                    "Chart detection: category-grouping signal with date + cat cols -> 'bar'. Prompt: '%s'",
                    prompt_text,
                )
                fallback_type = "bar"
            else:
                # Time-unit grouping or ambiguous → line (trend)
                fallback_type = "line"

        # 3c. Pure date + numeric, no other signal → time series → line
        else:
            fallback_type = "line"

    # 4. Categorical / text + numeric → bar (grouped aggregation)
    elif (n_cat + n_text) >= 1 and n_num >= 1:
        fallback_type = "bar"

    if fallback_type:
        logger.info(
            "Chart detection: semantic fallback to '%s' (dt=%d, cat=%d, num=%d, text=%d). Prompt: '%s'",
            fallback_type, n_dt, n_cat, n_num, n_text, prompt_text,
        )
        return fallback_type

    logger.info("Chart detection: unable to detect chart type. Prompt: '%s'", prompt_text)
    return None


def _format_col(c: str) -> str:
    return str(c).replace("_", " ").title()

def build_chart_spec(
    result_df: pd.DataFrame,
    chart_type: str,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    auto_pivot: bool = False,
) -> Dict[str, Any]:
    """
    Convert an aggregated result DataFrame to an ECharts option dict.
    Auto-detects x/y columns if not provided.

    auto_pivot: when True AND the DataFrame has exactly 2 non-numeric columns + 1 numeric
    column (flat GROUP BY result), pivot it into a wide format so that each group becomes
    a separate series. Only set by tasks.py when the prompt was a comparison request.
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"Unsupported chart type: {chart_type!r}")

    if result_df is None or len(result_df) == 0:
        raise ValueError("Result DataFrame is empty — cannot build chart spec.")

    df = result_df.copy()

    # ── Auto-detect columns ───────────────────────────────────────────────────
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = df.select_dtypes(exclude="number").columns.tolist()

    # ── Safe pivot for comparison prompts ────────────────────────────────────
    # When auto_pivot=True and the LLM returned a flat long-form table
    # (e.g. Date, Product, Revenue — 1 numeric col, 2 categorical cols),
    # pivot it so each unique value in col2 becomes a separate numeric column.
    # This only runs on chart types that have a natural multi-series axis.
    if (
        auto_pivot
        and chart_type in ("line", "bar", "area")
        and len(non_numeric_cols) == 2
        and len(numeric_cols) == 1
    ):
        idx_col  = non_numeric_cols[0]   # e.g. Date / Category axis
        pivot_col = non_numeric_cols[1]  # e.g. Product / Region (becomes series)
        val_col   = numeric_cols[0]      # e.g. Revenue
        try:
            pivoted = df.pivot_table(
                index=idx_col, columns=pivot_col, values=val_col, aggfunc="sum"
            ).reset_index()
            pivoted.columns.name = None  # remove the multi-index label
            logger.info(
                "auto_pivot: pivoted '%s' on '%s' -> %d series",
                val_col, pivot_col, len(pivoted.columns) - 1,
            )
            df = pivoted
            # Re-detect columns after pivot
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            non_numeric_cols = df.select_dtypes(exclude="number").columns.tolist()
        except Exception as e:
            logger.warning("auto_pivot failed (will use flat data): %s", e)

    spec = {}
    title_text = ""

    if chart_type == "histogram":
        x = x_col or (numeric_cols[0] if numeric_cols else df.columns[0])
        spec = _histogram(df, x)
        title_text = f"Distribution of {_format_col(x)}"

    elif chart_type == "scatter":
        cols = numeric_cols
        cx = x_col or (cols[0] if len(cols) > 0 else df.columns[0])
        cy = y_col or (cols[1] if len(cols) > 1 else df.columns[-1])
        spec = _scatter(df, cx, cy)
        title_text = f"{_format_col(cy)} vs {_format_col(cx)}"

    elif chart_type == "pie":
        name_col = x_col or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        value_col = y_col or (numeric_cols[0] if numeric_cols else df.columns[-1])
        if name_col == value_col:
            # Single numeric column fallback: use index for labels to avoid crashing ECharts
            df = df.reset_index()
            name_col = df.columns[0]
        spec = _pie(df, name_col, value_col)
        title_text = f"{_format_col(value_col)} by {_format_col(name_col)}"

    elif chart_type == "area":
        x = x_col or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        y_cols = [y_col] if y_col else [c for c in numeric_cols if c != x]
        if not y_cols:
            y_cols = [df.columns[-1]]
        spec = _area(df, x, y_cols)
        title_text = f"{', '.join(_format_col(y) for y in y_cols)} Trend over {_format_col(x)}"

    elif chart_type == "line":
        x = x_col or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        y_cols = [y_col] if y_col else [c for c in numeric_cols if c != x]
        if not y_cols:
            y_cols = [df.columns[-1]]
        spec = _line(df, x, y_cols)
        title_text = f"{', '.join(_format_col(y) for y in y_cols)} Trend over {_format_col(x)}"

    elif chart_type == "radar":
        name_col = x_col or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        y_cols = [y_col] if y_col else [c for c in numeric_cols if c != name_col]
        if not y_cols:
            y_cols = [df.columns[-1]]
        spec = _radar(df, name_col, y_cols)
        title_text = f"Radar: {', '.join(_format_col(y) for y in y_cols)}"

    elif chart_type == "heatmap":
        spec = _heatmap(df, non_numeric_cols, numeric_cols)
        title_text = "Heatmap"

    else:
        # bar (default)
        x = x_col or (non_numeric_cols[0] if non_numeric_cols else df.columns[0])
        y_cols = [y_col] if y_col else [c for c in numeric_cols if c != x]
        if not y_cols:
            y_cols = [df.columns[-1]]
        spec = _bar(df, x, y_cols)
        title_text = f"{', '.join(_format_col(y) for y in y_cols)} by {_format_col(x)}"

    # Add the generated human-readable title
    # We set show: False so it doesn't duplicate inside the canvas,
    # but the frontend can still use it for the card header.
    if "title" not in spec:
        spec["title"] = {}
    spec["title"]["text"] = title_text
    spec["title"]["show"] = False

    return spec


# ─── Individual chart builders ────────────────────────────────────────────────

def _clean(series: pd.Series) -> List[Any]:
    """Convert series to JSON-safe list."""
    return [
        (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v))
        for v in series
    ]


def _bar(df: pd.DataFrame, x_col: str, y_cols: List[str]) -> Dict[str, Any]:
    series = []
    for y in y_cols:
        series.append({
            "name": y,
            "type": "bar",
            "data": _clean(df[y]),
            "itemStyle": {"borderRadius": [4, 4, 0, 0]},
        })
    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": _clean(df[x_col].astype(str)),
            "axisLabel": {"rotate": 30 if len(df) > 6 else 0},
        },
        "yAxis": {"type": "value"},
        "legend": {"data": y_cols} if len(y_cols) > 1 else {},
        "series": series,
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    }


def _line(df: pd.DataFrame, x_col: str, y_cols: List[str]) -> Dict[str, Any]:
    series = []
    for y in y_cols:
        series.append({
            "name": y,
            "type": "line",
            "data": _clean(df[y]),
            "smooth": True,
        })
    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": _clean(df[x_col].astype(str)),
            "boundaryGap": False,
        },
        "yAxis": {"type": "value"},
        "legend": {"data": y_cols} if len(y_cols) > 1 else {},
        "series": series,
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    }

def _heatmap(df: pd.DataFrame, non_numeric_cols: List[str], numeric_cols: List[str]) -> Dict[str, Any]:
    # Support long format (e.g. Country, Month, Sales) or wide format (Country, Jan, Feb, Mar...)
    if len(non_numeric_cols) >= 2 and len(numeric_cols) >= 1:
        # Long format
        y_col = non_numeric_cols[0]
        x_col = non_numeric_cols[1]
        val_col = numeric_cols[0]
        
        y_labels = sorted(list(df[y_col].dropna().unique()))
        x_labels = sorted(list(df[x_col].dropna().unique()))
        y_map = {lbl: idx for idx, lbl in enumerate(y_labels)}
        x_map = {lbl: idx for idx, lbl in enumerate(x_labels)}
        
        data = []
        min_val, max_val = float('inf'), float('-inf')
        for _, row in df.iterrows():
            y_val, x_val, val = row[y_col], row[x_col], row[val_col]
            if pd.isna(y_val) or pd.isna(x_val) or pd.isna(val): continue
            if hasattr(val, "item"): val = val.item()
            data.append([x_map[x_val], y_map[y_val], val])
            min_val = min(min_val, val)
            max_val = max(max_val, val)
            
    else:
        # Wide format (pivot table)
        y_col = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
        x_labels = [c for c in numeric_cols]
        y_labels = sorted(list(df[y_col].dropna().unique()))
        y_map = {lbl: idx for idx, lbl in enumerate(y_labels)}
        
        data = []
        min_val, max_val = float('inf'), float('-inf')
        for _, row in df.iterrows():
            y_val = row[y_col]
            if pd.isna(y_val): continue
            y_idx = y_map[y_val]
            for x_idx, x_col in enumerate(x_labels):
                val = row[x_col]
                if pd.isna(val): continue
                if hasattr(val, "item"): val = val.item()
                data.append([x_idx, y_idx, val])
                min_val = min(min_val, val)
                max_val = max(max_val, val)

    if min_val == float('inf'):
        min_val, max_val = 0, 100

    return {
        "tooltip": {"position": "top"},
        "grid": {"left": "10%", "right": "5%", "bottom": "15%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": [str(x) for x in x_labels],
            "splitArea": {"show": True}
        },
        "yAxis": {
            "type": "category",
            "data": [str(y) for y in y_labels],
            "splitArea": {"show": True}
        },
        "visualMap": {
            "min": min_val,
            "max": max_val,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%"
        },
        "series": [{
            "type": "heatmap",
            "data": data,
            "label": {"show": False},
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            }
        }]
    }

def _area(df: pd.DataFrame, x_col: str, y_cols: List[str]) -> Dict[str, Any]:
    series = []
    for y in y_cols:
        series.append({
            "name": y,
            "type": "line",
            "data": _clean(df[y]),
            "smooth": True,
            "areaStyle": {"opacity": 0.3},
        })
    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": _clean(df[x_col].astype(str)),
            "boundaryGap": False,
        },
        "yAxis": {"type": "value"},
        "legend": {"data": y_cols} if len(y_cols) > 1 else {},
        "series": series,
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    }


def _pie(df: pd.DataFrame, name_col: str, value_col: str) -> Dict[str, Any]:
    data = [
        {"name": str(n), "value": float(v)}
        for n, v in zip(_clean(df[name_col]), _clean(df[value_col]))
        if v is not None
    ]
    
    # Sort by value descending
    data.sort(key=lambda x: x["value"], reverse=True)
    
    show_labels = True
    # Group into "Other" if there are > 8 categories
    if len(data) > 8:
        show_labels = False
        top_data = data[:7]
        other_val = sum(d["value"] for d in data[7:])
        top_data.append({"name": "Other", "value": other_val})
        data = top_data

    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {
            "type": "scroll",
            "orient": "vertical", 
            "right": 10,
            "top": "center"
        },
        "series": [
            {
                "name": _format_col(value_col),
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": data,
                "label": {"show": show_labels},
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0,0,0,0.5)",
                    }
                },
            }
        ],
    }


def _scatter(df: pd.DataFrame, x_col: str, y_col: str) -> Dict[str, Any]:
    data = list(zip(_clean(df[x_col]), _clean(df[y_col])))
    data = [d for d in data if None not in d]
    return {
        "tooltip": {"trigger": "item", "formatter": f"{x_col}: {{c[0]}}<br>{y_col}: {{c[1]}}"},
        "xAxis": {"type": "value", "name": x_col},
        "yAxis": {"type": "value", "name": y_col},
        "series": [
            {
                "type": "scatter",
                "data": data,
                "symbolSize": 8,
            }
        ],
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    }


def _histogram(df: pd.DataFrame, col: str, bins: int = 20) -> Dict[str, Any]:
    """
    Compute histogram bins manually (no matplotlib dependency).

    Guard: if PandasAI already returned a (label, count) aggregated table instead
    of raw values, render it as-is rather than re-running pd.cut() on count values.
    Detection heuristic: exactly 2 columns, exactly 1 of which is non-numeric.
    """
    non_numeric_cols = df.select_dtypes(exclude="number").columns.tolist()

    # ── Already-aggregated path (label + count) ───────────────────────────────
    if len(df.columns) == 2 and len(non_numeric_cols) == 1:
        label_col = non_numeric_cols[0]
        # value col is the other one
        value_col = [c for c in df.columns if c != label_col][0]
        labels = _clean(df[label_col].astype(str))
        values = _clean(df[value_col])
        return {
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"rotate": 45},
                "name": label_col,
            },
            "yAxis": {"type": "value", "name": value_col},
            "series": [
                {
                    "name": value_col,
                    "type": "bar",
                    "data": values,
                    "barCategoryGap": "1%",
                    "itemStyle": {"borderRadius": [2, 2, 0, 0]},
                }
            ],
            "grid": {"left": "3%", "right": "4%", "bottom": "10%", "containLabel": True},
        }

    # ── Raw-values path: apply pd.cut() binning ───────────────────────────────
    series_clean = df[col].dropna()
    counts, bin_edges = pd.cut(series_clean, bins=bins, retbins=True)
    freq = counts.value_counts(sort=False)

    labels = [f"{b.left:.2f}–{b.right:.2f}" for b in freq.index]
    values = freq.values.tolist()

    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"rotate": 45},
            "name": col,
        },
        "yAxis": {"type": "value", "name": "Count"},
        "series": [
            {
                "name": col,
                "type": "bar",
                "data": values,
                "barCategoryGap": "1%",
                "itemStyle": {"borderRadius": [2, 2, 0, 0]},
            }
        ],
        "grid": {"left": "3%", "right": "4%", "bottom": "10%", "containLabel": True},
    }


def _radar(df: pd.DataFrame, name_col: str, y_cols: List[str]) -> Dict[str, Any]:
    """Build an ECharts radar chart spec from a DataFrame.

    Each row is one 'spoke label'. Each y_col is one series on the radar.
    If there is only one y_col the single series is named after that column.
    """
    indicators = [{"name": str(n)} for n in _clean(df[name_col].astype(str))]

    # Compute max per spoke (used to scale the radar axes)
    for i, ind in enumerate(indicators):
        max_val = max(
            (df[y].iloc[i] for y in y_cols if pd.notna(df[y].iloc[i])),
            default=1,
        )
        ind["max"] = float(max_val) * 1.2  # give 20% headroom

    series_data = []
    for y in y_cols:
        series_data.append({
            "name": _format_col(y),
            "value": _clean(df[y]),
        })

    return {
        "tooltip": {"trigger": "item"},
        "legend": {"data": [_format_col(y) for y in y_cols]} if len(y_cols) > 1 else {},
        "radar": {
            "indicator": indicators,
            "shape": "circle",
        },
        "series": [
            {
                "type": "radar",
                "data": series_data,
                "areaStyle": {"opacity": 0.2},
            }
        ],
    }


def _heatmap(
    df: pd.DataFrame, row_col: str, col_col: str, val_col: str
) -> Dict[str, Any]:
    """Build an ECharts heatmap from a 3-column DataFrame (row, col, value).

    Handles both flat (long-form) DataFrames and wide pivot matrices.
    """
    # Pivot to matrix if needed
    try:
        pivot = df.pivot_table(index=row_col, columns=col_col, values=val_col, aggfunc="sum")
    except Exception:
        # Fallback: treat as-is
        pivot = df.set_index(row_col).select_dtypes(include="number")

    rows = [str(r) for r in pivot.index.tolist()]
    cols = [str(c) for c in pivot.columns.tolist()]

    data = []
    for ri, r in enumerate(pivot.index):
        for ci, c in enumerate(pivot.columns):
            v = pivot.loc[r, c]
            data.append([ci, ri, round(float(v), 4) if pd.notna(v) else 0])

    all_vals = [d[2] for d in data if d[2] is not None]
    min_val = min(all_vals, default=0)
    max_val = max(all_vals, default=1)

    return {
        "tooltip": {"position": "top"},
        "grid": {"left": "3%", "right": "4%", "bottom": "10%", "containLabel": True},
        "xAxis": {"type": "category", "data": cols, "splitArea": {"show": True}},
        "yAxis": {"type": "category", "data": rows, "splitArea": {"show": True}},
        "visualMap": {
            "min": min_val,
            "max": max_val,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "2%",
        },
        "series": [
            {
                "name": _format_col(val_col),
                "type": "heatmap",
                "data": data,
                "label": {"show": len(data) <= 100},
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
            }
        ],
    }
