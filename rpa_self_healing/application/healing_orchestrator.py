from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.entities import (
    HealingEvent,
    HealingLevel,
    HealingResult,
    HealingStats,
)
from rpa_self_healing.infrastructure.logging.rpa_logger import log_healing_event


class HealingOrchestrator:
    """Coordena o fluxo completo de self-healing: cache -> Nivel 1 -> Nivel 2.

    Fluxo MAPE-K:
        Monitor  -> detecta falha (excecao Playwright) ou proativa
        Analyze  -> consulta cache + captura contexto da pagina
        Plan     -> decide nivel 1 (seletor) ou nivel 2 (reescrita de codigo)
        Execute  -> chama LLM via LocatorHealer/FlowHealer, valida resultado
        Knowledge -> persiste no RepairCache, loga evento

    Nunca instancie esta classe em bots — ela e gerenciada pelo PlaywrightDriver.
    """

    def __init__(self, bot_name: str) -> None:
        self._bot_name = bot_name
        self._stats = HealingStats(session_id=str(uuid.uuid4()), bot=bot_name)

        # Lazy-init de infraestrutura (so criados na 1a chamada de healing)
        self._cache = None
        self._locator = None
        self._flow = None

    def _ensure_ready(self) -> None:
        """Inicializa cache, LLM e healers sob demanda."""
        if self._cache is not None:
            return
        from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache
        from rpa_self_healing.infrastructure.llm.llm_router import LLMRouter

        from rpa_self_healing.application.locator_healer import LocatorHealer
        from rpa_self_healing.application.flow_healer import FlowHealer

        self._cache = RepairCache.get_instance()
        llm = LLMRouter()
        self._locator = LocatorHealer(llm)
        self._flow = FlowHealer(llm)

    @property
    def stats(self) -> HealingStats:
        return self._stats

    # ── API publica ──────────────────────────────────────────────────────────

    async def heal(
        self,
        label: str,
        broken_selector: str,
        page_ctx: dict[str, Any],
        error: str,
        validate: Callable[[str], Awaitable[bool]],
        failed_code: str = "",
    ) -> HealingResult:
        """Tenta curar um seletor quebrado: cache -> Nivel 1 -> Nivel 2.

        Args:
            label: Nome do seletor (ex: ``CAMPO_USERNAME``).
            broken_selector: Seletor CSS que falhou.
            page_ctx: Contexto da pagina (DOM, a11y tree, etc.).
            error: Mensagem de erro original.
            validate: Callback ``async (selector) -> bool`` que verifica
                      se o seletor candidato existe na pagina (``count() > 0``).
            failed_code: Codigo Python que falhou (usado pelo Flow Healer).

        Returns:
            ``HealingResult`` com o seletor curado ou codigo reescrito.
        """
        self._ensure_ready()
        t0 = time.monotonic()

        # ── Nivel 1: Locator Healing ────────────────────────────────────
        self._stats.healing_attempts += 1
        self._stats.level1_used += 1

        # 1. Cache (obrigatorio — skill-8)
        cached = self._cache.get_locator(label, broken_selector)
        if cached:
            self._stats.cache_hits += 1
            if await validate(cached):
                return self._locator_success(
                    label, broken_selector, cached, t0, from_cache=True,
                )
            # Cache stale — prosseguir para LLM
        else:
            self._stats.cache_misses += 1

        # 2. LLM com retries
        for _ in range(settings.LLM_MAX_HEALING_ATTEMPTS):
            suggestion = await self._locator.suggest(
                broken_selector=broken_selector,
                label=label,
                page_ctx=page_ctx,
                error=error,
            )
            self._track_tokens(suggestion)

            new_selector = suggestion.get("selector")
            if new_selector and await validate(new_selector):
                self._cache.set_locator(
                    label, broken_selector, new_selector,
                    self._bot_name, suggestion.get("confidence", 0.9),
                )
                return self._locator_success(
                    label, broken_selector, new_selector, t0,
                    suggestion=suggestion,
                )

        # ── Nivel 2: Flow Healing (escalacao) ───────────────────────────
        logger.warning(
            f"[FLOW] Escalando para Flow Healing — '{label}' "
            f"falhou {settings.LLM_MAX_HEALING_ATTEMPTS}x no Nivel 1"
        )
        self._stats.level2_used += 1
        return await self._try_flow(label, failed_code, error, page_ctx, t0)

    async def heal_flow_direct(
        self,
        label: str,
        failed_code: str,
        error: str,
        page_ctx: dict[str, Any],
    ) -> HealingResult:
        """Forca Flow Healing (Nivel 2) diretamente, sem tentar Nivel 1."""
        self._ensure_ready()
        self._stats.healing_attempts += 1
        self._stats.level2_used += 1
        return await self._try_flow(label, failed_code, error, page_ctx, time.monotonic())

    # ── helpers internos ─────────────────────────────────────────────────

    async def _try_flow(
        self,
        label: str,
        failed_code: str,
        error: str,
        page_ctx: dict[str, Any],
        t0: float,
    ) -> HealingResult:
        # Flow cache check
        cached_code = self._cache.get_flow(label, self._bot_name)
        if cached_code:
            self._stats.cache_hits += 1
            self._stats.healing_successes += 1
            self._stats.total_healing_ms += int((time.monotonic() - t0) * 1000)
            return HealingResult(
                success=True, code=cached_code,
                level=HealingLevel.FLOW, from_cache=True,
            )

        # LLM call
        suggestion = await self._flow.suggest(
            step_name=label,
            failed_code=failed_code,
            error=error,
            page_ctx=page_ctx,
        )
        self._track_tokens(suggestion)

        code = suggestion.get("code")
        if code:
            self._cache.set_flow(label, self._bot_name, code)
            self._stats.healing_successes += 1
            duration = int((time.monotonic() - t0) * 1000)
            self._stats.total_healing_ms += duration
            logger.success(f"[OK] Healing nivel 2 (flow) bem-sucedido para '{label}'")
            return HealingResult(success=True, code=code, level=HealingLevel.FLOW)

        logger.error(f"[FLOW] Flow healer retornou codigo vazio para '{label}'")
        self._stats.healing_failures += 1
        return HealingResult(success=False)

    def _locator_success(
        self,
        label: str,
        broken: str,
        healed: str,
        t0: float,
        from_cache: bool = False,
        suggestion: dict[str, Any] | None = None,
    ) -> HealingResult:
        self._stats.healing_successes += 1
        duration = int((time.monotonic() - t0) * 1000)
        self._stats.total_healing_ms += duration

        s = suggestion or {}
        event = HealingEvent(
            bot=self._bot_name,
            selector_label=label,
            broken_selector=broken,
            healed_selector=healed,
            healing_level=HealingLevel.LOCATOR,
            llm_provider=s.get("provider", ""),
            llm_model=s.get("model", ""),
            tokens_in=s.get("tokens_in", 0),
            tokens_out=s.get("tokens_out", 0),
            cost_usd=s.get("cost_usd", 0.0),
            confidence=s.get("confidence", 0.0),
            from_cache=from_cache,
            success=True,
            duration_ms=duration,
        )
        log_healing_event(event.__dict__)

        level_label = "cache" if from_cache else "nivel 1"
        logger.success(f"[OK] Healing {level_label} bem-sucedido: '{label}' -> '{healed}'")

        return HealingResult(
            success=True, selector=healed, level=HealingLevel.LOCATOR,
            from_cache=from_cache, event=event,
        )

    def _track_tokens(self, suggestion: dict[str, Any]) -> None:
        self._stats.total_tokens_in += suggestion.get("tokens_in", 0)
        self._stats.total_tokens_out += suggestion.get("tokens_out", 0)
        self._stats.total_cost_usd += suggestion.get("cost_usd", 0.0)
