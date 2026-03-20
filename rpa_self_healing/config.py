from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent


class Settings:
    """Configuracoes centrais do framework, lidas do ``.env``.

    Instanciada uma unica vez como singleton (``settings``).
    Em testes, crie uma nova instancia apos ``monkeypatch.setenv()``.
    """

    def __init__(self) -> None:
        # LLM Providers
        self.OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
        self.ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # LLM Strategy
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
        self.LLM_LOCATOR_MODEL: str = os.getenv("LLM_LOCATOR_MODEL", "anthropic/claude-haiku-4-5")
        self.LLM_FLOW_MODEL: str = os.getenv("LLM_FLOW_MODEL", "anthropic/claude-sonnet-4-5")
        self.LLM_FALLBACK_MODEL: str = os.getenv("LLM_FALLBACK_MODEL", "ollama/llama3.3")
        self.LLM_MAX_HEALING_ATTEMPTS: int = int(os.getenv("LLM_MAX_HEALING_ATTEMPTS", "2"))

        # Git
        self.GIT_AUTO_COMMIT: bool = os.getenv("GIT_AUTO_COMMIT", "true").lower() in ("true", "1", "yes")
        self.GIT_AUTO_PUSH: bool = os.getenv("GIT_AUTO_PUSH", "false").lower() in ("true", "1", "yes")

        # Cache
        self.CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "json")
        self.CACHE_FILE: Path = _ROOT / os.getenv(
            "CACHE_FILE",
            "rpa_self_healing/infrastructure/cache/repair_cache.json",
        )
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Playwright
        self.PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() in ("true", "1", "yes")
        self.PLAYWRIGHT_SLOW_MO: int = int(os.getenv("PLAYWRIGHT_SLOW_MO", "300"))
        self.PLAYWRIGHT_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_TIMEOUT", "10000"))
        self.PLAYWRIGHT_HEALING_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_HEALING_TIMEOUT", "20000"))

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_DIR: Path = _ROOT / os.getenv("LOG_DIR", "logs")
        self.SCREENSHOT_ON_FAILURE: bool = os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() in ("true", "1", "yes")


settings = Settings()
