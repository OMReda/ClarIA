"""
prompts.py — Prompt submission, status polling, and clarification endpoints.

POST /api/v1/files/{file_id}/prompts          — submit prompt (→ 202)
GET  /api/v1/prompts/{prompt_id}              — poll status + result
POST /api/v1/prompts/{prompt_id}/clarify      — answer clarification question
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_async_session
from backend.core.security import get_current_user, User
from backend.models.file import File as FileModel
from backend.models.prompt import Prompt
from backend.services.rate_limiter import check_and_increment
from backend.workers.tasks import process_prompt

router = APIRouter(prefix="/api/v1", tags=["prompts"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SubmitPromptBody(BaseModel):
    # max_length mirrors the frontend textarea maxLength; enforced server-side
    # so a direct API call cannot submit an arbitrarily long prompt.
    text: str = Field(min_length=1, max_length=2000)


class ClarifyBody(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)


class ChartPayload(BaseModel):
    chart_id: str
    chart_type: str
    chart_spec: Dict[str, Any]


class PromptResponse(BaseModel):
    prompt_id: str
    status: str
    chart: Optional[ChartPayload] = None
    clarification_question: Optional[str] = None
    error_message: Optional[str] = None


def _error(code: str, message: str, details: Optional[Dict] = None, http_status: int = 400):
    return HTTPException(
        status_code=http_status,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )





# ── POST /api/v1/files/{file_id}/prompts ─────────────────────────────────────

@router.post(
    "/files/{file_id}/prompts",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_prompt(
    file_id: str,
    body: SubmitPromptBody,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    

    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise _error("INVALID_FILE_ID", "file_id must be a valid UUID.")

    # ── Validate file ownership ────────────────────────────────────────────
    result = await db.execute(select(FileModel).where(FileModel.id == fid))
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise _error("FILE_NOT_FOUND", "File not found.", http_status=404)
    if str(file_record.owner_id) != str(user.sub):
        raise _error("FORBIDDEN", "This file does not belong to your session.", http_status=403)
    if file_record.status != "validated":
        raise _error(
            "FILE_NOT_READY",
            f"File is not ready for querying (status: {file_record.status}).",
        )

    if not body.text.strip():
        raise _error("EMPTY_PROMPT", "Prompt text cannot be empty.")

    # ── Rate limiting ────────────────────────────────────────────────────
    allowed, count = check_and_increment(user.sub)
    if not allowed:
        from backend.core.config import get_settings
        limit = get_settings().rate_limit_prompts_per_hour
        raise _error(
            "RATE_LIMIT_EXCEEDED",
            f"You have reached the limit of {limit} prompts per hour.",
            details={"limit": limit, "current_count": count},
            http_status=429,
        )

    # ── Read per-request LLM config from headers ────────────────────────────
    llm_config = {
        "provider": request.headers.get("x-llm-provider", ""),
        "model":    request.headers.get("x-llm-model", ""),
        "api_key":  request.headers.get("x-api-key", ""),
        "explain":  request.headers.get("x-explain", "").lower() == "true",
    }

    provider = llm_config["provider"].lower()
    api_key = llm_config["api_key"]
    if provider and provider != "local" and not api_key:
        provider_labels = {"openai": "OpenAI", "anthropic": "Anthropic", "google": "Google"}
        label = provider_labels.get(provider, provider.title())
        raise _error("MISSING_API_KEY", f"Veuillez entrer votre clé API {label} dans les paramètres pour continuer.", http_status=400)

    # ── Create prompt record ───────────────────────────────────────────────────
    prompt = Prompt(file_id=fid, raw_text=body.text.strip(), status="pending")
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)

    # ── Enqueue Celery task (pass llm_config as kwargs) ───────────────────────
    process_prompt.delay(str(prompt.id), llm_config=llm_config)

    return {"prompt_id": str(prompt.id), "status": "pending"}


# ── GET /api/v1/prompts/{prompt_id} ──────────────────────────────────────────

@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    

    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise _error("INVALID_PROMPT_ID", "prompt_id must be a valid UUID.")

    result = await db.execute(
        select(Prompt).where(Prompt.id == pid)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise _error("PROMPT_NOT_FOUND", "Prompt not found.", http_status=404)

    # Ownership: load file explicitly (avoid lazy relationship)
    file_result = await db.execute(select(FileModel).where(FileModel.id == prompt.file_id))
    file_record = file_result.scalar_one_or_none()
    if not file_record or str(file_record.owner_id) != str(user.sub):
        raise _error("FORBIDDEN", "This prompt does not belong to your session.", http_status=403)

    chart_payload = None
    if prompt.status == "completed" and prompt.chart:
        chart_payload = ChartPayload(
            chart_id=str(prompt.chart.id),
            chart_type=prompt.chart.chart_type,
            chart_spec=prompt.chart.chart_spec,
        )

    return PromptResponse(
        prompt_id=str(prompt.id),
        status=prompt.status,
        chart=chart_payload,
        clarification_question=prompt.clarification_question,
        error_message=prompt.error_message,
    )


# ── POST /api/v1/prompts/{prompt_id}/clarify ─────────────────────────────────

@router.post("/prompts/{prompt_id}/clarify", status_code=status.HTTP_202_ACCEPTED)
async def clarify_prompt(
    prompt_id: str,
    body: ClarifyBody,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    

    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise _error("INVALID_PROMPT_ID", "prompt_id must be a valid UUID.")

    result = await db.execute(select(Prompt).where(Prompt.id == pid))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise _error("PROMPT_NOT_FOUND", "Prompt not found.", http_status=404)

    # Ownership: load file explicitly (avoid lazy relationship)
    file_result = await db.execute(select(FileModel).where(FileModel.id == prompt.file_id))
    file_record = file_result.scalar_one_or_none()
    if not file_record or str(file_record.owner_id) != str(user.sub):
        raise _error("FORBIDDEN", "This prompt does not belong to your session.", http_status=403)

    if prompt.status != "awaiting_clarification":
        raise _error(
            "PROMPT_NOT_AWAITING_CLARIFICATION",
            f"Prompt is not awaiting clarification (status: {prompt.status}).",
        )
    if not body.answer.strip():
        raise _error("EMPTY_ANSWER", "Clarification answer cannot be empty.")

    prompt.clarification_answer = body.answer.strip()
    prompt.status = "pending"
    prompt.clarification_question = None
    await db.commit()

    # Forward per-request LLM config (same headers the original submit_prompt reads)
    llm_config = {
        "provider": request.headers.get("x-llm-provider", ""),
        "model":    request.headers.get("x-llm-model", ""),
        "api_key":  request.headers.get("x-api-key", ""),
        "explain":  request.headers.get("x-explain", "").lower() == "true",
    }
    process_prompt.delay(str(prompt.id), llm_config=llm_config)

    return {"prompt_id": str(prompt.id), "status": "pending"}
