"""Testes unitarios para o comando scaffold (v3.2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def test_scaffold_creates_bot_structure(tmp_path, monkeypatch):
    """Verifica que scaffold cria toda a estrutura correta."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bots").mkdir()

    # Importar e chamar diretamente a funcao
    from cli import _scaffold_bot

    _scaffold_bot("meu_bot", {"url": "https://test.com", "actions": "login,coleta"})

    bot_dir = tmp_path / "bots" / "meu_bot"
    assert bot_dir.is_dir()
    assert (bot_dir / "__init__.py").exists()
    assert (bot_dir / "selectors.py").exists()
    assert (bot_dir / "use_cases" / "__init__.py").exists()
    assert (bot_dir / "use_cases" / "login_uc.py").exists()
    assert (bot_dir / "use_cases" / "coleta_uc.py").exists()

    # Verificar conteudo do __init__.py
    init_content = (bot_dir / "__init__.py").read_text(encoding="utf-8")
    assert "@bot(" in init_content
    assert 'name="meu_bot"' in init_content
    assert "MeuBotBot" in init_content  # class name gerado

    # Verificar conteudo do use case
    login_content = (bot_dir / "use_cases" / "login_uc.py").read_text(encoding="utf-8")
    assert "@use_case(" in login_content
    assert '"meu_bot"' in login_content
    assert '"login"' in login_content
    assert "OK(" in login_content


def test_scaffold_default_action(tmp_path, monkeypatch):
    """Sem --actions, cria action 'exemplo'."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bots").mkdir()

    from cli import _scaffold_bot

    _scaffold_bot("simple", {})

    assert (tmp_path / "bots" / "simple" / "use_cases" / "exemplo_uc.py").exists()


def test_scaffold_fails_if_exists(tmp_path, monkeypatch):
    """Scaffold nao sobrescreve pasta existente."""
    monkeypatch.chdir(tmp_path)
    bot_dir = tmp_path / "bots" / "existing"
    bot_dir.mkdir(parents=True)

    from cli import _scaffold_bot

    with pytest.raises(SystemExit):
        _scaffold_bot("existing", {})
