# Audit Results — Logic Issues Found
# ====================================

## ISSUE 1 — FIXED: Chart type detection priority (camembert bug)
# Status: ALREADY FIXED in previous commit

## ISSUE 2 — extract_column_references splits on whitespace only
# Problem: "ventes_totales" is one token but "ventes totales" becomes two tokens.
# Multi-word column names like "Chiffre d'Affaires" are split into 3 tokens,
# none of which individually match the full column name.
# Fix: Also try n-grams (2-word, 3-word combinations)

## ISSUE 3 — _pie crashes when value_col has non-numeric values
# Problem: float(v) in _pie() will crash on strings if PandasAI returns mixed types
# Fix: Add try/except around the float() conversion

## ISSUE 4 — Locale normalizer doesn't handle "1.234,56" (dot as thousands)
# Problem: European CSV exported from Excel uses "1.234,56" format (dot thousands, comma decimal)
# Current regex only handles space thousands: "1 234,56"
# Fix: Extend _FR_NUMBER_RE to also match dot-separated thousands

## ISSUE 5 — Intent detection keywords missing common French phrases
# Problem: Words like "résumé", "statistique", "croissance", "bénéfice", "recette",
# "dépense", "budget", "coût", "prix", "quantité" are not in DATA_KEYWORDS
# Fix: Add more business-domain keywords

## ISSUE 6 — build_columns_metadata uses dayfirst=False for date inference
# Problem: French dates like "01/03/2024" (1st March) will be parsed as January 3rd
# because dayfirst=False. This contradicts the locale normalizer which assumes dayfirst=True.
# Fix: Change to dayfirst=True
