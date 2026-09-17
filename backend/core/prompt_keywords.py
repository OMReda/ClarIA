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
    # ── Verbs / actions ──
    "montre", "affiche", "graph", "evolution", "comparer",
    "visualise", "visualiser", "analyse", "analyser",
    "calcul", "calculer", "resume", "resumer",
    # ── Aggregation / statistics ──
    "total", "moyenne", "somme", "comptage",
    "maximum", "minimum", "pourcentage", "proportion",
    "statistique", "statistiques", "mediane", "ecart",
    # ── Grouping signals ──
    "par mois", "par region", "par an", "par jour",
    "par semaine", "par trimestre", "par categorie",
    "par produit", "par client", "par ville", "par pays",
    # ── Questions ──
    "combien", "quel", "quelle", "quels", "quelles",
    # ── Ranking / top-flop ──
    "top", "pire", "meilleur", "meilleures", "meilleurs",
    "classement", "ranking", "flop",
    # ── Chart types (explicit names) ──
    "histogramme", "camembert", "cammembert", "camenbert",
    "repartition", "reparti", "diagramme", "circulaire",
    "courbe", "barre", "barres", "nuage", "radar",
    "heatmap", "aire",
    # ── Business-domain (French + English) ──
    "tendance", "chiffre", "contribution", "distribution",
    "croissance", "benefice", "recette", "depense",
    "budget", "cout", "prix", "quantite", "marge",
    "revenu", "vente", "ventes", "stock", "commande",
    "facture", "client", "fournisseur", "effectif",
    "salaire", "charge", "profit", "perte",
]
