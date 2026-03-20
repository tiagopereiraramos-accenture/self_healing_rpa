from __future__ import annotations

from bots.base import BaseBot, action

TJMS_URL = "https://esaj.tjms.jus.br/cpopg5/open.do"


class TJMSBot(BaseBot):
    name = "tjms"
    description = "Consulta processos no portal ESAJ/TJMS (Tribunal de Justica do MS)."
    url = TJMS_URL

    @action("consultar-processo")
    async def _consultar_processo(self, **kwargs) -> dict:
        from bots.tjms.use_cases.consultar_processo_uc import ConsultarProcessoUC

        return await ConsultarProcessoUC(self._driver).execute(**kwargs)


BOT_CLASS = TJMSBot
