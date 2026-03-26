from __future__ import annotations

import os

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"


class LoginUC:
    """Use case: login com credenciais validas no expandtesting.com."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(
        self,
        username: str = "",
        password: str = "",
        **kwargs,
    ) -> dict:
        username = username or os.getenv("BOT_USERNAME", "")
        password = password or os.getenv("BOT_PASSWORD", "")
        if not username or not password:
            raise EnvironmentError(
                "Credenciais nao configuradas. Defina BOT_USERNAME e BOT_PASSWORD "
                "no ambiente ou passe como argumento."
            )
        with TransactionTracker(
            bot_name="expandtesting",
            action="login",
            item_id=username,
        ) as tracker:
            await self._driver.goto(LOGIN_URL)
            await self._driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
            await self._driver.fill("CAMPO_PASSWORD", sel.CAMPO_PASSWORD, password)
            await self._driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

            # Erro logico (credenciais invalidas)
            if await self._driver.is_visible(sel.FLASH_ERRO):
                msg = await self._driver.get_text("FLASH_MSG", sel.FLASH_MSG)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}

            # Sucesso
            tracker.add_data("redirect_url", self._driver.page.url)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
