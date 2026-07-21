"""
provider.py — LLM provider status endpoint.

GET /api/v1/provider-status
  Returns the active provider, model, and reachability status.
  The frontend ProviderStatusBadge polls this on mount.
"""
from fastapi import APIRouter

from backend.core.llm_client import get_provider_status

router = APIRouter(prefix="/api/v1", tags=["provider"])


@router.get("/provider-status")
async def provider_status():
    """
    Check if the configured LLM provider is reachable.

    Response shape:
    {
      "provider": "local" | "openai" | "anthropic" | "google",
      "model": "ollama/qwen2.5-coder:7b",
      "status": "online" | "offline" | "configured" | "unknown",
      "fallback": "google/gemini-3.5-flash" | null
    }
    """
    return get_provider_status()
