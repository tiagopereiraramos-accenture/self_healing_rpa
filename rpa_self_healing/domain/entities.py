from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class HealingLevel(StrEnum):
    """Nivel de healing aplicado pelo framework."""

    LOCATOR = "LOCATOR"
    FLOW = "FLOW"
    PROACTIVE = "PROACTIVE"


class ActionStatus(StrEnum):
    """Status padrao de retorno de actions dos bots."""

    SUCESSO = "sucesso"
    ERRO_LOGICO = "erro_logico"
    ERRO_TECNICO = "erro_tecnico"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HealingEvent:
    """Registro de um evento de healing para logs e observabilidade."""

    bot: str
    selector_label: str
    broken_selector: str
    healed_selector: str | None = None
    healing_level: HealingLevel = HealingLevel.LOCATOR
    llm_provider: str = ""
    llm_model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    from_cache: bool = False
    confidence: float = 0.0
    duration_ms: int = 0
    success: bool = False
    ts: str = field(default_factory=_now_iso)


@dataclass
class HealingResult:
    """Resultado de uma tentativa de healing retornado pelo HealingOrchestrator.

    Campos:
        success   -- ``True`` se o healing encontrou solucao.
        selector  -- Novo seletor CSS (Nivel 1) ou ``None``.
        code      -- Codigo Python gerado (Nivel 2) ou ``None``.
        level     -- Nivel de healing aplicado.
        from_cache -- Se a solucao veio do RepairCache.
        event     -- Evento de healing para auditoria.
    """

    success: bool
    selector: str | None = None
    code: str | None = None
    level: HealingLevel = HealingLevel.LOCATOR
    from_cache: bool = False
    event: HealingEvent | None = None


@dataclass
class RepairRecord:
    healed: str
    bot: str
    healed_at: str
    hit_count: int = 0
    last_hit: str = ""
    confidence: float = 0.0


@dataclass
class FlowRepairRecord:
    healed_code: str
    healed_at: str
    hit_count: int = 0


@dataclass
class HealingStats:
    """Metricas acumuladas de healing durante uma sessao."""

    session_id: str
    bot: str
    healing_attempts: int = 0
    healing_successes: int = 0
    healing_failures: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    level1_used: int = 0
    level2_used: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_healing_ms: int = 0
    git_commits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "bot": self.bot,
            "healing_attempts": self.healing_attempts,
            "healing_successes": self.healing_successes,
            "healing_failures": self.healing_failures,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "level1_used": self.level1_used,
            "level2_used": self.level2_used,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_usd": self.total_cost_usd,
            "total_healing_ms": self.total_healing_ms,
            "git_commits": self.git_commits,
        }
