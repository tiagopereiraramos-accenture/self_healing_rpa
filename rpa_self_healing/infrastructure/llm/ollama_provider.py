from __future__ import annotations

from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class OllamaProvider(ILLMProvider):
    """Offline fallback — calls local Ollama instance via openai-compatible API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
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
