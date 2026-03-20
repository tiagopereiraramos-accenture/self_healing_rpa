"""Testes unitarios para RepairCache."""
from __future__ import annotations

from pathlib import Path

from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache


def test_set_and_get_locator(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_locator("CAMPO_USERNAME", "input#broken", "input#fixed", "mybot", 0.95)

    result = cache.get_locator("CAMPO_USERNAME", "input#broken")
    assert result == "input#fixed"


def test_cache_miss_returns_none(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    result = cache.get_locator("INEXISTENTE", "input#nope")
    assert result is None


def test_hit_count_increments(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_locator("LABEL", "old", "new", "bot")

    cache.get_locator("LABEL", "old")
    cache.get_locator("LABEL", "old")
    cache.get_locator("LABEL", "old")

    entry = cache._data["locators"]["LABEL|old"]
    assert entry["hit_count"] == 3


def test_flow_cache(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_flow("step1", "mybot", "await page.click('#btn')")

    result = cache.get_flow("step1", "mybot")
    assert result == "await page.click('#btn')"


def test_flow_cache_miss(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    assert cache.get_flow("inexistente", "mybot") is None


def test_clear_all(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_locator("L1", "old1", "new1", "bot1")
    cache.set_locator("L2", "old2", "new2", "bot2")
    cache.set_flow("step", "bot1", "code")

    cache.clear()

    assert cache.get_locator("L1", "old1") is None
    assert cache.get_flow("step", "bot1") is None


def test_clear_by_bot(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_locator("L1", "old1", "new1", "bot_a")
    cache.set_locator("L2", "old2", "new2", "bot_b")
    cache.set_flow("step_a", "bot_a", "code_a")
    cache.set_flow("step_b", "bot_b", "code_b")

    cache.clear(bot_name="bot_a")

    assert cache.get_locator("L1", "old1") is None
    assert cache.get_locator("L2", "old2") == "new2"
    assert cache.get_flow("step_a", "bot_a") is None
    assert cache.get_flow("step_b", "bot_b") == "code_b"


def test_get_stats(tmp_path: Path):
    cache = RepairCache(cache_file=tmp_path / "cache.json")
    cache.set_locator("L1", "old1", "new1", "bot_a")
    cache.set_flow("step", "bot_a", "code")

    stats = cache.get_stats()
    assert stats["total_entries"] == 2
    assert stats["total_hits"] == 0
    assert stats["top_bot"] == "bot_a"


def test_persistence(tmp_path: Path):
    file = tmp_path / "cache.json"
    cache1 = RepairCache(cache_file=file)
    cache1.set_locator("LABEL", "old", "new", "bot")

    # Nova instancia lendo do mesmo arquivo
    cache2 = RepairCache(cache_file=file)
    assert cache2.get_locator("LABEL", "old") == "new"


def test_singleton():
    RepairCache.reset_instance()
    a = RepairCache.get_instance()
    b = RepairCache.get_instance()
    assert a is b
    RepairCache.reset_instance()
