"""
fuzzy_matcher.py — Column name fuzzy matching using rapidfuzz.

Thresholds (configurable via env vars, defaults from spec gap resolution):
  HIGH  ≥ 80  → use silently (corrected without asking)
  MID   50-79 → awaiting_clarification with "did you mean X?"
  LOW   < 50  → awaiting_clarification asking user to name the column
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from rapidfuzz import fuzz, process

from backend.core.config import get_settings

settings = get_settings()


class MatchConfidence(str, Enum):
    HIGH = "high"      # use silently
    MID = "mid"        # ask "did you mean X?"
    LOW = "low"        # ask user to name the column
    EXACT = "exact"    # exact match


@dataclass
class MatchResult:
    user_term: str
    best_column: Optional[str]
    score: float
    confidence: MatchConfidence
    clarification_question: Optional[str] = None


def find_best_column(user_term: str, columns: List[str]) -> MatchResult:
    """
    Fuzzy-match user_term against df column names.
    Returns a MatchResult describing the best match and required action.
    """
    if not columns:
        return MatchResult(
            user_term=user_term,
            best_column=None,
            score=0.0,
            confidence=MatchConfidence.LOW,
            clarification_question=f"No columns are available. Please check your file.",
        )

    # Exact match first
    if user_term in columns:
        return MatchResult(
            user_term=user_term,
            best_column=user_term,
            score=100.0,
            confidence=MatchConfidence.EXACT,
        )

    # Case-insensitive exact
    lower_map = {c.lower(): c for c in columns}
    if user_term.lower() in lower_map:
        matched = lower_map[user_term.lower()]
        return MatchResult(
            user_term=user_term,
            best_column=matched,
            score=100.0,
            confidence=MatchConfidence.EXACT,
        )

    # Fuzzy match
    result = process.extractOne(
        user_term, columns, scorer=fuzz.WRatio
    )

    if result is None:
        return MatchResult(
            user_term=user_term,
            best_column=None,
            score=0.0,
            confidence=MatchConfidence.LOW,
            clarification_question=(
                f"I couldn't find a column called '{user_term}'. "
                f"Available columns are: {', '.join(columns)}. Which one did you mean?"
            ),
        )

    best_col, score, _ = result

    high_t = settings.fuzzy_high_threshold
    mid_t = settings.fuzzy_mid_threshold

    if score >= high_t:
        return MatchResult(
            user_term=user_term,
            best_column=best_col,
            score=score,
            confidence=MatchConfidence.HIGH,
        )
    elif score >= mid_t:
        return MatchResult(
            user_term=user_term,
            best_column=best_col,
            score=score,
            confidence=MatchConfidence.MID,
            clarification_question=(
                f"I couldn't find a column called '{user_term}'. "
                f"Did you mean '{best_col}'?"
            ),
        )
    else:
        available = ", ".join(f"'{c}'" for c in columns[:10])
        return MatchResult(
            user_term=user_term,
            best_column=None,
            score=score,
            confidence=MatchConfidence.LOW,
            clarification_question=(
                f"I couldn't find a column called '{user_term}'. "
                f"Available columns: {available}. Which column did you mean?"
            ),
        )


def extract_column_references(prompt: str, columns: List[str]) -> List[str]:
    """
    Heuristically extract likely column references from a user prompt.
    Returns a list of terms that *might* be column names.

    Handles both single-word columns ('Région') and multi-word columns
    ('Chiffre d'Affaires') by trying 1-, 2-, and 3-word n-grams.
    """
    tokens = prompt.split()
    references = []
    seen = set()

    # Try n-grams of size 3, 2, 1 (longest match first)
    for n in (3, 2, 1):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            clean = ngram.strip("'\",.!?():;")
            if len(clean) < 2 or clean.lower() in seen:
                continue
            result = process.extractOne(clean, columns, scorer=fuzz.WRatio)
            if result and result[1] >= settings.fuzzy_mid_threshold:
                references.append(clean)
                seen.add(clean.lower())
                # Skip tokens consumed by this n-gram
                break
    return references

