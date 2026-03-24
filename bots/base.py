from __future__ import annotations

import importlib
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


def bot(
    name: str,
    description: str = "",
    url: str = "",
    auto_discover: bool = True,
):
    """Decorator que transforma uma classe simples em um bot completo.

    Auto-descobre use cases decorados com ``@use_case`` na pasta
    ``use_cases/`` do bot e registra como actions automaticamente.

    Uso minimo::

        @bot(name="meu_bot", description="Descricao", url="https://...")
        class MeuBot:
            pass  # actions auto-descobertas de use_cases/

    Uso com actions manuais (podem coexistir com auto-discovery)::

        @bot(name="meu_bot", description="Descricao", url="https://...")
        class MeuBot:
            @action("custom")
            async def _custom(self, **kwargs) -> dict:
                return {"status": "sucesso"}

    O decorator define ``BOT_CLASS`` automaticamente no modulo do bot.
    """

    def decorator(cls):
        # Herdar de BaseBot se nao herda
        if not issubclass(cls, BaseBot):
            # Criar nova classe que herda de BaseBot e da classe original
            cls = type(cls.__name__, (cls, BaseBot), dict(cls.__dict__))

        cls.name = name
        cls.description = description
        cls.url = url

        if auto_discover:
            _inject_auto_discovered_actions(cls, name)

        # Definir BOT_CLASS no modulo que chamou o decorator
        import sys
        caller_module = sys.modules.get(cls.__module__)
        if caller_module:
            caller_module.BOT_CLASS = cls  # type: ignore[attr-defined]

        return cls

    return decorator


def _inject_auto_discovered_actions(cls, bot_name: str) -> None:
    """Descobre use cases na pasta use_cases/ e injeta como actions."""
    import sys

    mod = sys.modules.get(cls.__module__)
    if not mod or not mod.__file__:
        return

    bot_dir = Path(mod.__file__).parent
    uc_dir = bot_dir / "use_cases"
    if not uc_dir.is_dir():
        return

    for uc_file in uc_dir.glob("*.py"):
        if uc_file.name.startswith("_"):
            continue

        module_path = f"bots.{bot_name}.use_cases.{uc_file.stem}"
        try:
            uc_mod = importlib.import_module(module_path)
        except Exception:
            continue

        # Procurar classes com _is_use_case (criadas por @use_case)
        for attr_name in dir(uc_mod):
            obj = getattr(uc_mod, attr_name)
            if isinstance(obj, type) and getattr(obj, "_is_use_case", False):
                action_name = obj._action_name

                # Evitar sobrescrever actions definidas manualmente
                existing = {
                    getattr(getattr(cls, a, None), "_action_name", None)
                    for a in dir(cls)
                    if hasattr(getattr(cls, a, None), "_action_name")
                }
                if action_name in existing:
                    continue

                # Criar metodo action para esta UC
                _make_action_method(cls, action_name, obj)


def _make_action_method(cls, action_name: str, uc_class: type) -> None:
    """Cria e injeta um metodo @action na classe do bot."""

    async def _action_method(self, **kwargs):
        return await uc_class(self._driver).execute(**kwargs)

    _action_method._action_name = action_name  # type: ignore[attr-defined]
    _action_method.__name__ = f"_auto_{action_name.replace('-', '_')}"
    _action_method.__qualname__ = f"{cls.__name__}.{_action_method.__name__}"

    setattr(cls, _action_method.__name__, _action_method)
