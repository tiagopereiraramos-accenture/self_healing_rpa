from __future__ import annotations

from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class AnthropicProvider(ILLMProvider):
    """Calls Anthropic SDK directly — fallback when OpenRouter is unavailable."""

    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        # Strip provider prefix if present (e.g. "anthropic/claude-haiku-4-5")
        model_id = model.split("/")[-1]
        logger.info(f"[LLM] 🔵 Anthropic → {model_id}")
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        content = response.content[0].text if response.content else ""
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost = (tokens_in * 0.00000025) + (tokens_out * 0.00000125)
        return {
            "content": content.strip(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost, 8),
            "provider": "anthropic",
            "model": model_id,
        }
