from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMProvider(ABC):
    """Contrato para providers de LLM (OpenRouter, Anthropic, Ollama)."""

    @abstractmethod
    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        """Retorna {"content": str, "tokens_in": int, "tokens_out": int, "cost_usd": float}."""


class IRepairCache(ABC):
    """Contrato para cache persistente de reparos."""

    @abstractmethod
    def get_locator(self, label: str, broken: str) -> str | None: ...

    @abstractmethod
    def set_locator(self, label: str, broken: str, healed: str, bot_name: str, confidence: float = 0.0) -> None: ...

    @abstractmethod
    def get_flow(self, step_name: str, bot_name: str) -> str | None: ...

    @abstractmethod
    def set_flow(self, step_name: str, bot_name: str, healed_code: str) -> None: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def clear(self, bot_name: str | None = None) -> None: ...
