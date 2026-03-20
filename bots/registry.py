from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from loguru import logger

_BOTS_DIR = Path(__file__).parent
_registry: dict[str, Any] | None = None


def _discover() -> dict[str, Any]:
    bots: dict[str, Any] = {}
    for bot_dir in _BOTS_DIR.iterdir():
        if not bot_dir.is_dir() or bot_dir.name.startswith("_") or bot_dir.name == "__pycache__":
            continue
        init_file = bot_dir / "__init__.py"
        if not init_file.exists():
            continue
        module_name = f"bots.{bot_dir.name}"
        try:
            mod = importlib.import_module(module_name)
            bot_class = getattr(mod, "BOT_CLASS", None)
            if bot_class is None:
                continue
            bots[bot_dir.name] = bot_class
            logger.debug(f"[Registry] Discovered bot: {bot_dir.name} → {bot_class.__name__}")
        except Exception as exc:
            logger.warning(f"[Registry] Falha ao carregar bot '{bot_dir.name}': {exc}")
    return bots


def get_registry() -> dict[str, Any]:
    global _registry
    if _registry is None:
        _registry = _discover()
    return _registry


def get_bot_class(bot_id: str) -> Any:
    registry = get_registry()
    if bot_id not in registry:
        raise KeyError(f"Bot '{bot_id}' não encontrado. Disponíveis: {list(registry.keys())}")
    return registry[bot_id]
