from __future__ import annotations

import re
from pathlib import Path

from loguru import logger


class SelectorRepository:
    """Updates a bot's selectors.py in-place using Regex.

    Never refactor to use AST or formatters — preserves comments and formatting.
    """

    _PATTERN = re.compile(
        r"^(?P<name>{label})\s*:\s*str\s*=\s*['\"](?P<value>[^'\"]*)['\"](?P<comment>.*)$",
        re.MULTILINE,
    )

    def update(self, selectors_file: Path, label: str, new_selector: str) -> bool:
        if not selectors_file.exists():
            logger.warning(f"[GIT] selectors.py não encontrado: {selectors_file}")
            return False

        content = selectors_file.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"^(?P<name>{re.escape(label)})\s*:\s*str\s*=\s*['\"](?P<value>[^'\"]*)['\"](?P<comment>.*)$",
            re.MULTILINE,
        )
        match = pattern.search(content)
        if not match:
            logger.warning(f"[GIT] Label '{label}' não encontrado em {selectors_file}")
            return False

        old_line = match.group(0)
        from datetime import date

        comment_part = match.group("comment").strip()
        # update or add healing comment
        healing_tag = f"  # Healing: {date.today().isoformat()}"
        if "# Healing:" in comment_part:
            comment_part = re.sub(r"#\s*Healing:\s*\S+", f"# Healing: {date.today().isoformat()}", comment_part)
            new_line = f"{label}: str = \"{new_selector}\"{comment_part if comment_part.startswith(' ') else '  ' + comment_part}"
        else:
            new_line = f'{label}: str = "{new_selector}"{healing_tag}'

        updated = content.replace(old_line, new_line, 1)
        selectors_file.write_text(updated, encoding="utf-8")
        logger.info(f"[GIT] ⚪ Seletor '{label}' atualizado em {selectors_file.name}")
        return True
