"""
error_catalog.py — Human-readable error messages for every API error code.

Each entry is a dict with:
  - "title"  : Short, friendly title shown to the user  (≤ 8 words)
  - "message": Full natural-language explanation  (complete sentence)
  - "hint"   : Optional actionable tip so the user knows what to do next

Both files.py and prompts.py import USER_ERRORS and call `user_error()`.
Do NOT scatter hard-coded message strings across the codebase — add them here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

# ── Catalog ───────────────────────────────────────────────────────────────────

USER_ERRORS: Dict[str, Dict[str, str]] = {
    # ── File upload & validation ──────────────────────────────────────────────
    "FILE_TOO_LARGE": {
        "title": "Fichier trop volumineux",
        "message": (
            "Le fichier que vous avez envoyé dépasse la limite autorisée de {max_size_mb} Mo. "
            "Veuillez réduire la taille de votre fichier avant de réessayer."
        ),
        "hint": "Essayez de supprimer des colonnes inutiles ou de diviser le fichier en plusieurs parties.",
    },
    "INVALID_FILE_TYPE": {
        "title": "Type de fichier non supporté",
        "message": (
            "Seuls les fichiers CSV et Excel (.xlsx / .xls) sont acceptés. "
            "Le fichier que vous avez envoyé semble être d'un autre format ({detected_mime})."
        ),
        "hint": "Exportez votre fichier depuis Excel ou un tableur au format CSV ou .xlsx, puis réessayez.",
    },
    "EMPTY_FILE": {
        "title": "Fichier vide",
        "message": "Le fichier importé ne contient aucune donnée. Veuillez vérifier son contenu avant de le renvoyer.",
        "hint": "Assurez-vous que le fichier contient au moins une ligne de données en plus de l'en-tête.",
    },
    "DUPLICATE_FILE": {
        "title": "Fichier déjà importé",
        "message": (
            "Un fichier portant le même nom a déjà été importé dans votre espace. "
            "Renommez votre fichier ou supprimez l'ancien avant d'en importer un nouveau."
        ),
        "hint": "Vous pouvez supprimer l'ancien fichier depuis votre tableau de bord, puis réimporter.",
    },
    "UNREADABLE_ENCODING": {
        "title": "Encodage de fichier non reconnu",
        "message": (
            "Nous n'avons pas réussi à lire votre fichier à cause de son encodage de caractères. "
            "Cela arrive souvent avec des fichiers Windows anciens ou des exports spéciaux."
        ),
        "hint": "Dans Excel, utilisez « Enregistrer sous » → format CSV UTF-8 ou choisissez l'encodage Latin-1.",
    },
    "PARSE_ERROR": {
        "title": "Impossible de lire le fichier",
        "message": (
            "Une erreur inattendue s'est produite lors de la lecture de votre fichier. "
            "Il est possible que le fichier soit corrompu ou dans un format inhabituel."
        ),
        "hint": "Essayez d'ouvrir le fichier dans Excel et de le ré-enregistrer, puis importez-le à nouveau.",
    },
    "TOO_MANY_ROWS": {
        "title": "Trop de lignes",
        "message": (
            "Votre fichier contient {received_rows:,} lignes, ce qui dépasse la limite de {max_rows:,} lignes. "
            "La plateforme ne peut pas traiter des fichiers aussi grands pour le moment."
        ),
        "hint": "Filtrez ou découpez votre fichier pour ne conserver que les données nécessaires.",
    },
    "PAYLOAD_TOO_LARGE": {
        "title": "Configuration trop volumineuse",
        "message": (
            "La configuration du tableau de bord dépasse la taille maximale autorisée (500 Ko). "
            "Veuillez simplifier votre tableau de bord."
        ),
        "hint": "Réduisez le nombre de graphiques ou supprimez les éléments inutilisés.",
    },

    # ── File lookup & permissions ─────────────────────────────────────────────
    "FILE_NOT_FOUND": {
        "title": "Fichier introuvable",
        "message": (
            "Le fichier demandé n'existe pas ou a été supprimé. "
            "Vérifiez que vous avez bien sélectionné le bon fichier."
        ),
        "hint": "Retournez à votre tableau de bord et sélectionnez un fichier existant.",
    },
    "INVALID_FILE_ID": {
        "title": "Identifiant de fichier invalide",
        "message": (
            "L'identifiant de fichier fourni n'est pas reconnu. "
            "Cela peut indiquer un lien corrompu ou une requête mal formée."
        ),
        "hint": "Rechargez la page et réessayez. Si le problème persiste, contactez le support.",
    },
    "FORBIDDEN": {
        "title": "Accès refusé",
        "message": (
            "Vous n'êtes pas autorisé à accéder à cette ressource. "
            "Elle appartient à un autre utilisateur ou à une autre session."
        ),
        "hint": "Connectez-vous avec le bon compte ou sélectionnez une ressource qui vous appartient.",
    },

    # ── Prompts ───────────────────────────────────────────────────────────────
    "EMPTY_PROMPT": {
        "title": "Question vide",
        "message": "Vous n'avez pas saisi de question. Veuillez écrire ce que vous souhaitez analyser ou visualiser.",
        "hint": "Exemple : « Montre les ventes par région sous forme de camembert ».",
    },
    "FILE_NOT_READY": {
        "title": "Fichier pas encore prêt",
        "message": (
            "Le fichier sélectionné n'est pas encore validé et ne peut pas être interrogé pour l'instant. "
            "Son statut actuel est : {status}."
        ),
        "hint": "Si un fichier Excel multi-feuilles attend une sélection de feuille, effectuez-la d'abord.",
    },
    "RATE_LIMIT_EXCEEDED": {
        "title": "Limite de questions atteinte",
        "message": (
            "Vous avez posé {current_count} questions cette heure, ce qui dépasse la limite de {limit}. "
            "Attendez quelques minutes avant d'en poser une nouvelle."
        ),
        "hint": "La limite se réinitialise automatiquement au début de chaque heure.",
    },
    "MISSING_API_KEY": {
        "title": "Clé API manquante",
        "message": (
            "Pour utiliser le modèle {provider}, vous devez d'abord renseigner votre clé API "
            "dans les paramètres de la plateforme."
        ),
        "hint": "Allez dans ⚙ Paramètres → Clés API et entrez votre clé {provider} pour continuer.",
    },
    "PROMPT_NOT_FOUND": {
        "title": "Question introuvable",
        "message": (
            "La question demandée n'existe pas ou a expiré. "
            "Il est possible qu'elle ait été supprimée ou que son identifiant soit incorrect."
        ),
        "hint": "Retournez à la liste de vos questions et réessayez.",
    },
    "INVALID_PROMPT_ID": {
        "title": "Identifiant de question invalide",
        "message": "L'identifiant de question fourni n'est pas reconnu. La requête semble mal formée.",
        "hint": "Rechargez la page et réessayez. Si le problème persiste, contactez le support.",
    },
    "PROMPT_NOT_AWAITING_CLARIFICATION": {
        "title": "Pas de clarification attendue",
        "message": (
            "Cette question n'est pas en attente de précision de votre part (statut actuel : {status}). "
            "Vous ne pouvez répondre à une demande de clarification que lorsque la question est dans l'état 'awaiting_clarification'."
        ),
        "hint": "Vérifiez le statut de votre question et réessayez si nécessaire.",
    },
    "EMPTY_ANSWER": {
        "title": "Réponse de clarification vide",
        "message": "Votre réponse de clarification ne peut pas être vide. Veuillez saisir une réponse avant de valider.",
        "hint": "Répondez précisément à la question posée par l'assistant pour qu'il puisse continuer.",
    },

    # ── Data / columns ────────────────────────────────────────────────────────
    "INVALID_COLUMN": {
        "title": "Colonne introuvable",
        "message": (
            "La colonne « {column} » n'existe pas dans votre fichier. "
            "Vérifiez l'orthographe ou choisissez une colonne présente dans vos données."
        ),
        "hint": "Les colonnes disponibles sont visibles dans l'aperçu de votre fichier.",
    },
    "INVALID_AGGREGATION": {
        "title": "Agrégation non valide",
        "message": (
            "L'opération d'agrégation demandée n'est pas supportée. "
            "Les opérations disponibles sont : somme, moyenne, nombre, minimum et maximum."
        ),
        "hint": "Choisissez parmi : sum, avg, count, min, max.",
    },
    "INVALID_DTYPE": {
        "title": "Type de colonne incompatible",
        "message": (
            "L'opération demandée nécessite une colonne numérique, "
            "mais la colonne « {column} » contient du texte ou des dates."
        ),
        "hint": "Choisissez une colonne contenant des chiffres pour effectuer ce calcul.",
    },
    "AGGREGATION_ERROR": {
        "title": "Erreur de calcul",
        "message": "Le calcul demandé sur la colonne « {column} » a échoué. Il est possible que la colonne contienne des valeurs inattendues.",
        "hint": "Vérifiez que la colonne ne contient pas de valeurs manquantes ou de texte mélangé avec des chiffres.",
    },
}

# ── Helper ────────────────────────────────────────────────────────────────────

def user_error(
    code: str,
    http_status: int = 400,
    details: Optional[Dict[str, Any]] = None,
    **fmt_kwargs: Any,
) -> HTTPException:
    """
    Build an HTTPException with a fully human-readable error payload.

    The response body is:
    {
        "error": {
            "code":    "FILE_TOO_LARGE",
            "title":   "Fichier trop volumineux",
            "message": "Le fichier … dépasse …",
            "hint":    "Essayez de …",
            "details": { ... }   # optional raw details (size, limit, …)
        }
    }

    Usage:
        raise user_error("FILE_TOO_LARGE", details=exc.details, max_size_mb=10)
        raise user_error("FORBIDDEN", http_status=403)
        raise user_error("RATE_LIMIT_EXCEEDED", http_status=429,
                         limit=30, current_count=31)
    """
    entry = USER_ERRORS.get(code)
    if entry is None:
        # Fallback for undocumented codes — still human-readable
        return HTTPException(
            status_code=http_status,
            detail={
                "error": {
                    "code": code,
                    "title": "Une erreur inattendue s'est produite",
                    "message": (
                        "Une erreur inattendue s'est produite. "
                        "Veuillez réessayer ou contacter le support si le problème persiste."
                    ),
                    "hint": "Rechargez la page et réessayez.",
                    "details": details or {},
                }
            },
        )

    # Merge details into fmt_kwargs so {max_size_mb} works in message templates
    merged = dict(details or {})
    merged.update(fmt_kwargs)

    def _fmt(s: str) -> str:
        try:
            return s.format_map(merged)
        except (KeyError, ValueError):
            return s  # return un-interpolated if a key is missing

    return HTTPException(
        status_code=http_status,
        detail={
            "error": {
                "code": code,
                "title": entry["title"],
                "message": _fmt(entry["message"]),
                "hint": _fmt(entry.get("hint", "")),
                "details": details or {},
            }
        },
    )
