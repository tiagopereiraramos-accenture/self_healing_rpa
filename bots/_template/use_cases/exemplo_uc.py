"""Exemplo de use case usando o estilo v3.2 (zero boilerplate).

Estilo v3.1 (classe + TransactionTracker manual) continua funcionando.
Veja login_uc.py do expandtesting para exemplo do estilo classico.
"""

from __future__ import annotations

from rpa_self_healing import use_case, OK

import bots._template.selectors as sel


@use_case("template", "exemplo")
async def exemplo(driver, **kwargs):
    await driver.goto("https://example.com")
    return OK(msg="Template executado")
