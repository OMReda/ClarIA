"""
test_robustness.py — Tests for all logic fixes from the robustness audit.

Covers:
- Issue 2: Multi-word column fuzzy matching
- Issue 3: Pie chart crash on non-numeric values
- Issue 4: European number format (dot-thousands)
- Issue 5: Business-domain intent detection keywords
- Issue 6: French date parsing (dayfirst=True)
"""
import pytest
import pandas as pd

from backend.services.chart_resolver import detect_chart_type, build_chart_spec
from backend.services.fuzzy_matcher import find_best_column, extract_column_references
from backend.services.locale_normalizer import normalize_column, _parse_fr_number, _is_fr_number
from backend.services.file_validator import build_columns_metadata
from backend.core.prompt_keywords import DATA_KEYWORDS, strip_accents


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE 2: Multi-word column names in fuzzy matching
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiWordColumnMatching:

    def test_exact_match_multi_word(self):
        cols = ["Chiffre d'Affaires", "Région", "Date"]
        result = find_best_column("Chiffre d'Affaires", cols)
        assert result.best_column == "Chiffre d'Affaires"
        assert result.confidence.value == "exact"

    def test_case_insensitive_multi_word(self):
        cols = ["Chiffre d'Affaires", "Région", "Date"]
        result = find_best_column("chiffre d'affaires", cols)
        assert result.best_column == "Chiffre d'Affaires"

    def test_fuzzy_match_single_word(self):
        cols = ["Ventes", "Région", "Produit"]
        result = find_best_column("vente", cols)
        assert result.best_column == "Ventes"
        assert result.confidence.value == "mid"

    def test_no_match_returns_low(self):
        cols = ["Ventes", "Région", "Produit"]
        result = find_best_column("xyzabc", cols)
        assert result.confidence.value == "low"

    def test_empty_columns_returns_low(self):
        result = find_best_column("anything", [])
        assert result.confidence.value == "low"
        assert result.best_column is None


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE 3: Pie chart with non-numeric values
# ═══════════════════════════════════════════════════════════════════════════════

