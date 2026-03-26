from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import IRepairCache

_COST_PER_TOKEN = 0.00000025


class RepairCache(IRepairCache):
    """Cache persistente (JSON) de seletores e fluxos curados.

    Regra de ouro (skill-8): o cache DEVE ser consultado ANTES de
    qualquer chamada ao LLM. Chamar LLM sem checar o cache e PROIBIDO.

    Use ``RepairCache.get_instance()`` para obter o singleton.
    Em testes, use ``RepairCache.reset_instance()`` para limpar.
    """

    _instance: RepairCache | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, cache_file: Path | None = None) -> None:
        self._file = cache_file or settings.CACHE_FILE
        self._data: dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> RepairCache:
        """Retorna a instancia singleton do cache (thread-safe)."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Limpa o singleton (para uso em testes)."""
        with cls._lock:
            cls._instance = None

    # ── persistencia ─────────────────────────────────────────────────────────

    def _load(self) -> dict[str, Any]:
        if self._file.exists():
            try:
                return json.loads(self._file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.debug(f"[CACHE] Falha ao carregar cache: {type(exc).__name__}: {exc}")
        return {"locators": {}, "flows": {}}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── locator cache ────────────────────────────────────────────────────────

    def _locator_key(self, label: str, broken: str) -> str:
        return f"{label}|{broken}"

    def get_locator(self, label: str, broken: str) -> str | None:
        key = self._locator_key(label, broken)
        entry = self._data["locators"].get(key)
        if entry:
            entry["hit_count"] = entry.get("hit_count", 0) + 1
            entry["last_hit"] = datetime.now(timezone.utc).isoformat()
            self._save()
            savings = entry.get("hit_count", 1) * _COST_PER_TOKEN * 260
            logger.info(
                f"[CACHE] HIT  '{label}' -> '{entry['healed']}' "
                f"(hit #{entry['hit_count']} | economia: ${savings:.6f})"
            )
            return entry["healed"]
        logger.info(f"[CACHE] MISS '{label}' — chamando LLM...")
        return None

    def set_locator(
        self,
        label: str,
        broken: str,
        healed: str,
        bot_name: str,
        confidence: float = 0.0,
    ) -> None:
        key = self._locator_key(label, broken)
        self._data["locators"][key] = {
            "healed": healed,
            "bot": bot_name,
            "healed_at": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
            "last_hit": "",
            "confidence": confidence,
        }
        self._save()
        logger.info(f"[CACHE] SAVE '{label}' -> '{healed}' salvo")

    # ── flow cache ───────────────────────────────────────────────────────────

    def _flow_key(self, step_name: str, bot_name: str) -> str:
        return f"{bot_name}|{step_name}"

    def get_flow(self, step_name: str, bot_name: str) -> str | None:
        key = self._flow_key(step_name, bot_name)
        entry = self._data["flows"].get(key)
        if entry:
            entry["hit_count"] = entry.get("hit_count", 0) + 1
            self._save()
            return entry["healed_code"]
        return None

    def set_flow(self, step_name: str, bot_name: str, healed_code: str) -> None:
        key = self._flow_key(step_name, bot_name)
        self._data["flows"][key] = {
            "healed_code": healed_code,
            "healed_at": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
        }
        self._save()

    # ── stats ────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        locators = self._data.get("locators", {})
        total_hits = sum(v.get("hit_count", 0) for v in locators.values())
        savings = total_hits * _COST_PER_TOKEN * 260
        most_used = max(
            locators,
            key=lambda k: locators[k].get("hit_count", 0),
            default="",
        )
        bot_counts: Counter[str] = Counter(
            v.get("bot", "") for v in locators.values()
        )
        top_bot = bot_counts.most_common(1)[0][0] if bot_counts else ""
        return {
            "total_entries": len(locators) + len(self._data.get("flows", {})),
            "total_hits": total_hits,
            "estimated_savings_usd": round(savings, 6),
            "most_used_label": most_used,
            "top_bot": top_bot,
        }

    def clear(self, bot_name: str | None = None) -> None:
        if bot_name:
            self._data["locators"] = {
                k: v for k, v in self._data["locators"].items()
                if v.get("bot") != bot_name
            }
            self._data["flows"] = {
                k: v for k, v in self._data["flows"].items()
                if not k.startswith(bot_name + "|")
            }
        else:
            self._data = {"locators": {}, "flows": {}}
        self._save()
