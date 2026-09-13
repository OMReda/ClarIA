"""
tasks.py — Celery tasks for prompt processing.

DockerSandbox lifecycle:
  - sandbox is started once per worker process (via worker_init signal)
  - shared via module-level _sandbox variable
  - stopped on worker_shutdown
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from billiard.exceptions import SoftTimeLimitExceeded
from celery import signals
from sqlalchemy import select

from backend.core.config import get_settings
from backend.core.database import get_sync_session
from backend.core.llm_client import build_aggregation_prompt, classify_data_intent, configure_pandasai, generate_explanation, _is_comparison_prompt
from backend.core.prompt_keywords import DATA_KEYWORDS, strip_accents as _strip_accents
from backend.models.chart import Chart
from backend.models.file import File as FileModel
from backend.models.prompt import Prompt
from backend.services.chart_resolver import build_chart_spec, detect_chart_type
from backend.services.file_validator import load_dataframe_from_path
from backend.services.fuzzy_matcher import MatchConfidence, extract_column_references, find_best_column
from backend.workers.celery_app import celery_app

import redis as _redis_module

logger = logging.getLogger(__name__)
settings = get_settings()

_sandbox = None  # DockerSandbox instance, pre-warmed per worker


# ── Worker lifecycle ──────────────────────────────────────────────────────────

@signals.worker_init.connect
def on_worker_init(**_kwargs):
    """Start DockerSandbox and configure PandasAI once per worker."""
    global _sandbox
    try:
        from pandasai_docker import DockerSandbox  # type: ignore
        _sandbox = DockerSandbox()
        _sandbox.start()
        logger.info("DockerSandbox started for worker.")
    except Exception as exc:
        logger.warning("DockerSandbox unavailable (%s). Code will run unsandboxed.", exc)
        _sandbox = None

    try:
        configure_pandasai()
    except Exception as exc:
        logger.error("PandasAI configuration failed: %s", exc)


@signals.worker_shutdown.connect
def on_worker_shutdown(**_kwargs):
    """Stop DockerSandbox on clean shutdown."""
    global _sandbox
    if _sandbox is not None:
        try:
            _sandbox.stop()
            logger.info("DockerSandbox stopped.")
        except Exception:
            pass


# ── Redis pub/sub helper ──────────────────────────────────────────────────────

def _publish_ws_event(prompt_id: str, event: dict) -> None:
    """Publish a WebSocket event via Redis pub/sub."""
    try:
        r = _redis_module.from_url(settings.redis_url, decode_responses=True)
        r.publish(f"ws:prompt:{prompt_id}", json.dumps(event))
    except Exception as exc:
        logger.warning("Failed to publish WS event: %s", exc)


# ── Main task ─────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="process_prompt", max_retries=0)
def process_prompt(self, prompt_id: str, llm_config: dict | None = None) -> None:
    """
    Full prompt processing pipeline:
    1. Load file + column metadata
    2. Fuzzy-match column references in the prompt
    3. Detect chart type
    4. Call PandasAI (engineered prompt → aggregated DataFrame)
    5. Convert result → ECharts spec
    6. Persist result, publish WS event
    """
    db = get_sync_session()
    try:
        prompt_uuid = uuid.UUID(prompt_id)
        prompt: Optional[Prompt] = db.get(Prompt, prompt_uuid)
        if prompt is None:
            logger.error("Prompt %s not found", prompt_id)
            return

        # ── Log prompt text unconditionally (Issue 25) ───────────────────────
        # Always emitted here, regardless of what happens later (LLM error,
        # file-not-found, classification failure, etc.) — makes every task
        # debuggable from the worker logs.
        logger.info(
            "process_prompt START | id=%s | text=%r",
            prompt_id, prompt.raw_text or "(empty)",
        )

        # ── Mark processing ───────────────────────────────────────────────────
        prompt.status = "processing"
        db.commit()
        _publish_ws_event(prompt_id, {"status": "processing", "message": "Analysing your request…"})



        # ── Configure PandasAI with per-request LLM settings ──────────────────────
        try:
            actual_provider = configure_pandasai(llm_config=llm_config or {})
        except Exception as exc:
            logger.error("PandasAI LLM configuration failed: %s", exc)
            _fail_prompt(db, prompt, f"LLM configuration error: {exc}", prompt_id)
            return

        # Notify user immediately if Ollama was down and a fallback was used
        if actual_provider.endswith("-fallback"):
            fb_label = {"google-fallback": "Google", "openai-fallback": "OpenAI", "anthropic-fallback": "Anthropic"}.get(actual_provider, "cloud")
            _publish_ws_event(prompt_id, {
                "status": "processing",
                "fallback_notice": f"Ollama hors ligne — réponse générée via {fb_label}",
            })


        # ── Load file ─────────────────────────────────────────────────────────
        file = db.get(FileModel, prompt.file_id)
        if file is None:
            logger.error("File not found for prompt %s", prompt_id)
            _fail_prompt(db, prompt, "Source file not found.", prompt_id)
            return

        columns_metadata = file.columns_metadata or []
        column_names = [c["name"] for c in columns_metadata]

        df = load_dataframe_from_path(file.storage_path, sheet_name=file.sheet_name)

        # ── Intent Detection (LLM-based for cloud, keywords for local) ────────
        # For local/Ollama models: skip the extra LLM call (it would double
        # latency on an already-slow local model). Use keyword matching instead.
        # For cloud providers (Google, OpenAI, Anthropic): ask the LLM — it
        # handles any language/phrasing with zero false positives.
        _provider = (llm_config or {}).get("provider", settings.llm_provider).lower()
        _use_llm_classify = _provider in ("google", "openai", "anthropic")

        if _use_llm_classify:
            llm_says = classify_data_intent(prompt.raw_text, column_names)
        else:
            llm_says = None  # fall through to keyword fallback below

        if llm_says is None:
            # Keyword fallback (instant, used for local models and LLM failures)
            text_norm = _strip_accents(prompt.raw_text.lower())
            llm_says = any(kw in text_norm for kw in DATA_KEYWORDS) or any(
                len(_strip_accents(c.lower())) > 2 and _strip_accents(c.lower()) in text_norm
                for c in column_names
            )

        if not llm_says:
            cols_str = ", ".join(column_names[:3]) + ("..." if len(column_names) > 3 else "")
            msg = (
                f"Je suis là pour analyser vos données ! Essayez une question comme : "
                f"'Montre l'évolution sous forme de graphique' ou une question sur une colonne de votre fichier ({cols_str})."
            )
            _fail_prompt(db, prompt, msg, prompt_id)
            return

        # ── Build effective prompt (with clarification answer if present) ──────
        user_text = prompt.raw_text
        if prompt.clarification_answer:
            user_text = f"{user_text}\n[Clarification]: {prompt.clarification_answer}"

        # ── Proactive Fuzzy Matching ──────────────────────────────────────────
        refs = extract_column_references(user_text, column_names)
        for ref in refs:
            match = find_best_column(ref, column_names)
            if match.confidence == MatchConfidence.HIGH and match.best_column and match.best_column.lower() != ref.lower():
                # Replace word occurrences with the exact column name
                user_text = re.sub(rf"\b{re.escape(ref)}\b", match.best_column, user_text, flags=re.IGNORECASE)

        # ── Detect chart type ─────────────────────────────────────────────────
        # Ensure we only use the original raw_text so column replacements and
        # clarification answers do NOT falsely trigger keyword matches.
        chart_type = detect_chart_type(prompt.raw_text, columns_metadata)
        if chart_type is None:
            chart_type = "text"

        # Detect comparison intent — used later to auto-pivot flat DataFrames
        # into multi-series (e.g. Date/Product/Revenue -> Date with two value cols)
        is_comparison = _is_comparison_prompt(prompt.raw_text)

        # ── Call PandasAI (aggregated DataFrame back, not a plot) ─────────────
        columns_info = ", ".join(
            f"{c['name']} ({c['dtype']})" for c in columns_metadata
        )
        engineered_prompt = build_aggregation_prompt(user_text, chart_type, columns_info, provider=_provider)

        try:
            import pandasai as pai  # lazy — not available on Python 3.14 dev hosts
            pai_df = pai.DataFrame(df)
        except ImportError:
            _fail_prompt(db, prompt, "PandasAI is not installed. Run inside Docker.", prompt_id)
            return

        try:
            if _sandbox is not None:
                response = pai_df.chat(engineered_prompt, sandbox=_sandbox)
            else:
                response = pai_df.chat(engineered_prompt)
        except SoftTimeLimitExceeded:
            logger.error("Task time limit exceeded for prompt %s", prompt_id)
            _fail_prompt(db, prompt, "La génération a pris trop de temps et a expiré. Réessayez ou posez une question plus simple.", prompt_id)
            return
        except Exception as exc:
            logger.exception("PandasAI execution failed for prompt %s", prompt_id)
            exc_str = str(exc)
            exc_type = type(exc).__name__

            # 0. NoResultFoundError — local model didn't format result correctly.
            # Must be checked by class name because str(exc) only yields the message,
            # never the class name, so the string-based check below would miss it.
            if exc_type == "NoResultFoundError":
                _fail_prompt(db, prompt,
                    "Le modèle local n'a pas réussi à formater le code correctement. "
                    "Veuillez réessayer ou utiliser un modèle plus performant (ex: Gemini ou un modèle local plus large).",
                    prompt_id)
                return

            # 1. Mask raw litellm/PandasAI generation failures behind friendly UI message
            # Do this BEFORE clarification logic so API error JSON isn't misread as column names.
            if any(err in exc_str for err in [
                "litellm.", "APIConnectionError", "MaxRetryError", 
                "Timeout", "OllamaException", "AuthenticationError", 
                "APIError", "BadRequestError", "RateLimitError"
            ]):
                friendly_msg = "Une erreur inattendue est survenue avec le modèle d'IA."
                
                # Check for specific known errors to give a precise human-readable message
                if "503" in exc_str or "ServiceUnavailableError" in exc_str or "high demand" in exc_str:
                    friendly_msg = "Le modèle d'IA est temporairement surchargé en raison d'une forte demande. Veuillez réessayer dans quelques instants."
                elif "401" in exc_str or "AuthenticationError" in exc_str or "invalid_api_key" in exc_str:
                    friendly_msg = "Clé API invalide ou non reconnue. Veuillez vérifier votre clé dans les paramètres."
                elif "429" in exc_str or "RateLimitError" in exc_str or "quota" in exc_str:
                    friendly_msg = "Vous avez dépassé le quota ou la limite de requêtes du modèle d'IA. Veuillez patienter un peu avant de réessayer."
                elif "Timeout" in exc_str or "timeout" in exc_str.lower():
                    friendly_msg = "La génération a pris trop de temps et a expiré. Réessayez ou posez une question plus simple."
                elif "ConnectionError" in exc_str or "MaxRetryError" in exc_str:
                    friendly_msg = "Impossible de se connecter au service d'IA. Vérifiez votre connexion internet ou que le service local est bien démarré."
                elif "NoResultFoundError" in exc_str:
                    friendly_msg = "Le modèle local n'a pas réussi à formater le code correctement. Veuillez réessayer ou utiliser un modèle plus performant (ex: Gemini ou un modèle local plus large)."
                else:
                    # If it's another API error, try to extract a clean message if possible, or fall back
                    match = re.search(r'"message":\s*"([^"]+)"', exc_str)
                    if match:
                        friendly_msg = f"Erreur de l'IA : {match.group(1)}"
                
                _fail_prompt(db, prompt, friendly_msg, prompt_id)
                return
            
            # 2. Post-execution clarification: only trigger if the runtime error mentions an unknown column
            clarification_needed = None
            quoted_terms = re.findall(r"['\"](.+?)['\"]", exc_str)
            
            for term in quoted_terms:
                if len(term) < 2 or term in column_names:
                    continue
                match = find_best_column(term, column_names)
                if match.confidence in (MatchConfidence.MID, MatchConfidence.LOW) and match.score > 40:
                    clarification_needed = match.clarification_question
                    break
                    
            if clarification_needed:
                prompt.status = "awaiting_clarification"
                prompt.clarification_question = clarification_needed
                db.commit()
                _publish_ws_event(prompt_id, {
                    "status": "awaiting_clarification",
                    "clarification_question": clarification_needed,
                })
                return

            # 3. Fallback for any other execution errors
            _fail_prompt(db, prompt, f"Erreur de génération : {exc_str}", prompt_id)
            return


        # Capture generated code for audit log (never re-executed directly)
        generated_code = getattr(response, "last_code_executed", None)
        prompt.generated_code = generated_code

        # ── Extract result ────────────────────────────────────────────────────
        if chart_type == "text":
            # Just text output, no chart
            text_response = getattr(response, "value", response) if hasattr(response, "value") else str(response)
            if isinstance(text_response, pd.DataFrame):
                # Accidentally got a DF, convert to string
                text_response = text_response.to_markdown()
            elif isinstance(text_response, (dict, list)):
                text_response = str(text_response)
                
            chart_spec = None
            explanation_text = str(text_response)
            
            prompt.status = "completed"
            prompt.completed_at = datetime.now(tz=timezone.utc)
            prompt.explanation = explanation_text
            db.commit()

            _publish_ws_event(prompt_id, {
                "status": "completed",
                "chart": None,
                "explanation": explanation_text,
            })
            return

        # ── Extract result DataFrame ──────────────────────────────────────────
        result_df = _extract_dataframe(response)
        if result_df is None or len(result_df) == 0:
            _fail_prompt(
                db, prompt,
                "The analysis returned no data. Try rephrasing your request.",
                prompt_id,
            )
            return

        # ── Build ECharts spec ────────────────────────────────────────────────
        try:
            chart_spec = build_chart_spec(
                result_df, chart_type,
                auto_pivot=is_comparison,
                prompt_text=user_text,
            )
        except Exception as exc:
            logger.exception("Chart spec build failed for prompt %s", prompt_id)
            # Map common internal errors to friendly user-facing messages
            exc_str = str(exc)
            if "missing" in exc_str and "argument" in exc_str:
                user_msg = "Impossible de générer le graphique : les données retournées ne correspondent pas au format attendu. Essayez de préciser les colonnes dans votre requête (ex. 'par Vendeur', 'par Matériau')."
            elif "KeyError" in type(exc).__name__ or "key" in exc_str.lower():
                user_msg = "Une colonne mentionnée dans votre requête est introuvable dans les données. Vérifiez les noms de colonnes."
            elif "empty" in exc_str.lower() or "no data" in exc_str.lower():
                user_msg = "L'analyse n'a retourné aucune donnée exploitable pour construire ce graphique."
            else:
                user_msg = "La génération du graphique a échoué. Essayez de reformuler votre requête avec des colonnes plus précises."
            _fail_prompt(db, prompt, user_msg, prompt_id)
            return

        # ── Persist chart ─────────────────────────────────────────────────────
        chart = Chart(
            prompt_id=prompt_uuid,
            chart_type=chart_type,
            chart_spec=chart_spec,
        )
        db.add(chart)
        prompt.status = "completed"
        prompt.completed_at = datetime.now(tz=timezone.utc)

        # ── Optional explanation (opt-in via X-Explain header) ────────────────
        explanation_text = None
        if llm_config and llm_config.get("explain"):
            # Build a short data summary from the result DataFrame
            summary = result_df.to_string(max_rows=10, max_cols=6)
            explanation_text = generate_explanation(
                user_text, chart_type, summary, llm_config
            )
            prompt.explanation = explanation_text

        db.commit()

        _publish_ws_event(prompt_id, {
            "status": "completed",
            "chart": {
                "chart_id": str(chart.id),
                "chart_type": chart_type,
                "chart_spec": chart_spec,
            },
            "explanation": explanation_text,
        })

    except SoftTimeLimitExceeded:
        db.rollback()
        _fail_prompt(
            db, db.get(Prompt, uuid.UUID(prompt_id)),
            "La génération a pris trop de temps et a expiré. Réessayez ou posez une question plus simple.",
            prompt_id,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Unhandled error in process_prompt %s", prompt_id)
        try:
            p = db.get(Prompt, uuid.UUID(prompt_id))
            if p:
                _fail_prompt(db, p, "An unexpected error occurred. Please try again.", prompt_id)
        except Exception:
            pass
    finally:
        db.close()


def _extract_dataframe(response) -> Optional[pd.DataFrame]:
    """Extract a pandas DataFrame from a PandasAI v3 response object."""
    if response is None:
        return None

    # v3 response has a .value attribute
    value = getattr(response, "value", response)

    if isinstance(value, pd.DataFrame):
        return value

    # PandasAI may return a dict or list — try to coerce
    if isinstance(value, dict):
        try:
            return pd.DataFrame([value])
        except Exception:
            pass
    if isinstance(value, list) and len(value) > 0:
        try:
            return pd.DataFrame(value)
        except Exception:
            pass

    return None


def _fail_prompt(db, prompt: Optional[Prompt], message: str, prompt_id: str) -> None:
    """Mark a prompt as failed and publish WS event."""
    if prompt is None:
        return
    try:
        prompt.status = "failed"
        prompt.error_message = message
        db.commit()
    except Exception:
        db.rollback()
    _publish_ws_event(prompt_id, {
        "status": "failed",
        "message": message,
    })

# ── Background jobs ───────────────────────────────────────────────────────────

@celery_app.task(name="cleanup_expired_files")
def cleanup_expired_files() -> None:
    """
    Delete File records (and their on-disk storage) older than SESSION_TTL_DAYS.
    Runs as a periodic Celery beat task.

    NOTE: The previous task used SessionModel which no longer exists.
    The app now stores ownership on FileModel.owner_id (Keycloak user ID).
    TTL is measured from FileModel.created_at.
    """
    db = get_sync_session()
    try:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=settings.session_ttl_days)
        result = db.execute(select(FileModel).where(FileModel.created_at < cutoff))
        expired_files = result.scalars().all()

        for file_record in expired_files:
            # 1. Physical disk cleanup
            storage_dir = Path(settings.storage_path) / str(file_record.id)
            if storage_dir.exists() and storage_dir.is_dir():
                shutil.rmtree(storage_dir, ignore_errors=True)

            # 2. DB cleanup (cascade deletes prompts + charts)
            db.delete(file_record)

        if expired_files:
            db.commit()
            logger.info("Cleaned up %d expired files.", len(expired_files))

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to clean up expired files: %s", exc)
    finally:
        db.close()
