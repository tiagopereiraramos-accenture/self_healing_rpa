from __future__ import annotations

from pathlib import Path

from loguru import logger

from rpa_self_healing.config import settings


class GitService:
    """Auto-commits healed selectors.py files.

    Graceful degradation when no .git repository is present.
    GIT_AUTO_PUSH is always False by default — never change without authorization.
    """

    def __init__(self) -> None:
        self._repo = self._load_repo()

    def _load_repo(self):  # type: ignore[return]
        if not settings.GIT_AUTO_COMMIT:
            return None
        try:
            import git

            return git.Repo(search_parent_directories=True)
        except Exception:
            logger.warning("[GIT] ⚪ Repositório Git não encontrado — graceful degradation")
            return None

    def commit_healed_selector(
        self,
        selectors_file: Path,
        label: str,
        old_selector: str,
        new_selector: str,
        bot_name: str,
        healing_level: str = "LOCATOR",
        llm_model: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        confidence: float = 0.0,
    ) -> bool:
        if self._repo is None:
            return False

        message = (
            f"feat(self-healing): Ajustado seletor para '{label}'\n\n"
            f"Bot: {bot_name}\n"
            f"Seletor anterior: {old_selector}\n"
            f"Novo seletor:     {new_selector}\n"
            f"Nível de healing: {healing_level} (Nível {'1' if healing_level == 'LOCATOR' else '2'})\n"
            f"LLM utilizado:    {llm_model}\n"
            f"Tokens usados:    {tokens_in} input + {tokens_out} output\n"
            f"Confiança:        {confidence:.2f}\n\n"
            f"Correção automática — Framework Self-Healing RPA v3.0"
        )
        try:
            self._repo.index.add([str(selectors_file.resolve())])
            self._repo.index.commit(message)
            logger.info(f"[GIT] ⚪ Commit: {label} → {new_selector[:40]}")
            return True
        except Exception as exc:
            logger.warning(f"[GIT] Falha ao commitar: {exc}")
            return False
