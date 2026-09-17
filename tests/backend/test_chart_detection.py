"""
test_chart_detection.py — Verify detect_chart_type() picks the right chart.

Focus: explicit chart names MUST override contextual keywords.
e.g. "camembert par mois" → pie (NOT line)
"""
import pytest
from backend.services.chart_resolver import detect_chart_type

# ── Test fixtures ─────────────────────────────────────────────────────────────

COLS_MIXED = [
    {"name": "Région", "dtype": "categorical"},
    {"name": "Date", "dtype": "datetime"},
    {"name": "Ventes", "dtype": "numeric"},
]

COLS_CAT_NUM = [
    {"name": "Produit", "dtype": "categorical"},
    {"name": "Chiffre", "dtype": "numeric"},
]

COLS_NUM_ONLY = [
    {"name": "Valeur", "dtype": "numeric"},
]

COLS_TWO_NUM = [
    {"name": "Poids", "dtype": "numeric"},
    {"name": "Taille", "dtype": "numeric"},
]

COLS_DATE_NUM = [
    {"name": "Date", "dtype": "datetime"},
    {"name": "Revenue", "dtype": "numeric"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. EXPLICIT CHART NAME OVERRIDE — the bug fix
#    When the user says the NAME of a chart, that MUST win over any other keyword.
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplicitChartNameOverride:
    """The core bug: 'camembert par mois' was returning 'line' instead of 'pie'."""

    def test_camembert_par_mois_returns_pie(self):
        """BUG FIX: 'par mois' is a LINE keyword, but 'camembert' is an explicit pie name."""
        assert detect_chart_type("camembert des ventes par mois", COLS_MIXED) == "pie"

    def test_camembert_evolution_returns_pie(self):
        """'évolution' is a LINE keyword, but 'camembert' must win."""
        assert detect_chart_type("camembert de l'évolution", COLS_MIXED) == "pie"

    def test_camembert_tendance_returns_pie(self):
        """'tendance' is a LINE keyword, but 'camembert' must win."""
        assert detect_chart_type("camembert de la tendance des ventes", COLS_MIXED) == "pie"

    def test_camembert_simple(self):
        assert detect_chart_type("camembert des ventes", COLS_CAT_NUM) == "pie"

    def test_camembert_typo_cammembert(self):
        assert detect_chart_type("cammembert des ventes par region", COLS_MIXED) == "pie"

    def test_camembert_typo_camenbert(self):
        assert detect_chart_type("camenbert par produit", COLS_CAT_NUM) == "pie"

    def test_pie_keyword(self):
        assert detect_chart_type("pie chart of sales", COLS_CAT_NUM) == "pie"

    def test_donut_keyword(self):
        assert detect_chart_type("donut des ventes par région", COLS_MIXED) == "pie"

    def test_barre_overrides_par_mois(self):
        """'barre' must win over 'par mois' (LINE keyword)."""
        assert detect_chart_type("barre des ventes par mois", COLS_MIXED) == "bar"

    def test_courbe_overrides_par_categorie(self):
        """'courbe' must win over 'par categorie' (BAR keyword)."""
        assert detect_chart_type("courbe par catégorie", COLS_CAT_NUM) == "line"

    def test_nuage_de_points_overrides_evolution(self):
        """'nuage de points' must win over 'évolution' (LINE keyword)."""
        assert detect_chart_type("nuage de points de l'évolution", COLS_TWO_NUM) == "scatter"

    def test_radar_overrides_par_mois(self):
        assert detect_chart_type("radar par mois", COLS_MIXED) == "radar"

    def test_heatmap_overrides_evolution(self):
        assert detect_chart_type("heatmap de l'évolution", COLS_MIXED) == "heatmap"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CONTEXTUAL KEYWORDS (when no explicit chart name is used)
#    These should still work as before.
# ═══════════════════════════════════════════════════════════════════════════════

class TestContextualKeywords:
    """When the user does NOT name a chart type, contextual keywords decide."""

    def test_evolution_returns_line(self):
        assert detect_chart_type("montre l'évolution des ventes", COLS_DATE_NUM) == "line"

    def test_tendance_returns_line(self):
        assert detect_chart_type("quelle est la tendance", COLS_DATE_NUM) == "line"

    def test_par_mois_returns_line(self):
        assert detect_chart_type("ventes par mois", COLS_DATE_NUM) == "line"

    def test_proportion_returns_pie(self):
        assert detect_chart_type("proportion des ventes par produit", COLS_CAT_NUM) == "pie"

    def test_pourcentage_returns_pie(self):
        assert detect_chart_type("pourcentage par catégorie", COLS_CAT_NUM) == "pie"

    def test_repartition_with_categorical_returns_pie(self):
        assert detect_chart_type("répartition par produit", COLS_CAT_NUM) == "pie"

    def test_distribution_returns_histogram(self):
        assert detect_chart_type("distribution des valeurs", COLS_NUM_ONLY) == "histogram"

    def test_frequence_returns_histogram(self):
        assert detect_chart_type("fréquence des prix", COLS_NUM_ONLY) == "histogram"

    def test_correlation_returns_scatter(self):
        assert detect_chart_type("corrélation entre poids et taille", COLS_TWO_NUM) == "scatter"

    def test_nuage_returns_scatter(self):
        assert detect_chart_type("nuage entre poids et taille", COLS_TWO_NUM) == "scatter"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SEMANTIC FALLBACK (no keywords at all — infer from column types)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticFallback:
    """When no keywords match, the function infers from column types."""

    def test_date_plus_numeric_defaults_to_line(self):
        assert detect_chart_type("montre moi les données", COLS_DATE_NUM) == "line"

    def test_categorical_plus_numeric_defaults_to_bar(self):
        assert detect_chart_type("montre moi les données", COLS_CAT_NUM) == "bar"

    def test_two_numerics_defaults_to_scatter(self):
        assert detect_chart_type("montre moi les données", COLS_TWO_NUM) == "scatter"

    def test_single_numeric_defaults_to_histogram(self):
        assert detect_chart_type("montre moi les données", COLS_NUM_ONLY) == "histogram"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_histogramme_des_goes_to_bar(self):
        """'histogramme des ventes' — 'histogramme' is an explicit name so it returns histogram.
        The 'histogramme des' → bar disambiguation is only useful when 'histogramme' itself
        doesn't match first (which it now does via the explicit override)."""
        result = detect_chart_type("histogramme des ventes par region", COLS_CAT_NUM)
        assert result == "histogram"

    def test_histogramme_alone_goes_to_histogram(self):
        """'histogramme' alone → real histogram."""
        assert detect_chart_type("histogramme des prix", COLS_NUM_ONLY) == "histogram"

    def test_repartition_numeric_only_goes_to_histogram(self):
        """'répartition' with only numeric columns → histogram (no categories for pie)."""
        assert detect_chart_type("répartition des valeurs", COLS_NUM_ONLY) == "histogram"

    def test_compare_with_dates_returns_line(self):
        assert detect_chart_type("compare les ventes 2023-2024", COLS_DATE_NUM) == "line"

    def test_compare_with_categories_returns_bar(self):
        assert detect_chart_type("compare les produits", COLS_CAT_NUM) == "bar"

    def test_empty_prompt_returns_fallback(self):
        """Empty prompt should still return a sensible fallback based on columns."""
        result = detect_chart_type("", COLS_CAT_NUM)
        assert result == "bar"  # categorical + numeric → bar
