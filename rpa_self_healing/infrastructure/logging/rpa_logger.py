from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from loguru import logger

from rpa_self_healing.config import settings

# ── Loguru setup ─────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)
logger.add(
    settings.LOG_DIR / "rpa.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
(settings.LOG_DIR / "screenshots").mkdir(parents=True, exist_ok=True)

_TRANSACTIONS_FILE = settings.LOG_DIR / "rpa_transactions.jsonl"
_HEALING_FILE = settings.LOG_DIR / "healing_events.jsonl"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def log_healing_event(event: dict[str, Any]) -> None:
    _append_jsonl(_HEALING_FILE, event)


# ── TransactionTracker ───────────────────────────────────────────────────────

class TransactionTracker:
    """Context manager que rastreia uma transacao RPA para auditoria.

    Obrigatorio em todo use case (skill-4)::

        with TransactionTracker(
            bot_name="expandtesting",
            action="login",
            item_id=username,
        ) as tracker:
            await driver.goto(...)
            ...
            tracker.add_healing_stats(driver.get_healing_stats())
    """

    def __init__(self, bot_name: str, action: str, item_id: str = "") -> None:
        self._bot_name = bot_name
        self._action = action
        self._item_id = item_id
        self._start = datetime.now(timezone.utc)
        self._status = "sucesso"
        self._msg = ""
        self._data: dict[str, Any] = {}
        self._healing_stats: dict[str, Any] = {}

    @property
    def item_id(self) -> str:
        return self._item_id

    @item_id.setter
    def item_id(self, value: str) -> None:
        self._item_id = value

    # ── context manager ──────────────────────────────────────────────────────

    @staticmethod
    def _mask_pii(value: str) -> str:
        """Mascara PII usando hash parcial (SEC-9)."""
        if not value:
            return ""
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()[:8]

    def __enter__(self) -> TransactionTracker:
        masked = self._mask_pii(self._item_id)
        logger.info(f"[DRIVER] {self._bot_name}.{self._action} | item={masked}")
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, _tb: Any) -> bool:
        if exc_type is not None:
            self._status = "erro_tecnico"
            self._msg = str(exc_val)
            logger.error(f"[ERRO] {self._bot_name}.{self._action} — {exc_val}")

        duration_ms = int((datetime.now(timezone.utc) - self._start).total_seconds() * 1000)
        record: dict[str, Any] = {
            "ts": self._start.isoformat(),
            "bot": self._bot_name,
            "action": self._action,
            "item_id": self._item_id,
            "status": self._status,
            "msg": self._msg,
            "duration_ms": duration_ms,
            **self._data,
        }
        if self._healing_stats:
            record["healing"] = self._healing_stats

        _append_jsonl(_TRANSACTIONS_FILE, record)

        if self._status == "sucesso":
            logger.success(f"[OK] {self._bot_name}.{self._action} — {duration_ms}ms")
        elif self._status == "erro_logico":
            logger.warning(f"[WARN] {self._bot_name}.{self._action} — {self._msg}")

        if self._healing_stats:
            self._print_healing_report()

        return False  # nunca suprime excecoes

    # ── API publica ──────────────────────────────────────────────────────────

    def fail(self, msg: str) -> None:
        """Marca a transacao como erro logico (ex: credenciais invalidas)."""
        self._status = "erro_logico"
        self._msg = msg

    def add_data(self, key: str, value: Any) -> None:
        """Adiciona dados extras ao registro JSONL."""
        self._data[key] = value

    def add_healing_stats(self, stats: dict[str, Any]) -> None:
        """Adiciona metricas de healing ao registro (chamado no final do UC)."""
        self._healing_stats = stats

    # ── report ───────────────────────────────────────────────────────────────

    def _print_healing_report(self) -> None:
        s = self._healing_stats
        attempts = s.get("healing_attempts", 0)
        if not attempts:
            return
        successes = s.get("healing_successes", 0)
        rate = int(successes / attempts * 100) if attempts else 0
        tokens = s.get("total_tokens_in", 0) + s.get("total_tokens_out", 0)
        cost = s.get("total_cost_usd", 0.0)
        lines = [
            f"{'=' * 55}",
            f"  SELF-HEALING REPORT -- {self._bot_name}",
            f"{'=' * 55}",
            f"  Tentativas de healing:   {attempts}",
            f"  Bem-sucedidos:           {successes}  ({rate}%)",
            f"  Cache hits:              {s.get('cache_hits', 0)}",
            f"  Nivel 1 (locator):       {s.get('level1_used', 0)}",
            f"  Nivel 2 (flow):          {s.get('level2_used', 0)}",
            f"  Tokens consumidos:       {tokens}",
            f"  Custo estimado:          $ {cost:.6f}",
            f"  Commits Git:             {s.get('git_commits', 0)}",
            f"{'=' * 55}",
        ]
        logger.info("\n" + "\n".join(lines))


# ── Decorator @tracked (opcional — alternativa ao with TransactionTracker) ──

def tracked(bot_name: str, action_name: str):
    """Decorator que envolve um use case com TransactionTracker.

    Injeta ``tracker`` como keyword argument na funcao decorada.
    Adiciona healing_stats automaticamente ao final se ``self._driver`` existir.

    Uso::

        class MeuUC:
            @tracked("meu_bot", "minha-action")
            async def execute(self, param1: str = "", tracker: TransactionTracker | None = None, **kwargs) -> dict:
                tracker.item_id = param1
                await self._driver.goto(...)
                ...
                tracker.add_data("key", "value")
                tracker.fail("mensagem")  # em caso de erro logico
    """

    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            with TransactionTracker(bot_name=bot_name, action=action_name) as tracker:
                kwargs["tracker"] = tracker
                result = await fn(self, *args, **kwargs)
                if hasattr(self, "_driver") and self._driver is not None:
                    tracker.add_healing_stats(self._driver.get_healing_stats())
                return result
        return wrapper
    return decorator