class TestPieChartRobustness:

    def test_pie_with_clean_data(self):
        df = pd.DataFrame({"Produit": ["A", "B", "C"], "Ventes": [100, 200, 300]})
        spec = build_chart_spec(df, "pie")
        assert spec["series"][0]["type"] == "pie"
        assert len(spec["series"][0]["data"]) == 3

    def test_pie_with_none_values(self):
        """Pie should skip None values without crashing."""
        df = pd.DataFrame({"Produit": ["A", "B", "C"], "Ventes": [100, None, 300]})
        spec = build_chart_spec(df, "pie")
        assert len(spec["series"][0]["data"]) == 2  # B skipped

    def test_pie_with_mixed_types(self):
        """Pie should skip non-numeric values (like 'N/A') without crashing."""
        df = pd.DataFrame({"Produit": ["A", "B", "C"], "Ventes": [100, "N/A", 300]})
        spec = build_chart_spec(df, "pie")
        assert len(spec["series"][0]["data"]) == 2  # "N/A" skipped

    def test_pie_groups_into_other_when_too_many(self):
        """More than 8 categories should be grouped into 'Other'."""
        df = pd.DataFrame({
            "Produit": [f"P{i}" for i in range(12)],
            "Ventes": list(range(100, 1300, 100)),
        })
        spec = build_chart_spec(df, "pie")
        names = [d["name"] for d in spec["series"][0]["data"]]
        assert "Other" in names
        assert len(spec["series"][0]["data"]) == 8  # 7 + Other

    def test_pie_with_single_numeric_column(self):
        """Single numeric column should not crash — uses index as labels."""
        df = pd.DataFrame({"Montant": [100, 200, 300]})
        spec = build_chart_spec(df, "pie")
        assert spec["series"][0]["type"] == "pie"


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE 4: European number format (dot-thousands)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLocaleNormalizerRobustness:

    def test_space_thousands(self):
        """Standard French: 1 234,56 → 1234.56"""
        assert _parse_fr_number("1 234,56") == 1234.56

    def test_dot_thousands(self):
        """European Excel export: 1.234,56 → 1234.56"""
        assert _is_fr_number("1.234,56")
        assert _parse_fr_number("1.234,56") == 1234.56

    def test_dot_thousands_large(self):
        """Large European number: 1.234.567,89 → 1234567.89"""
        assert _is_fr_number("1.234.567,89")
        assert _parse_fr_number("1.234.567,89") == 1234567.89

    def test_negative_french_number(self):
        assert _parse_fr_number("-1 234,56") == -1234.56

    def test_no_decimal(self):
        assert _parse_fr_number("1 234") == 1234.0

    def test_normalize_column_with_dot_thousands(self):
        """Full column normalization with European format."""
        series = pd.Series(["1.234,56", "2.345,67", "3.456,78"])
        result = normalize_column(series)
        assert result.iloc[0] == 1234.56
        assert result.iloc[1] == 2345.67

    def test_normalize_column_preserves_non_numbers(self):
        """Column with mixed types: normalize numbers, keep text."""
        series = pd.Series(["Paris", "Lyon", "Marseille"])
        result = normalize_column(series)
        assert result.iloc[0] == "Paris"  # Unchanged


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE 5: Intent detection — business-domain keywords
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntentDetectionKeywords:

    def _has_keyword(self, prompt: str) -> bool:
        """Simulate the intent detection logic from prompts.py and tasks.py."""
        norm = strip_accents(prompt.lower())
        return any(strip_accents(kw.lower()) in norm for kw in DATA_KEYWORDS)

    def test_basic_french_prompts(self):
        assert self._has_keyword("montre les ventes")
        assert self._has_keyword("affiche le total")
        assert self._has_keyword("quelle est la moyenne")

    def test_chart_name_prompts(self):
        assert self._has_keyword("fais un camembert")
        assert self._has_keyword("courbe des ventes")
        assert self._has_keyword("diagramme en barre")

    def test_business_domain_prompts(self):
        """NEW: These used to fail before adding business keywords."""
        assert self._has_keyword("quel est le bénéfice total")
        assert self._has_keyword("montre la croissance")
        assert self._has_keyword("budget par département")
        assert self._has_keyword("coût moyen par produit")
        assert self._has_keyword("quantité en stock")
        assert self._has_keyword("marge par client")
        assert self._has_keyword("revenu par trimestre")

    def test_ranking_prompts(self):
        assert self._has_keyword("classement des meilleurs vendeurs")
        assert self._has_keyword("top 5 des produits")
        assert self._has_keyword("flop des régions")

    def test_grouping_prompts(self):
        """NEW: More 'par X' grouping phrases."""
        assert self._has_keyword("ventes par jour")
        assert self._has_keyword("résultat par semaine")
        assert self._has_keyword("par trimestre")
        assert self._has_keyword("par catégorie")

    def test_non_data_prompt_rejected(self):
        """A prompt with no data keywords should NOT match."""
        assert not self._has_keyword("bonjour comment ça va")
        assert not self._has_keyword("merci beaucoup")
        assert not self._has_keyword("au revoir")


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUE 6: French date parsing (dayfirst=True)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrenchDateParsing:

    def test_build_columns_metadata_detects_french_dates(self):
        """French dates dd/mm/yyyy should be detected as datetime, not text."""
        df = pd.DataFrame({
            "Date": ["01/03/2024", "15/06/2024", "25/12/2024"],
            "Valeur": [100, 200, 300],
        })
        metadata = build_columns_metadata(df)
        date_col = next(m for m in metadata if m["name"] == "Date")
        assert date_col["dtype"] == "datetime"

    def test_iso_dates_detected(self):
        """ISO dates yyyy-mm-dd should also be detected."""
        df = pd.DataFrame({
            "Date": ["2024-01-15", "2024-06-20", "2024-12-31"],
            "Valeur": [100, 200, 300],
        })
        metadata = build_columns_metadata(df)
        date_col = next(m for m in metadata if m["name"] == "Date")
        assert date_col["dtype"] == "datetime"

    def test_numeric_column_detected(self):
        df = pd.DataFrame({"Prix": [10.5, 20.3, 30.1]})
        metadata = build_columns_metadata(df)
        assert metadata[0]["dtype"] == "numeric"

    def test_text_column_detected(self):
        df = pd.DataFrame({"Ville": ["Paris", "Lyon", "Marseille"]})
        metadata = build_columns_metadata(df)
        assert metadata[0]["dtype"] == "text"
