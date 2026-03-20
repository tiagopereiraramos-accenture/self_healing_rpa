"""Testes unitarios para LLMRouter."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from rpa_self_healing.infrastructure.llm.llm_router import LLMRouter


@pytest.fixture
def page_ctx() -> dict:
    return {
        "url": "https://example.com",
        "title": "Test",
        "elements": [{"tag": "input", "id": "username"}],
        "accessibility_tree": "",
    }


def test_router_raises_when_no_providers():
    router = LLMRouter.__new__(LLMRouter)
    router._providers = []

    # Simula construtor verificando chain vazia
    with pytest.raises(RuntimeError, match="Todos os providers LLM falharam"):
        import asyncio
        asyncio.get_event_loop().run_until_complete(router._call("s", "u", "m"))


async def test_fallback_on_provider_failure(monkeypatch, page_ctx):
    failing_provider = AsyncMock()
    failing_provider.complete = AsyncMock(side_effect=RuntimeError("API down"))

    working_provider = AsyncMock()
    working_provider.complete = AsyncMock(return_value={
        "content": "input#fixed",
        "tokens_in": 100,
        "tokens_out": 5,
        "cost_usd": 0.0,
        "provider": "ollama",
        "model": "llama3.3",
    })

    router = LLMRouter.__new__(LLMRouter)
    router._providers = [
        ("openrouter", failing_provider),
        ("ollama", working_provider),
    ]

    result = await router.heal_locator(
        broken_selector="input#broken",
        intent="test",
        context=page_ctx,
    )

    assert result["content"] == "input#fixed"
    failing_provider.complete.assert_called_once()
    working_provider.complete.assert_called_once()


async def test_all_providers_fail_raises(monkeypatch):
    provider1 = AsyncMock()
    provider1.complete = AsyncMock(side_effect=RuntimeError("fail1"))
    provider2 = AsyncMock()
    provider2.complete = AsyncMock(side_effect=RuntimeError("fail2"))

    router = LLMRouter.__new__(LLMRouter)
    router._providers = [("p1", provider1), ("p2", provider2)]

    with pytest.raises(RuntimeError, match="Todos os providers LLM falharam"):
        await router._call("system", "user", "model")
