"""Testes unitarios para code_validator — validacao AST de codigo LLM."""
from __future__ import annotations

import pytest

from rpa_self_healing.domain.code_validator import UnsafeCodeError, validate_generated_code


class TestValidCode:
    def test_simple_click(self):
        validate_generated_code("await page.click('#btn')")

    def test_fill_action(self):
        validate_generated_code("await page.fill('#input', 'value')")

    def test_locator_chain(self):
        validate_generated_code("await page.locator('#form').locator('input').fill('x')")

    def test_multiline(self):
        code = "el = page.locator('#x')\nawait el.click()"
        validate_generated_code(code)


class TestBlockedImports:
    def test_import_os(self):
        with pytest.raises(UnsafeCodeError, match="Imports nao permitidos"):
            validate_generated_code("import os")

    def test_from_import(self):
        with pytest.raises(UnsafeCodeError, match="Imports nao permitidos"):
            validate_generated_code("from subprocess import run")


class TestBlockedBuiltins:
    def test_exec(self):
        with pytest.raises(UnsafeCodeError, match="builtin bloqueado.*exec"):
            validate_generated_code("exec('print(1)')")

    def test_eval(self):
        with pytest.raises(UnsafeCodeError, match="builtin bloqueado.*eval"):
            validate_generated_code("eval('1+1')")

    def test_dunder_import(self):
        with pytest.raises(UnsafeCodeError, match="builtin bloqueado.*__import__"):
            validate_generated_code("__import__('os').system('id')")

    def test_open(self):
        with pytest.raises(UnsafeCodeError, match="builtin bloqueado.*open"):
            validate_generated_code("open('/etc/passwd')")


class TestBlockedDunderAccess:
    def test_dunder_class(self):
        with pytest.raises(UnsafeCodeError, match="dunder"):
            validate_generated_code("page.__class__.__bases__")

    def test_dunder_globals(self):
        with pytest.raises(UnsafeCodeError, match="dunder"):
            validate_generated_code("page.__globals__")


class TestSyntaxError:
    def test_invalid_syntax(self):
        with pytest.raises(UnsafeCodeError, match="sintaxe invalida"):
            validate_generated_code("def (broken")
