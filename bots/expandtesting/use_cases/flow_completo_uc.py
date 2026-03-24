from __future__ import annotations

from loguru import logger

from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.application.pipeline import Pipeline


class _VerificarSecureAreaUC:
    """Step intermediario: verifica se estamos na area segura apos login."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        import bots.expandtesting.selectors as sel

        if await self._driver.is_visible(sel.SECURE_AREA):
            text = await self._driver.get_text("SECURE_AREA", sel.SECURE_AREA)
            return {
                "status": ActionStatus.SUCESSO,
                "msg": f"Área segura confirmada: {text}",
                "secure_url": self._driver.page.url,
            }
        return {
            "status": ActionStatus.ERRO_LOGICO,
            "msg": "Não foi possível confirmar acesso à área segura",
        }


class _LogoutUC:
    """Step final: faz logout da area segura."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        import bots.expandtesting.selectors as sel

        await self._driver.click("BOTAO_LOGOUT", sel.BOTAO_LOGOUT)
        return {"status": ActionStatus.SUCESSO, "msg": "Logout realizado"}


async def _notificar_erro(step_name: str, result: dict, driver: PlaywrightDriver) -> None:
    """Handler de erro do pipeline — em producao, integraria com Slack/Teams/email."""
    logger.error(
        f"[NOTIFICACAO] Pipeline falhou no step '{step_name}': "
        f"{result.get('msg', 'erro desconhecido')}"
    )


class FlowCompletoUC:
    """Demonstra o Pipeline: login -> verificar area segura -> logout.

    Uso via CLI::

        uv run rpa-cli expandtesting flow-completo
        uv run rpa-cli expandtesting flow-completo --username practice --password SuperSecretPassword!
    """

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_uc import LoginUC

        return await Pipeline(self._driver, bot_name="expandtesting") \
            .step("login", LoginUC) \
            .step("verificar-secure", _VerificarSecureAreaUC) \
            .step("logout", _LogoutUC) \
            .on_error(_notificar_erro) \
            .run(**kwargs)
