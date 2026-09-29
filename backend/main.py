"""
main.py — FastAPI application factory.
"""
from __future__ import annotations

import sys

# ── Python version guard ──────────────────────────────────────────────────────
# PandasAI 3.0.0 requires Python >=3.10 and <3.12.
# Fail loudly here rather than letting workers crash with cryptic import errors.
if sys.version_info < (3, 10) or sys.version_info >= (3, 12):
    import warnings
    warnings.warn(
        f"Unsupported Python {sys.version}. "
        "This application is tested on Python >=3.10, <3.12 "
        "(PandasAI 3.0.0 does not support Python 3.12+). "
        "Proceeding anyway — workers may fail.",
        RuntimeWarning,
        stacklevel=1,
    )

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.files import router as files_router
from backend.api.prompts import router as prompts_router
from backend.api.provider import router as provider_router
from backend.api.websocket import router as ws_router
from backend.api import admin
from backend.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Suppress PandasAI sandbox fallback warnings
logging.getLogger("pandasai").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events."""
    yield

app = FastAPI(
    title="Plateforme de Restitution Intelligente",
    description="CSV/Excel → Prompt → Interactive Chart",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(files_router)
app.include_router(prompts_router)
app.include_router(provider_router)
app.include_router(ws_router)

app.include_router(admin.router, prefix="/api/v1/platform-users", tags=["admin"])


# ── Global error handler — never expose raw stack traces ──────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again later.",
                "details": {},
            }
        },
    )


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "config": {
            "max_file_size_mb": settings.max_file_size_mb,
            "max_rows": settings.max_rows,
        }
    }

