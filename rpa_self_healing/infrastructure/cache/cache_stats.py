from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rpa_self_healing.config import settings


class CacheStatsReporter:
    """Gera relatorios formatados de cache para o CLI.

    Usado por ``uv run rpa-cli --cache-stats``.
    """

    def __init__(self, cache_stats: dict[str, Any]) -> None:
        self._stats = cache_stats

    def as_dict(self) -> dict[str, Any]:
        return self._stats

    def format_report(self) -> str:
        s = self._stats
        lines = [
            "=" * 48,
            "        RELATORIO DE CACHE -- Self-Healing RPA",
            "=" * 48,
            f" Entradas no cache:          {s.get('total_entries', 0)}",
            f" Cache hits (total):         {s.get('total_hits', 0)}",
            f" Chamadas LLM evitadas:      {s.get('total_hits', 0)}",
            f" Economia estimada:          $ {s.get('estimated_savings_usd', 0):.6f}",
            f" Seletor mais reutilizado:   {s.get('most_used_label', '--')}",
            f" Bot com mais reparos:       {s.get('top_bot', '--')}",
            "=" * 48,
        ]
        return "\n".join(lines)


class HealingStatsReporter:
    """Gera relatorios historicos de healing lidos do JSONL.

    Usado por ``uv run rpa-cli --healing-stats``.
    """

    def __init__(self, healing_file: Path | None = None) -> None:
        self._file = healing_file or (settings.LOG_DIR / "healing_events.jsonl")

    def load_events(self) -> list[dict[str, Any]]:
        if not self._file.exists():
            return []
        lines = self._file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def summary(self) -> dict[str, Any]:
        events = self.load_events()
        if not events:
            return {"total": 0}

        total = len(events)
        successes = sum(1 for e in events if e.get("success", True))
        total_cost = sum(e.get("cost_usd", 0.0) for e in events)
        cache_hits = sum(1 for e in events if e.get("from_cache", False))
        models: dict[str, int] = {}
        for e in events:
            m = e.get("llm_model", "unknown")
            models[m] = models.get(m, 0) + 1
        top_model = max(models, key=lambda k: models[k], default="--")
        rate = f"{successes / total * 100:.1f}%" if total else "N/A"

        return {
            "total": total,
            "successes": successes,
            "rate": rate,
            "total_cost": total_cost,
            "cache_hits": cache_hits,
            "top_model": top_model,
        }

    def format_report(self) -> str:
        s = self.summary()
        if s["total"] == 0:
            return "Nenhum evento de healing registrado ainda."
        return (
            f"\nPeriodo: ultimos 7 dias\n"
            f"Total de healings:   {s['total']}\n"
            f"Taxa de sucesso:     {s['rate']}\n"
            f"Custo total:         ${s['total_cost']:.4f}\n"
            f"Economia por cache:  {s['cache_hits']} hits\n"
            f"Modelo mais usado:   {s['top_model']}\n"
        )
