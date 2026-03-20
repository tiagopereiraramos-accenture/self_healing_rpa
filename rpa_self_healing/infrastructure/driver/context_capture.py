from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from rpa_self_healing.config import settings

if TYPE_CHECKING:
    from playwright.async_api import Page

_MAX_HTML_BYTES = 50 * 1024  # 50 KB


async def capture_context(page: "Page", label: str = "") -> dict[str, Any]:
    """Capture DOM context, accessibility tree, and screenshot for LLM healing."""
    url = page.url
    title = await page.title()

    # Screenshot → base64 (for logging; LLM receives text only)
    screenshot_path: Path | None = None
    if settings.SCREENSHOT_ON_FAILURE:
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_label = label.replace("/", "_").replace(" ", "_")
        screenshot_path = settings.LOG_DIR / "screenshots" / f"{safe_label}_{ts}.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
            logger.debug(f"[DRIVER] Screenshot: {screenshot_path.name}")
        except Exception:
            screenshot_path = None

    # HTML (truncated)
    try:
        html = await page.content()
        html = html[:_MAX_HTML_BYTES]
    except Exception:
        html = ""

    # Interactive elements list
    elements: list[dict[str, Any]] = []
    try:
        elements = await page.evaluate("""() => {
            const tags = ['input', 'button', 'a', 'select', 'textarea', '[role]', '[data-testid]'];
            const els = document.querySelectorAll(tags.join(','));
            return Array.from(els).slice(0, 60).map(el => ({
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                type: el.getAttribute('type') || null,
                role: el.getAttribute('role') || null,
                aria_label: el.getAttribute('aria-label') || null,
                data_testid: el.getAttribute('data-testid') || null,
                placeholder: el.getAttribute('placeholder') || null,
                text: (el.innerText || el.value || '').trim().slice(0, 80) || null,
                visible: el.offsetParent !== null,
            }));
        }""")
    except Exception:
        elements = []

    # Accessibility tree snapshot (text)
    a11y_tree = ""
    try:
        snapshot = await page.accessibility.snapshot()
        if snapshot:
            import json

            a11y_tree = json.dumps(snapshot, ensure_ascii=False)[:3000]
    except Exception:
        a11y_tree = ""

    return {
        "url": url,
        "title": title,
        "html": html,
        "elements": elements,
        "accessibility_tree": a11y_tree,
        "screenshot_path": str(screenshot_path) if screenshot_path else None,
    }
