from __future__ import annotations

from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class OpenRouterProvider(ILLMProvider):
    """Calls OpenRouter using the openai-compatible SDK."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        logger.info(f"[LLM] 🔵 OpenRouter → {model}")
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        usage = response.usage
        content = response.choices[0].message.content or ""
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        # rough cost estimate (haiku pricing)
        cost = (tokens_in * 0.00000025) + (tokens_out * 0.00000125)
        return {
            "content": content.strip(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 8),
            "provider": "openrouter",
            "model": model,
        }
