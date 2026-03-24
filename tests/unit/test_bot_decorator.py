"""Testes unitarios para o @bot decorator (v3.2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from bots.base import BaseBot, action, bot


def _make_driver():
    driver = MagicMock()
    driver.get_healing_stats.return_value = {"healing_attempts": 0}
    return driver


def test_bot_decorator_sets_attributes():
    @bot(name="test_bot", description="Teste", url="https://test.com", auto_discover=False)
    class TestBot:
        pass

    assert TestBot.name == "test_bot"
    assert TestBot.description == "Teste"
    assert TestBot.url == "https://test.com"


def test_bot_decorator_inherits_basebot():
    @bot(name="test_bot", auto_discover=False)
    class TestBot:
        pass

    assert issubclass(TestBot, BaseBot)


def test_bot_decorator_with_manual_actions():
    @bot(name="test_bot", auto_discover=False)
    class TestBot:
        @action("hello")
        async def _hello(self, **kwargs):
            return {"status": "sucesso"}

    driver = _make_driver()
    instance = TestBot(driver)
    actions = instance.get_actions()
    assert "hello" in actions


def test_bot_decorator_preserves_existing_basebot():
    @bot(name="test_bot", auto_discover=False)
    class TestBot(BaseBot):
        pass

    assert issubclass(TestBot, BaseBot)
    assert TestBot.name == "test_bot"
