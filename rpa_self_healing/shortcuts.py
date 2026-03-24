"""Atalhos para simplificar o desenvolvimento de bots (v3.2).

Uso::

    from rpa_self_healing import use_case, OK, FAIL

    @use_case("meu_bot", "minha-action")
    async def minha_action(driver, **kwargs):
        await driver.goto("https://exemplo.com")
        return OK(msg="Feito!")

O decorator ``@use_case`` cria automaticamente uma classe compativel
com o Pipeline e o sistema de roteamento, incluindo TransactionTracker
e coleta de healing stats — zero boilerplate para o desenvolvedor.
"""

from __future__ import annotations

from functools import wraps
from typing import Any

from rpa_self_healing.domain.entities import ActionStatus


# ── OK / FAIL helpers ─────────────────────────────────────────────────────────


def OK(**data: Any) -> dict[str, Any]:
    """Retorna resultado de sucesso padrao.

    Uso::

        return OK(url="https://...", token="abc123")
        # => {"status": ActionStatus.SUCESSO, "url": "https://...", "token": "abc123"}
    """
    return {"status": ActionStatus.SUCESSO, **data}


def FAIL(msg: str, **data: Any) -> dict[str, Any]:
    """Retorna resultado de erro logico padrao.

    Uso::

        return FAIL("Credenciais invalidas", tentativas=3)
        # => {"status": ActionStatus.ERRO_LOGICO, "msg": "Credenciais invalidas", "tentativas": 3}
    """
    return {"status": ActionStatus.ERRO_LOGICO, "msg": msg, **data}


# ── @use_case decorator ──────────────────────────────────────────────────────


def use_case(bot_name: str, action_name: str):
    """Transforma uma funcao async em um use case completo.

    O decorator cria uma classe wrapper compativel com Pipeline e
    roteamento, adicionando automaticamente:

    - TransactionTracker (abertura, fechamento, healing stats)
    - Coleta de healing stats via ``driver.get_healing_stats()``
    - Tratamento de excecoes como ERRO_TECNICO

    A funcao decorada recebe ``driver`` como primeiro argumento,
    seguido dos kwargs da action.

    Parametros extras disponiveis na funcao decorada:

    - ``tracker``: instancia de TransactionTracker (para ``tracker.fail()``,
      ``tracker.add_data()``, ``tracker.item_id = ...``)

    Uso::

        @use_case("meu_bot", "login")
        async def login(driver, username="", password="", **kwargs):
            await driver.goto("https://...")
            await driver.fill("CAMPO", sel.CAMPO, username)
            return OK(url=driver.page.url)

    Compatibilidade com Pipeline::

        result = await Pipeline(driver, bot_name="meu_bot") \\
            .step("login", login) \\
            .run(username="user")
    """

    def decorator(fn):
        @wraps(fn)
        async def _execute(self, **kwargs):
            from rpa_self_healing.infrastructure.logging.rpa_logger import (
                TransactionTracker,
            )

            with TransactionTracker(
                bot_name=bot_name, action=action_name
            ) as tracker:
                kwargs["tracker"] = tracker
                result = await fn(self._driver, **kwargs)
                if hasattr(self._driver, "get_healing_stats"):
                    tracker.add_healing_stats(self._driver.get_healing_stats())
                return result

        class _UCWrapper:
            __qualname__ = fn.__qualname__
            __name__ = fn.__name__
            __doc__ = fn.__doc__

            def __init__(self, driver):
                self._driver = driver

            execute = _execute

        # Marcadores para o framework reconhecer
        _UCWrapper._is_use_case = True  # type: ignore[attr-defined]
        _UCWrapper._bot_name = bot_name  # type: ignore[attr-defined]
        _UCWrapper._action_name = action_name  # type: ignore[attr-defined]
        _UCWrapper.__name__ = fn.__name__  # type: ignore[assignment]
        _UCWrapper.__qualname__ = fn.__qualname__  # type: ignore[assignment]

        return _UCWrapper

    return decorator
