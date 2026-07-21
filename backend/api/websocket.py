"""
websocket.py — WebSocket endpoint for real-time prompt status updates.

GET /ws/prompts/{prompt_id}

Security: validates Authorization Bearer token ownership before accepting the connection.
Uses Redis pub/sub to receive events published by the Celery worker.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from backend.core.security import decode_and_validate_token
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.config import get_settings
from backend.core.database import AsyncSessionLocal
from backend.models.file import File as FileModel
from backend.models.prompt import Prompt

router = APIRouter(tags=["websocket"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.websocket("/ws/prompts/{prompt_id}")
async def ws_prompt_status(websocket: WebSocket, prompt_id: str):
    await websocket.accept()

    # ── Validate prompt_id format ─────────────────────────────────────────────
    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        await websocket.close(code=4000, reason="Invalid prompt_id")
        return

    # ── Read Token from query param or header ─────────────────────────────────
    token_raw = websocket.query_params.get("token")
    if not token_raw:
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_raw = auth_header.split(" ", 1)[1]

    if not token_raw:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        user = decode_and_validate_token(token_raw)
        user_sub = user.sub
    except HTTPException as e:
        await websocket.close(code=4001, reason=str(e.detail))
        return

    # ── Ownership check ───────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prompt).where(Prompt.id == pid))
        prompt = result.scalar_one_or_none()

        if prompt is None:
            await websocket.close(code=4004, reason="Prompt not found")
            return

        # Load file to check session ownership
        file_result = await db.execute(
            select(FileModel).where(FileModel.id == prompt.file_id)
        )
        file_record = file_result.scalar_one_or_none()

        if file_record is None or str(file_record.owner_id) != user_sub:
            await websocket.close(code=4003, reason="Forbidden")
            return

        # If already completed/failed, send final state immediately
        current_status = prompt.status

    if current_status in ("completed", "failed"):
        # Client connected after completion — re-fetch with chart eagerly loaded
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Prompt)
                .where(Prompt.id == pid)
                .options(selectinload(Prompt.chart))
            )
            prompt = result.scalar_one_or_none()
            if prompt and prompt.chart:
                await websocket.send_json({
                    "status": "completed",
                    "chart": {
                        "chart_id": str(prompt.chart.id),
                        "chart_type": prompt.chart.chart_type,
                        "chart_spec": prompt.chart.chart_spec,
                    },
                })
            elif prompt:
                await websocket.send_json({
                    "status": prompt.status,
                    "message": prompt.error_message or "",
                })
        await websocket.close()
        return

    # ── Subscribe to Redis pub/sub channel ───────────────────────────────────
    channel = f"ws:prompt:{prompt_id}"
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
    except Exception as exc:
        logger.error("Redis connection failed for ws:%s - %s", prompt_id, exc)
        await websocket.send_json({"status": "failed", "message": "Real-time updates unavailable (internal error)."})
        await websocket.close()
        return

    try:
        # Send initial ack
        await websocket.send_json({"status": current_status, "message": "Connected — waiting for result…"})

        async def listen():
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                try:
                    await websocket.send_json(data)
                except WebSocketDisconnect:
                    break

                # Terminal states — close connection
                if data.get("status") in ("completed", "failed"):
                    await websocket.close()
                    break

        # Timeout after 5 minutes to avoid zombie connections
        try:
            await asyncio.wait_for(listen(), timeout=300)
        except asyncio.TimeoutError:
            await websocket.send_json({"status": "failed", "message": "Connection timed out."})
            await websocket.close()

    except WebSocketDisconnect:
        logger.debug("Client disconnected from ws:%s", prompt_id)
    finally:
        await pubsub.unsubscribe(channel)
        # Installed redis-py version is 4.6.0, which doesn't expose aclose() directly on this client type
        import inspect
        if hasattr(r, "aclose"):
            await r.aclose()
        else:
            close_result = r.close()
            if inspect.isawaitable(close_result):
                await close_result
