"""Testes unitarios para OK, FAIL e @use_case (v3.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.shortcuts import FAIL, OK, use_case


# ── OK / FAIL ─────────────────────────────────────────────────────────────────


def test_ok_returns_sucesso():
    result = OK()
    assert result["status"] == ActionStatus.SUCESSO


def test_ok_with_data():
    result = OK(url="https://...", token="abc")
    assert result["status"] == ActionStatus.SUCESSO
    assert result["url"] == "https://..."
    assert result["token"] == "abc"


def test_fail_returns_erro_logico():
    result = FAIL("deu ruim")
    assert result["status"] == ActionStatus.ERRO_LOGICO
    assert result["msg"] == "deu ruim"


def test_fail_with_extra_data():
    result = FAIL("credenciais", tentativas=3)
    assert result["status"] == ActionStatus.ERRO_LOGICO
    assert result["msg"] == "credenciais"
    assert result["tentativas"] == 3


# ── @use_case ─────────────────────────────────────────────────────────────────


def _make_driver():
    driver = MagicMock()
    driver.get_healing_stats.return_value = {"healing_attempts": 0}
    return driver


async def test_use_case_creates_class():
    @use_case("test_bot", "my-action")
    async def my_action(driver, **kwargs):
        return OK(msg="done")

    # Retorna uma classe, nao uma funcao
    assert isinstance(my_action, type)
    assert my_action._is_use_case is True
    assert my_action._bot_name == "test_bot"
    assert my_action._action_name == "my-action"


async def test_use_case_execute():
    @use_case("test_bot", "greet")
    async def greet(driver, name="world", **kwargs):
        return OK(greeting=f"Hello {name}")

    driver = _make_driver()
    uc = greet(driver)
    result = await uc.execute(name="Junior")

    assert result["status"] == ActionStatus.SUCESSO
    assert result["greeting"] == "Hello Junior"


async def test_use_case_injects_tracker():
    tracker_ref = {}

    @use_case("test_bot", "track-me")
    async def track_me(driver, tracker=None, **kwargs):
        tracker_ref["tracker"] = tracker
        return OK()

    driver = _make_driver()
    await track_me(driver).execute()

    assert tracker_ref["tracker"] is not None


async def test_use_case_collects_healing_stats():
    @use_case("test_bot", "heal-check")
    async def heal_check(driver, **kwargs):
        return OK()

    driver = _make_driver()
    await heal_check(driver).execute()

    driver.get_healing_stats.assert_called_once()


async def test_use_case_fail_result():
    @use_case("test_bot", "fail-action")
    async def fail_action(driver, **kwargs):
        return FAIL("something broke")

    driver = _make_driver()
    result = await fail_action(driver).execute()

    assert result["status"] == ActionStatus.ERRO_LOGICO
    assert result["msg"] == "something broke"


async def test_use_case_works_with_pipeline():
    """Garante que @use_case e compativel com Pipeline."""
    from rpa_self_healing.application.pipeline import Pipeline

    @use_case("test_bot", "step-a")
    async def step_a(driver, **kwargs):
        return OK(value=42)

    @use_case("test_bot", "step-b")
    async def step_b(driver, **kwargs):
        return OK(received=kwargs.get("value"))

    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("a", step_a, forward=["value"]) \
        .step("b", step_b) \
        .run()

    assert result["status"] == ActionStatus.SUCESSO
    assert result["steps_completed"] == 2
    assert result["results"][1]["received"] == 42


async def test_use_case_kwargs_forwarded():
    @use_case("test_bot", "echo")
    async def echo(driver, x="", y="", **kwargs):
        return OK(x=x, y=y)

    driver = _make_driver()
    result = await echo(driver).execute(x="hello", y="world")

    assert result["x"] == "hello"
    assert result["y"] == "world"
