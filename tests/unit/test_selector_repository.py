"""Testes unitarios para SelectorRepository."""
from __future__ import annotations

from pathlib import Path

from rpa_self_healing.infrastructure.git.selector_repository import SelectorRepository


def _write_selectors(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_update_selector_value(tmp_path: Path):
    file = _write_selectors(tmp_path / "selectors.py", 'CAMPO_USERNAME: str = "input#old"\n')
    repo = SelectorRepository()

    result = repo.update(file, "CAMPO_USERNAME", "input#new")

    assert result is True
    content = file.read_text(encoding="utf-8")
    assert 'input#new' in content
    assert 'input#old' not in content


def test_preserves_other_selectors(tmp_path: Path):
    file = _write_selectors(tmp_path / "selectors.py", (
        'CAMPO_USERNAME: str = "input#old"\n'
        'CAMPO_PASSWORD: str = "input#password"\n'
    ))
    repo = SelectorRepository()

    repo.update(file, "CAMPO_USERNAME", "input#new")

    content = file.read_text(encoding="utf-8")
    assert 'input#new' in content
    assert 'CAMPO_PASSWORD: str = "input#password"' in content


def test_adds_healing_date_comment(tmp_path: Path):
    file = _write_selectors(tmp_path / "selectors.py", 'BOTAO: str = "button#old"\n')
    repo = SelectorRepository()

    repo.update(file, "BOTAO", "button#new")

    content = file.read_text(encoding="utf-8")
    assert "# Healing:" in content


def test_updates_existing_healing_comment(tmp_path: Path):
    file = _write_selectors(
        tmp_path / "selectors.py",
        'BOTAO: str = "button#old"  # Healing: 2020-01-01\n',
    )
    repo = SelectorRepository()

    repo.update(file, "BOTAO", "button#new")

    content = file.read_text(encoding="utf-8")
    assert "2020-01-01" not in content
    assert "# Healing:" in content


def test_label_not_found_returns_false(tmp_path: Path):
    file = _write_selectors(tmp_path / "selectors.py", 'CAMPO_X: str = "input#x"\n')
    repo = SelectorRepository()

    result = repo.update(file, "INEXISTENTE", "input#new")

    assert result is False


def test_file_not_found_returns_false(tmp_path: Path):
    repo = SelectorRepository()
    result = repo.update(tmp_path / "inexistente.py", "LABEL", "new")
    assert result is False
