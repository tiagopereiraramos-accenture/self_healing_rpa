from __future__ import annotations

from bots.base import BaseBot, action

LOGIN_URL = "https://practice.expandtesting.com/login"


class ExpandTestingBot(BaseBot):
    name = "expandtesting"
    description = "Bot de demo — login em practice.expandtesting.com. Demonstra Self-Healing ao vivo."
    url = LOGIN_URL

    @action("login")
    async def _login(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_uc import LoginUC

        return await LoginUC(self._driver).execute(**kwargs)

    @action("login-invalido")
    async def _login_invalido(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_invalido_uc import LoginInvalidoUC

        return await LoginInvalidoUC(self._driver).execute(**kwargs)

    @action("demo-healing")
    async def _demo_healing(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.demo_healing_uc import DemoHealingUC

        return await DemoHealingUC(self._driver).execute(**kwargs)


BOT_CLASS = ExpandTestingBot
