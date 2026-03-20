from __future__ import annotations

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"


class LoginInvalidoUC:
    """Use case: login com credenciais invalidas (teste negativo)."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(
        self,
        username: str = "usuario_errado",
        password: str = "senha_errada",
        **kwargs,
    ) -> dict:
        with TransactionTracker(
            bot_name="expandtesting",
            action="login-invalido",
            item_id=username,
        ) as tracker:
            await self._driver.goto(LOGIN_URL)
            await self._driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
            await self._driver.fill("CAMPO_PASSWORD", sel.CAMPO_PASSWORD, password)
            await self._driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

            if await self._driver.is_visible(sel.FLASH_ERRO):
                msg = await self._driver.get_text("FLASH_MSG", sel.FLASH_MSG)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg, "esperado": True}

            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
