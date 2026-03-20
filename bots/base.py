from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver


def action(name: str | None = None):
    """Decorator que registra um metodo como action do bot.

    O nome da action e usado pelo CLI para roteamento::

        class MeuBot(BaseBot):
            @action("minha-action")
            async def _minha_action(self, **kwargs) -> dict:
                ...

    Se ``name`` nao for informado, o nome do metodo e usado
    (sem ``_`` inicial e com ``_`` trocado por ``-``).
    """

    def decorator(fn: Callable) -> Callable:
        fn._action_name = name or fn.__name__.lstrip("_").replace("_", "-")  # type: ignore[attr-defined]
        return fn

    return decorator


class BaseBot:
    """Classe base para todos os bots do framework.

    Subclasses DEVEM:
        1. Definir atributos de classe: ``name``, ``description``, ``url``
        2. Decorar actions com ``@action("nome-da-action")``
        3. Expor ``BOT_CLASS = MinhClasse`` no final do modulo

    Exemplo::

        class MeuBot(BaseBot):
            name = "meu_bot"
            description = "Descricao do bot"
            url = "https://exemplo.com"

            @action("consultar")
            async def _consultar(self, **kwargs) -> dict:
                from bots.meu_bot.use_cases.consultar_uc import ConsultarUC
                return await ConsultarUC(self._driver).execute(**kwargs)

        BOT_CLASS = MeuBot
    """

    name: str = ""
    description: str = ""
    url: str = ""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    def get_actions(self) -> dict[str, Callable]:
        """Auto-descobre actions decoradas com ``@action``.

        Pode ser sobrescrito manualmente se preferir o estilo antigo.
        """
        actions: dict[str, Callable] = {}
        for attr_name in dir(self):
            if attr_name.startswith("__"):
                continue
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "_action_name"):
                actions[method._action_name] = method
        return actions

    @property
    def selectors_file(self) -> Path:
        import sys

        mod = sys.modules.get(type(self).__module__)
        if mod and mod.__file__:
            return Path(mod.__file__).parent / "selectors.py"
        return Path("selectors.py")
