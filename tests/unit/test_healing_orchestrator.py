"""Testes unitarios para HealingOrchestrator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rpa_self_healing.application.healing_orchestrator import HealingOrchestrator
from rpa_self_healing.domain.entities import HealingLevel


@pytest.fixture
def page_ctx() -> dict:
    return {
        "url": "https://example.com",
        "title": "Test",
        "elements": [{"tag": "input", "id": "username"}],
        "accessibility_tree": "",
    }


@pytest.fixture
def orchestrator(tmp_path: Path) -> HealingOrchestrator:
    """Cria orchestrator com mocks injetados."""
    orch = HealingOrchestrator(bot_name="test_bot")
    # Inject mocks for cache, locator, flow
    orch._cache = MagicMock()
    orch._cache.get_locator = MagicMock(return_value=None)
    orch._cache.set_locator = MagicMock()
    orch._cache.get_flow = MagicMock(return_value=None)
    orch._cache.set_flow = MagicMock()

    orch._locator = MagicMock()
    orch._locator.suggest = AsyncMock(return_value={
        "selector": "input#healed",
        "tokens_in": 200,
        "tokens_out": 10,
        "cost_usd": 0.00003,
        "confidence": 0.92,
        "model": "haiku",
        "provider": "openrouter",
    })

    orch._flow = MagicMock()
    orch._flow.suggest = AsyncMock(return_value={
        "code": "await page.click('#btn')",
        "tokens_in": 400,
        "tokens_out": 20,
        "cost_usd": 0.0001,
        "model": "sonnet",
        "provider": "openrouter",
    })
    return orch


async def test_cache_hit_skips_llm(orchestrator, page_ctx):
    orchestrator._cache.get_locator.return_value = "input#cached"
    validate = AsyncMock(return_value=True)

    result = await orchestrator.heal(
        label="CAMPO",
        broken_selector="input#broken",
        page_ctx=page_ctx,
        error="Timeout",
        validate=validate,
    )

    assert result.success is True
    assert result.selector == "input#cached"
    assert result.from_cache is True
    orchestrator._locator.suggest.assert_not_called()


async def test_cache_hit_stale_falls_through_to_llm(orchestrator, page_ctx):
    orchestrator._cache.get_locator.return_value = "input#stale"
    call_count = 0

    async def validate(sel):
        nonlocal call_count
        call_count += 1
        if sel == "input#stale":
            return False  # cache stale
        return True  # LLM suggestion valid

    result = await orchestrator.heal(
        label="CAMPO",
        broken_selector="input#broken",
        page_ctx=page_ctx,
        error="Timeout",
        validate=validate,
    )

    assert result.success is True
    assert result.selector == "input#healed"
    assert result.from_cache is False
    orchestrator._locator.suggest.assert_called()


async def test_locator_healing_success(orchestrator, page_ctx):
    validate = AsyncMock(return_value=True)

    result = await orchestrator.heal(
        label="BOTAO",
        broken_selector="#old-btn",
        page_ctx=page_ctx,
        error="Element not found",
        validate=validate,
    )

    assert result.success is True
    assert result.selector == "input#healed"
    assert result.level == HealingLevel.LOCATOR
    orchestrator._cache.set_locator.assert_called_once()


async def test_locator_failure_escalates_to_flow(orchestrator, page_ctx):
    orchestrator._locator.suggest = AsyncMock(return_value={
        "selector": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
    })
    validate = AsyncMock(return_value=False)

    result = await orchestrator.heal(
        label="CAMPO",
        broken_selector="#broken",
        page_ctx=page_ctx,
        error="Timeout",
        validate=validate,
        failed_code="await page.click('#broken')",
    )

    assert result.success is True
    assert result.code == "await page.click('#btn')"
    assert result.level == HealingLevel.FLOW
    orchestrator._flow.suggest.assert_called_once()


async def test_flow_healing_failure(orchestrator, page_ctx):
    orchestrator._locator.suggest = AsyncMock(return_value={
        "selector": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
    })
    orchestrator._flow.suggest = AsyncMock(return_value={
        "code": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
    })
    validate = AsyncMock(return_value=False)

    result = await orchestrator.heal(
        label="CAMPO",
        broken_selector="#broken",
        page_ctx=page_ctx,
        error="Timeout",
        validate=validate,
    )

    assert result.success is False


async def test_stats_tracking(orchestrator, page_ctx):
    validate = AsyncMock(return_value=True)

    await orchestrator.heal(
        label="L1",
        broken_selector="#old",
        page_ctx=page_ctx,
        error="err",
        validate=validate,
    )

    stats = orchestrator.stats
    assert stats.healing_attempts == 1
    assert stats.healing_successes == 1
    assert stats.level1_used == 1
    assert stats.total_tokens_in == 200
    assert stats.total_cost_usd == 0.00003


async def test_heal_flow_direct(orchestrator, page_ctx):
    result = await orchestrator.heal_flow_direct(
        label="STEP",
        failed_code="await page.click('#x')",
        error="Timeout",
        page_ctx=page_ctx,
    )

    assert result.success is True
    assert result.code is not None
    assert result.level == HealingLevel.FLOW
    assert orchestrator.stats.level2_used == 1


async def test_flow_cache_hit(orchestrator, page_ctx):
    orchestrator._locator.suggest = AsyncMock(return_value={
        "selector": None, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
    })
    orchestrator._cache.get_flow.return_value = "await page.click('#cached')"
    validate = AsyncMock(return_value=False)

    result = await orchestrator.heal(
        label="STEP",
        broken_selector="#broken",
        page_ctx=page_ctx,
        error="err",
        validate=validate,
    )

    assert result.success is True
    assert result.code == "await page.click('#cached')"
    assert result.from_cache is True
    orchestrator._flow.suggest.assert_not_called()
