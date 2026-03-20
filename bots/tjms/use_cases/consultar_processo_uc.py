from __future__ import annotations

import bots.tjms.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

TJMS_URL = "https://esaj.tjms.jus.br/cpopg5/open.do"


class ConsultarProcessoUC:
    """Use case: consulta processo por numero no portal ESAJ/TJMS."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(
        self,
        numero: str = "",
        **kwargs,
    ) -> dict:
        with TransactionTracker(
            bot_name="tjms",
            action="consultar-processo",
            item_id=numero,
        ) as tracker:
            await self._driver.goto(TJMS_URL)

            await self._driver.fill(
                "CAMPO_NUMERO_PROCESSO",
                sel.CAMPO_NUMERO_PROCESSO,
                numero,
            )
            await self._driver.click("BOTAO_PESQUISAR", sel.BOTAO_PESQUISAR)

            if await self._driver.is_visible(sel.MENSAGEM_ERRO):
                msg = await self._driver.get_text("MENSAGEM_ERRO", sel.MENSAGEM_ERRO)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}

            titulo = await self._driver.get_text("RESULTADO_TITULO", sel.RESULTADO_TITULO)
            tracker.add_data("titulo", titulo)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "numero": numero, "titulo": titulo}
