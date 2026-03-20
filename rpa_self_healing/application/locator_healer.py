from __future__ import annotations

from typing import Any


class LocatorHealer:
    """Nivel 1 — sugere seletor CSS alternativo via LLM.

    Responsabilidades:
        - Chamar o LLMRouter com o contexto da pagina
        - Retornar o seletor sugerido + metadados (tokens, custo, etc.)

    NAO faz: cache, validacao de count(), git commit, stats.
    Isso e responsabilidade do ``HealingOrchestrator``.
    """

    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(
        self,
        broken_selector: str,
        label: str,
        page_ctx: dict[str, Any],
        error: str = "",
    ) -> dict[str, Any]:
        """Consulta o LLM e retorna um seletor candidato.

        Returns:
            dict com chaves: selector, tokens_in, tokens_out, cost_usd,
            confidence, model, provider.
            Se o LLM nao retornar resposta, ``selector`` sera ``None``.
        """
        result = await self._llm.heal_locator(
            broken_selector=broken_selector,
            intent=f"executar {label}",
            context=page_ctx,
            error=error,
        )
        new_selector = result.get("content", "").strip()
        return {
            "selector": new_selector or None,
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            "confidence": result.get("confidence", 0.9),
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
        }
