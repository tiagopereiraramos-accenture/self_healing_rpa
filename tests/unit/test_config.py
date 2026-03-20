"""Testes unitarios para rpa_self_healing.config.Settings."""
from __future__ import annotations

from rpa_self_healing.config import Settings


def test_settings_reads_openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-123")
    s = Settings()
    assert s.OPENROUTER_API_KEY == "sk-or-test-123"


def test_settings_default_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    s = Settings()
    assert s.LLM_PROVIDER == "openrouter"


def test_settings_bool_parsing(monkeypatch):
    monkeypatch.setenv("GIT_AUTO_COMMIT", "true")
    monkeypatch.setenv("GIT_AUTO_PUSH", "false")
    s = Settings()
    assert s.GIT_AUTO_COMMIT is True
    assert s.GIT_AUTO_PUSH is False


def test_settings_int_parsing(monkeypatch):
    monkeypatch.setenv("LLM_MAX_HEALING_ATTEMPTS", "5")
    s = Settings()
    assert s.LLM_MAX_HEALING_ATTEMPTS == 5


def test_settings_new_instance_reflects_env_changes(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    s = Settings()
    assert s.LLM_PROVIDER == "anthropic"

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    s2 = Settings()
    assert s2.LLM_PROVIDER == "ollama"
