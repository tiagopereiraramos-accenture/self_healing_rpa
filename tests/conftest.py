from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Configura variaveis de ambiente para testes e recria Settings."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-openrouter")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-anthropic")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("GIT_AUTO_COMMIT", "false")
    monkeypatch.setenv("PLAYWRIGHT_HEADLESS", "true")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs_test"))
    monkeypatch.setenv("CACHE_FILE", str(tmp_path / "repair_cache_test.json"))

    # Recria settings com os novos env vars
    from rpa_self_healing.config import Settings

    test_settings = Settings()
    monkeypatch.setattr("rpa_self_healing.config.settings", test_settings)

    # Limpa singleton do RepairCache
    from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache

    RepairCache.reset_instance()
