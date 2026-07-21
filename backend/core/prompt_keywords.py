"""
prompt_keywords.py — Single source of truth for data-intent keyword detection.

Both workers/tasks.py and api/prompts.py import DATA_KEYWORDS and strip_accents
from here so that additions never drift out of sync between the two files.
"""
import unicodedata


def strip_accents(s: str) -> str:
    """Normalize and remove diacritical marks from a string."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


# Canonical list of French/mixed keywords that signal a data-analysis intent.
# Edit ONLY here — tasks.py and prompts.py both import this list.
DATA_KEYWORDS = [
    "montre", "affiche", "graph", "evolution", "comparer",
    "total", "moyenne", "par mois", "par region", "par an",
    "combien", "quel", "quelle", "top", "pire", "meilleur",
    "histogramme", "camembert", "repartition", "reparti",
    "tendance", "diagramme", "circulaire", "chiffre", "ca",
    "visualise", "visualiser", "contribution", "distribution",
    "analyse", "analyser", "calcul", "calculer", "somme",
    "maximum", "minimum", "pourcentage", "proportion",
]
