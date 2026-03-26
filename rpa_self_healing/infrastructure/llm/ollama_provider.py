from __future__ import annotations

from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


_SSRF_BLOCKLIST = ("169.254.169.254", "metadata.google", "metadata.aws")


def _validate_ollama_url(url: str) -> str:
    """Valida URL do Ollama contra SSRF (SEC-6 / DAST-01)."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if any(blocked in hostname for blocked in _SSRF_BLOCKLIST):
        raise ValueError(f"URL bloqueada por politica SSRF: {url}")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Esquema invalido para Ollama URL: {parsed.scheme}")
    return url


class OllamaProvider(ILLMProvider):
    """Offline fallback — calls local Ollama instance via openai-compatible API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        base_url = _validate_ollama_url(settings.OLLAMA_BASE_URL)
        self._client = AsyncOpenAI(
            api_key="ollama",
            base_url=f"{base_url}/v1",
        )

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        model_id = model.split("/")[-1]
        logger.info(f"[LLM] 🔵 Ollama (offline) → {model_id}")
        response = await self._client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        usage = response.usage
        content = response.choices[0].message.content or ""
        return {
            "content": content.strip(),
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "cost_usd": 0.0,
            "provider": "ollama",
            "model": model_id,
        }
