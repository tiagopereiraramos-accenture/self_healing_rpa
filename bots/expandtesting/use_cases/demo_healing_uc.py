from __future__ import annotations

from loguru import logger

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"


class DemoHealingUC:
    """Demonstra Self-Healing ao vivo usando seletores propositalmente quebrados.

    Opcoes via CLI::

        uv run rpa-cli expandtesting demo-healing --nivel locator
        uv run rpa-cli expandtesting demo-healing --nivel flow
        uv run rpa-cli expandtesting demo-healing --nivel ambos
    """

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, nivel: str = "locator", **kwargs) -> dict:
        with TransactionTracker(
            bot_name="expandtesting",
            action="demo-healing",
            item_id=nivel,
        ) as tracker:
            await self._driver.goto(LOGIN_URL)

            if nivel in ("locator", "ambos"):
                logger.warning("[DEMO] Usando seletor QUEBRADO para username — healing N1 sera ativado")
                await self._driver.fill(
                    "CAMPO_USERNAME_QUEBRADO",
                    sel.CAMPO_USERNAME_QUEBRADO,
                    "practice",
                )
                logger.success("[DEMO] Nivel 1 (Locator) curou o seletor com sucesso!")

            if nivel in ("flow", "ambos"):
                logger.warning("[DEMO] Forcando Flow Healing (Nivel 2) para botao de login")
                await self._driver.click(
                    "BOTAO_LOGIN_QUEBRADO",
                    sel.BOTAO_LOGIN_QUEBRADO,
                    force_flow_heal=True,
                )
                logger.success("[DEMO] Nivel 2 (Flow) funcionou!")

            stats = self._driver.get_healing_stats()
            tracker.add_healing_stats(stats)
            return {
                "status": ActionStatus.SUCESSO,
                "nivel_demonstrado": nivel,
                "healing_stats": stats,
            }
