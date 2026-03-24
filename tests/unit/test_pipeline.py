"""Testes unitarios para Pipeline."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rpa_self_healing.application.pipeline import Pipeline
from rpa_self_healing.domain.entities import ActionStatus


def _make_driver():
    driver = MagicMock()
    driver.get_healing_stats.return_value = {"healing_attempts": 0}
    return driver


def _make_uc(status: ActionStatus = ActionStatus.SUCESSO, extra: dict | None = None):
    """Cria uma classe UC fake com resultado configuravel."""

    class FakeUC:
        def __init__(self, driver):
            self._driver = driver

        async def execute(self, **kwargs):
            result = {"status": status, "msg": f"fake {status}", **kwargs}
            if extra:
                result.update(extra)
            return result

    return FakeUC


def _make_failing_uc():
    """UC que lanca excecao."""

    class FailingUC:
        def __init__(self, driver):
            pass

        async def execute(self, **kwargs):
            raise RuntimeError("boom")

    return FailingUC


async def test_pipeline_all_steps_succeed():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("step1", _make_uc()) \
        .step("step2", _make_uc()) \
        .step("step3", _make_uc()) \
        .run()

    assert result["status"] == ActionStatus.SUCESSO
    assert result["steps_completed"] == 3
    assert result["steps_failed"] == 0
    assert result["steps_skipped"] == 0
    assert result["steps_total"] == 3
    assert len(result["results"]) == 3


async def test_pipeline_stops_on_error():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("ok", _make_uc()) \
        .step("fail", _make_uc(ActionStatus.ERRO_LOGICO)) \
        .step("never", _make_uc()) \
        .run()

    assert result["status"] == ActionStatus.ERRO_LOGICO
    assert result["steps_completed"] == 1
    assert result["steps_failed"] == 1
    assert len(result["results"]) == 2  # step3 nunca executou


async def test_pipeline_continue_on_error():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("ok", _make_uc()) \
        .step("fail", _make_uc(ActionStatus.ERRO_LOGICO)) \
        .step("also-ok", _make_uc()) \
        .on_error(AsyncMock(), stop=False) \
        .run()

    assert result["steps_completed"] == 2
    assert result["steps_failed"] == 1
    assert len(result["results"]) == 3  # todos executaram


async def test_pipeline_error_handler_called():
    driver = _make_driver()
    handler = AsyncMock()

    await Pipeline(driver, bot_name="test") \
        .step("fail", _make_uc(ActionStatus.ERRO_TECNICO)) \
        .on_error(handler) \
        .run()

    handler.assert_called_once()
    call_args = handler.call_args
    assert call_args[0][0] == "fail"  # step_name


async def test_pipeline_when_condition_skip():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("always", _make_uc()) \
        .step("skip-this", _make_uc(), when=lambda r: r.get("role") == "admin") \
        .step("also-always", _make_uc()) \
        .run()

    assert result["steps_completed"] == 2
    assert result["steps_skipped"] == 1
    assert result["results"][1]["skipped"] is True


async def test_pipeline_when_condition_run():
    driver = _make_driver()
    uc_with_role = _make_uc(extra={"role": "admin"})

    result = await Pipeline(driver, bot_name="test") \
        .step("login", uc_with_role) \
        .step("admin-only", _make_uc(), when=lambda r: r.get("role") == "admin") \
        .run()

    assert result["steps_completed"] == 2
    assert result["steps_skipped"] == 0


async def test_pipeline_forward_kwargs():
    driver = _make_driver()
    uc_with_token = _make_uc(extra={"token": "abc123", "session": "xyz"})

    result = await Pipeline(driver, bot_name="test") \
        .step("login", uc_with_token, forward=["token"]) \
        .step("use-token", _make_uc()) \
        .run()

    # O segundo step deve receber o token no kwargs
    last = result["results"][-1]
    assert last["token"] == "abc123"
    assert "session" not in last  # nao forwarded


async def test_pipeline_exception_becomes_erro_tecnico():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("crash", _make_failing_uc()) \
        .run()

    assert result["status"] == ActionStatus.ERRO_LOGICO
    assert result["steps_failed"] == 1
    assert "boom" in result["results"][0]["msg"]


async def test_pipeline_empty_runs_ok():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test").run()

    assert result["status"] == ActionStatus.SUCESSO
    assert result["steps_total"] == 0


async def test_pipeline_kwargs_passed_to_steps():
    driver = _make_driver()
    result = await Pipeline(driver, bot_name="test") \
        .step("step1", _make_uc()) \
        .run(username="user", password="pass")

    step_data = result["results"][0]
    assert step_data["username"] == "user"
    assert step_data["password"] == "pass"
