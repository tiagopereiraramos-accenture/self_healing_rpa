from __future__ import annotations

import bots._template.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker


class ExemploUC:
    """Use case de exemplo — copie e adapte para seu bot."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        with TransactionTracker(bot_name="template", action="exemplo") as tracker:
            await self._driver.goto("https://example.com")
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "msg": "Template executado"}
