from __future__ import annotations

from bots.base import BaseBot, action


class TemplateBot(BaseBot):
    name = "template"
    description = "Template — copie esta pasta para criar um novo bot"
    url = "https://example.com"

    @action("exemplo")
    async def _exemplo(self, **kwargs) -> dict:
        from bots._template.use_cases.exemplo_uc import ExemploUC

        return await ExemploUC(self._driver).execute(**kwargs)


# BOT_CLASS omitido intencionalmente — template nao aparece no CLI
