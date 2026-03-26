"""Validacao AST de codigo gerado por LLM antes de execucao ou persistencia.

Bloqueia construcoes perigosas como imports, acesso a atributos nao autorizados,
chamadas a builtins perigosos (exec, eval, open, etc.) e acesso a dunder attributes.
"""
from __future__ import annotations

import ast

_ALLOWED_PAGE_ATTRS = frozenset({
    "click", "fill", "wait_for_selector", "locator", "goto",
    "inner_text", "is_visible", "count", "text_content",
    "input_value", "get_attribute", "check", "uncheck",
    "select_option", "hover", "focus", "press", "type",
    "wait_for_timeout", "query_selector", "query_selector_all",
    "frame_locator", "nth", "first", "last", "filter",
})

_BLOCKED_BUILTINS = frozenset({
    "exec", "eval", "compile", "__import__", "open",
    "getattr", "setattr", "delattr", "globals", "locals",
    "vars", "dir", "breakpoint", "input", "exit", "quit",
    "memoryview", "type", "super",
})


class UnsafeCodeError(ValueError):
    """Codigo gerado pelo LLM contem construcoes nao permitidas."""


def validate_generated_code(code: str) -> None:
    """Valida via AST que o codigo nao contem construcoes perigosas.

    Raises:
        UnsafeCodeError: se o codigo contiver imports, chamadas bloqueadas,
            acesso a dunder attributes ou builtins perigosos.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Codigo com sintaxe invalida: {exc}") from exc

    for node in ast.walk(tree):
        # Bloquear imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise UnsafeCodeError(
                "Imports nao permitidos em codigo gerado por LLM"
            )

        # Bloquear acesso a dunder attributes (__class__, __globals__, etc.)
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise UnsafeCodeError(
                f"Acesso a atributo dunder nao permitido: '{node.attr}'"
            )

        # Bloquear chamadas a builtins perigosos
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BLOCKED_BUILTINS:
                raise UnsafeCodeError(
                    f"Chamada a builtin bloqueado: '{func.id}'"
                )
