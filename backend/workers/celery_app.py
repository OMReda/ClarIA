from __future__ import annotations

import logging
import warnings

logging.getLogger("pandasai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "plateforme",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.workers.tasks"],
)

celery_app.conf.update(
    task_always_eager=settings.celery_always_eager,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Hard timeout: task killed after this many seconds
    task_time_limit=180,
    # Soft timeout: SoftTimeLimitExceeded raised, allows graceful cleanup
    task_soft_time_limit=150,
)

