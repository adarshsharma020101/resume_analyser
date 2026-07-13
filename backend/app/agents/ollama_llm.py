"""
Ollama LLM adapter for CrewAI.
Wraps the local Ollama HTTP API into a CrewAI-compatible LLM.
No external calls — Ollama host must be local/Docker-internal.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from crewai import LLM
from app.core.config import get_settings

settings = get_settings()


def get_crewai_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLM:
    """
    Returns a CrewAI LLM configured to use local Ollama.
    Uses the ollama/ prefix which CrewAI/LiteLLM recognises for Ollama.
    """
    return LLM(
        model=f"ollama/{model or settings.OLLAMA_LLM_MODEL}",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temperature if temperature is not None else settings.OLLAMA_TEMPERATURE,
        max_tokens=max_tokens or settings.OLLAMA_MAX_TOKENS,
        timeout=settings.OLLAMA_REQUEST_TIMEOUT,
    )
