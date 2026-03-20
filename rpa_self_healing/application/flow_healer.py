from __future__ import annotations

from typing import Any


class FlowHealer:
    """Nivel 2 — reescreve bloco de codigo Playwright via LLM.

    Ativado SOMENTE quando Nivel 1 (LocatorHealer) falha apos
    ``MAX_HEALING_ATTEMPTS`` tentativas consecutivas.

    O codigo gerado e executado via ``exec()`` em namespace sandboxado
    dentro do ``PlaywrightDriver._exec_sandboxed()``.

    NAO faz: cache, execucao do codigo, stats.
    Isso e responsabilidade do ``HealingOrchestrator`` e ``PlaywrightDriver``.
    """

    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(
        self,
        step_name: str,
        failed_code: str,
        error: str,
        page_ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Consulta o LLM e retorna codigo Python reescrito.

        Returns:
            dict com chaves: code, tokens_in, tokens_out, cost_usd, model, provider.
            Se o LLM nao retornar resposta, ``code`` sera ``None``.
        """
        result = await self._llm.heal_flow(
            step_name=step_name,
            failed_code=failed_code,
            error=error,
            context=page_ctx,
        )
        code = result.get("content", "").strip()
        return {
            "code": code or None,
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
        }
