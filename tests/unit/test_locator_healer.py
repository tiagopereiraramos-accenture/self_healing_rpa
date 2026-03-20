"""Testes unitarios para LocatorHealer (Nivel 1)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rpa_self_healing.application.locator_healer import LocatorHealer


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.heal_locator = AsyncMock(return_value={
        "content": "input[name='username']",
        "tokens_in": 200,
        "tokens_out": 10,
        "cost_usd": 0.00003,
        "confidence": 0.94,
        "model": "claude-haiku-4-5",
        "provider": "openrouter",
    })
    return llm


@pytest.fixture
def page_ctx() -> dict:
    return {
        "url": "https://example.com",
        "title": "Test",
        "elements": [{"tag": "input", "id": "username"}],
        "accessibility_tree": "",
    }


async def test_suggest_returns_selector(mock_llm, page_ctx):
    healer = LocatorHealer(mock_llm)
    result = await healer.suggest(
        broken_selector="input#broken",
        label="CAMPO_USERNAME",
        page_ctx=page_ctx,
        error="Timeout",
    )
    assert result["selector"] == "input[name='username']"
    assert result["tokens_in"] == 200
    assert result["cost_usd"] == 0.00003


async def test_suggest_empty_response_returns_none(mock_llm, page_ctx):
    mock_llm.heal_locator.return_value = {"content": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}
    healer = LocatorHealer(mock_llm)
    result = await healer.suggest(
        broken_selector="input#broken",
        label="CAMPO",
        page_ctx=page_ctx,
    )
    assert result["selector"] is None


async def test_suggest_calls_llm_with_correct_params(mock_llm, page_ctx):
    healer = LocatorHealer(mock_llm)
    await healer.suggest(
        broken_selector="input#old",
        label="CAMPO_X",
        page_ctx=page_ctx,
        error="Element not found",
    )
    mock_llm.heal_locator.assert_called_once_with(
        broken_selector="input#old",
        intent="executar CAMPO_X",
        context=page_ctx,
        error="Element not found",
    )
