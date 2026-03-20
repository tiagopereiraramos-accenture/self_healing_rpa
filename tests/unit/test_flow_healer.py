"""Testes unitarios para FlowHealer (Nivel 2)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rpa_self_healing.application.flow_healer import FlowHealer


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.heal_flow = AsyncMock(return_value={
        "content": "await page.fill(\"input[name='username']\", value)",
        "tokens_in": 400,
        "tokens_out": 20,
        "cost_usd": 0.0001,
        "model": "claude-sonnet-4-5",
        "provider": "openrouter",
    })
    return llm


@pytest.fixture
def page_ctx() -> dict:
    return {
        "url": "https://example.com",
        "title": "Test",
        "elements": [{"tag": "input", "id": "username"}],
    }


async def test_suggest_returns_code(mock_llm, page_ctx):
    healer = FlowHealer(mock_llm)
    result = await healer.suggest(
        step_name="fill_username",
        failed_code="await page.fill('input#broken', value)",
        error="Timeout",
        page_ctx=page_ctx,
    )
    assert result["code"] is not None
    assert "page.fill" in result["code"]
    assert result["tokens_in"] == 400


async def test_suggest_empty_code_returns_none(mock_llm, page_ctx):
    mock_llm.heal_flow.return_value = {"content": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0}
    healer = FlowHealer(mock_llm)
    result = await healer.suggest(
        step_name="step",
        failed_code="code",
        error="err",
        page_ctx=page_ctx,
    )
    assert result["code"] is None


async def test_suggest_calls_llm_with_correct_params(mock_llm, page_ctx):
    healer = FlowHealer(mock_llm)
    await healer.suggest(
        step_name="click_btn",
        failed_code="await page.click('#btn')",
        error="Not found",
        page_ctx=page_ctx,
    )
    mock_llm.heal_flow.assert_called_once_with(
        step_name="click_btn",
        failed_code="await page.click('#btn')",
        error="Not found",
        context=page_ctx,
    )
