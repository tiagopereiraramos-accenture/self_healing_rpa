from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from rpa_self_healing.config import settings
from rpa_self_healing.domain.entities import HealingLevel, HealingStats
from rpa_self_healing.infrastructure.driver.context_capture import capture_context
from rpa_self_healing.infrastructure.git.git_service import GitService
from rpa_self_healing.infrastructure.git.selector_repository import SelectorRepository


class PlaywrightDriver:
    """Driver Playwright com self-healing integrado em dois niveis.

    Uso::

        async with PlaywrightDriver(
            selectors_file=Path("bots/mybot/selectors.py"),
            bot_name="mybot",
        ) as driver:
            await driver.goto("https://example.com")
            await driver.click("BUTTON", sel.BUTTON)

    NUNCA instancie ``async_playwright()`` diretamente em bots ou use cases.
    """

    def __init__(
        self,
        selectors_file: Path | None = None,
        bot_name: str = "unknown",
        headless: bool | None = None,
    ) -> None:
        self._selectors_file = selectors_file
        self._bot_name = bot_name
        self._headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS

        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        # Healing: lazy-init (so criado na 1a falha)
        self._orchestrator = None
        self._git = GitService()
        self._selector_repo = SelectorRepository()

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def __aenter__(self) -> PlaywrightDriver:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            slow_mo=settings.PLAYWRIGHT_SLOW_MO,
        )
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._page.set_default_timeout(settings.PLAYWRIGHT_TIMEOUT)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @property
    def page(self) -> Page:
        assert self._page is not None, "Driver nao inicializado. Use 'async with PlaywrightDriver() as driver'."
        return self._page

    # ── API publica (acoes com self-healing) ─────────────────────────────────

    async def goto(self, url: str) -> None:
        logger.info(f"[DRIVER] goto {url}")
        await self.page.goto(url, wait_until="domcontentloaded")

    async def click(self, label: str, selector: str, force_flow_heal: bool = False) -> None:
        await self._with_healing(label, selector, "click", force_flow_heal=force_flow_heal)

    async def fill(self, label: str, selector: str, value: str) -> None:
        await self._with_healing(label, selector, "fill", value=value)

    async def get_text(self, label: str, selector: str) -> str:
        return await self._with_healing(label, selector, "get_text") or ""

    async def wait_for(self, label: str, selector: str) -> None:
        await self._with_healing(label, selector, "wait_for")

    async def is_visible(self, selector: str, heal: bool = False) -> bool:
        """Verifica visibilidade — NAO ativa healing por padrao."""
        try:
            return await self.page.locator(selector).is_visible()
        except Exception:
            return False

    # ── deteccao proativa ────────────────────────────────────────────────────

    async def detect_broken_selectors(
        self, pairs: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Verifica quais seletores estao ausentes na pagina."""
        broken = []
        for label, selector in pairs:
            try:
                count = await self.page.locator(selector).count()
                if count == 0:
                    broken.append((label, selector))
            except Exception:
                broken.append((label, selector))
        return broken

    async def heal_proactive(self, broken: list[tuple[str, str]]) -> None:
        """Healing preventivo para seletores ausentes (antes de quebrar)."""
        logger.warning(f"[HEALER] Healing proativo para {len(broken)} seletor(es)")
        orchestrator = self._get_orchestrator()

        for label, selector in broken:
            try:
                ctx = await capture_context(self.page, f"{self._bot_name}_{label}")

                async def validate(sel: str) -> bool:
                    try:
                        return await self.page.locator(sel).count() > 0
                    except Exception:
                        return False

                result = await orchestrator.heal(
                    label=label,
                    broken_selector=selector,
                    page_ctx=ctx,
                    error="proactive detection",
                    validate=validate,
                )
                if result.success and result.selector:
                    self._persist_healed_selector(label, selector, result)
            except Exception as exc:
                logger.error(f"[HEALER] Falha no healing proativo de '{label}': {exc}")

    def get_healing_stats(self) -> dict[str, Any]:
        """Retorna metricas de healing da sessao atual."""
        if self._orchestrator:
            return self._orchestrator.stats.to_dict()
        return HealingStats(session_id="", bot=self._bot_name).to_dict()

    # ── execucao interna ─────────────────────────────────────────────────────

    async def _execute_action(self, selector: str, action: str, **kwargs: Any) -> Any:
        loc = self.page.locator(selector)
        if action == "click":
            await loc.click()
        elif action == "fill":
            await loc.fill(kwargs["value"])
        elif action == "get_text":
            return await loc.inner_text()
        elif action == "wait_for":
            await self.page.wait_for_selector(selector, timeout=settings.PLAYWRIGHT_TIMEOUT)
        return None

    async def _with_healing(
        self,
        label: str,
        selector: str,
        action: str,
        force_flow_heal: bool = False,
        **kwargs: Any,
    ) -> Any:
        if force_flow_heal:
            return await self._force_flow_heal(label, selector, action, **kwargs)

        try:
            logger.debug(f"[DRIVER] {action}('{label}', '{selector}')")
            return await self._execute_action(selector, action, **kwargs)
        except Exception as exc:
            logger.warning(f"[HEALER] Healing ativado: '{label}' — {type(exc).__name__}")
            return await self._do_heal(label, selector, action, exc, **kwargs)

    async def _do_heal(
        self,
        label: str,
        selector: str,
        action: str,
        exc: Exception,
        **kwargs: Any,
    ) -> Any:
        orchestrator = self._get_orchestrator()
        ctx = await capture_context(self.page, f"{self._bot_name}_{label}")
        failed_code = self._build_failed_code(selector, action, **kwargs)

        async def validate(sel: str) -> bool:
            try:
                return await self.page.locator(sel).count() > 0
            except Exception:
                return False

        result = await orchestrator.heal(
            label=label,
            broken_selector=selector,
            page_ctx=ctx,
            error=str(exc),
            validate=validate,
            failed_code=failed_code,
        )

        # Nivel 1: novo seletor encontrado
        if result.success and result.selector:
            self._persist_healed_selector(label, selector, result)
            return await self._execute_action(result.selector, action, **kwargs)

        # Nivel 2: codigo reescrito
        if result.success and result.code:
            try:
                return await self._exec_sandboxed(result.code, **kwargs)
            except Exception as flow_exc:
                logger.error(f"[FLOW] Codigo gerado falhou para '{label}': {flow_exc}")

        # Healing falhou — re-raise excecao original
        raise exc

    async def _force_flow_heal(
        self, label: str, selector: str, action: str, **kwargs: Any,
    ) -> Any:
        orchestrator = self._get_orchestrator()
        ctx = await capture_context(self.page, label)
        failed_code = self._build_failed_code(selector, action, **kwargs)

        result = await orchestrator.heal_flow_direct(
            label=label,
            failed_code=failed_code,
            error="force_flow_heal",
            page_ctx=ctx,
        )

        if result.success and result.code:
            return await self._exec_sandboxed(result.code, **kwargs)
        raise RuntimeError(f"Flow healing falhou para '{label}'")

    async def _exec_sandboxed(self, code: str, **kwargs: Any) -> Any:
        """Executa codigo gerado pelo LLM em namespace isolado com suporte a await."""
        local_vars: dict[str, Any] = {"page": self.page, **kwargs}
        lines = "\n".join(f"    {line}" for line in code.strip().splitlines())
        fn_code = f"async def __heal__():\n{lines}"
        exec(compile(fn_code, "<healing>", "exec"), local_vars)  # noqa: S102
        return await local_vars["__heal__"]()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_orchestrator(self):
        if self._orchestrator is None:
            from rpa_self_healing.application.healing_orchestrator import HealingOrchestrator
            self._orchestrator = HealingOrchestrator(bot_name=self._bot_name)
        return self._orchestrator

    def _build_failed_code(self, selector: str, action: str, **kwargs: Any) -> str:
        if action == "fill":
            return f"await page.fill('{selector}', '{kwargs.get('value', '')}')"
        return f"await page.{action}('{selector}')"

    def _persist_healed_selector(self, label: str, old_selector: str, result) -> None:
        """Atualiza selectors.py e commita via Git (se habilitado)."""
        if not self._selectors_file or not result.event:
            return
        updated = self._selector_repo.update(
            self._selectors_file, label, result.selector,
        )
        if not updated:
            return
        event = result.event
        committed = self._git.commit_healed_selector(
            selectors_file=self._selectors_file,
            label=label,
            old_selector=old_selector,
            new_selector=result.selector,
            bot_name=self._bot_name,
            healing_level=str(result.level),
            llm_model=f"{event.llm_model} ({event.llm_provider})" if event.llm_model else "",
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            confidence=event.confidence,
        )
        if committed and self._orchestrator:
            self._orchestrator.stats.git_commits += 1
