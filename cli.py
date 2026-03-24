from __future__ import annotations

"""rpa-cli — Dynamic dispatcher for Self-Healing RPA framework.

Rules (skill-2):
- Never add add_argument() calls for bot actions.
- All --param values are parsed dynamically and injected as **kwargs.
- Global flags (--list, --healing-stats, --cache-stats, --cache-clear) are
  handled here before routing to any bot.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any


def _parse_kwargs(args: list[str]) -> dict[str, Any]:
    """Parse --key value / --flag pairs into a dict."""
    kwargs: dict[str, Any] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                kwargs[key] = args[i + 1]
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            i += 1
    return kwargs


def _print_list() -> None:
    from rich.console import Console
    from rich.table import Table

    from bots.registry import get_registry

    registry = get_registry()
    console = Console()
    table = Table(title="Self-Healing RPA — Bots Registrados", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Nome", style="white")
    table.add_column("Descrição", style="dim")
    table.add_column("Actions", style="green")

    for bot_id, bot_class in sorted(registry.items()):
        # Instantiate without driver just to enumerate actions
        try:
            from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver

            bot = bot_class.__new__(bot_class)
            bot._driver = None  # type: ignore[assignment]
            actions = ", ".join(bot.get_actions().keys())
        except Exception:
            actions = "—"
        table.add_row(bot_id, bot_class.name, bot_class.description, actions)
    console.print(table)


def _print_bot_help(bot_id: str) -> None:
    from rich.console import Console

    from bots.registry import get_bot_class

    console = Console()
    bot_class = get_bot_class(bot_id)
    try:
        bot = bot_class.__new__(bot_class)
        bot._driver = None  # type: ignore[assignment]
        actions = bot.get_actions()
    except Exception:
        actions = {}
    console.print(f"\n[bold cyan]{bot_id}[/] — {bot_class.description}")
    console.print(f"URL: [dim]{bot_class.url}[/]\n")
    console.print("[bold]Actions disponíveis:[/]")
    for name in actions:
        console.print(f"  [green]{name}[/]")
    console.print(f"\nExemplo: uv run rpa-cli {bot_id} {list(actions.keys())[0] if actions else '<action>'} --param valor\n")


def _print_cache_stats() -> None:
    from rich.console import Console
    from rich.panel import Panel

    from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache

    cache = RepairCache()
    stats = cache.get_stats()
    Console().print(
        Panel(
            f"[cyan]Entradas no cache:[/]         {stats['total_entries']}\n"
            f"[cyan]Cache hits (total):[/]        {stats['total_hits']}\n"
            f"[cyan]Chamadas LLM evitadas:[/]     {stats['total_hits']}\n"
            f"[cyan]Economia estimada:[/]          $ {stats['estimated_savings_usd']:.6f}\n"
            f"[cyan]Seletor mais reutilizado:[/]   {stats.get('most_used_label', '—')}\n"
            f"[cyan]Bot com mais reparos:[/]       {stats.get('top_bot', '—')}",
            title="RELATÓRIO DE CACHE — Self-Healing RPA",
        )
    )


def _print_healing_stats() -> None:
    from rich.console import Console

    from rpa_self_healing.config import settings

    console = Console()
    healing_file = settings.LOG_DIR / "healing_events.jsonl"
    if not healing_file.exists():
        console.print("[yellow]Nenhum evento de healing registrado ainda.[/]")
        return

    import json

    events = [json.loads(line) for line in healing_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(events)
    successes = sum(1 for e in events if e.get("success", True))
    total_cost = sum(e.get("cost_usd", 0.0) for e in events)
    cache_hits = sum(1 for e in events if e.get("from_cache", False))
    models: dict[str, int] = {}
    for e in events:
        m = e.get("llm_model", "unknown")
        models[m] = models.get(m, 0) + 1
    top_model = max(models, key=lambda k: models[k], default="—")
    rate = f"{successes / total * 100:.1f}%" if total else "N/A"

    console.print(
        f"\n[bold]Período:[/] últimos 7 dias\n"
        f"[bold]Total de healings:[/]   {total}\n"
        f"[bold]Taxa de sucesso:[/]     {rate}\n"
        f"[bold]Custo total:[/]         ${total_cost:.4f}\n"
        f"[bold]Economia por cache:[/]  {cache_hits} hits\n"
        f"[bold]Modelo mais usado:[/]   {top_model}\n"
    )


async def _run_bot_action(bot_id: str, action_name: str, kwargs: dict[str, Any]) -> None:
    from pathlib import Path

    from rich.console import Console

    from bots.registry import get_bot_class
    from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver

    console = Console()
    bot_class = get_bot_class(bot_id)
    selectors_file = Path("bots") / bot_id / "selectors.py"
    headless = kwargs.pop("headless", None)
    if headless is not None:
        headless = headless is True or str(headless).lower() in ("true", "1")

    async with PlaywrightDriver(
        selectors_file=selectors_file if selectors_file.exists() else None,
        bot_name=bot_id,
        headless=headless,
    ) as driver:
        bot = bot_class(driver)
        actions = bot.get_actions()
        if action_name not in actions:
            console.print(f"[red]Action '{action_name}' não encontrada em '{bot_id}'.[/]")
            console.print(f"Disponíveis: {', '.join(actions.keys())}")
            sys.exit(1)
        result = await actions[action_name](**kwargs)

    console.print("\n[bold]Resultado:[/]")
    import json as _json

    console.print(_json.dumps(result, indent=2, ensure_ascii=False, default=str))


def _scaffold_bot(bot_name: str, kwargs: dict[str, Any]) -> None:
    """Gera a estrutura completa de um novo bot."""
    from rich.console import Console

    console = Console()
    url = kwargs.get("url", "https://example.com")
    actions_str = kwargs.get("actions", "exemplo")
    action_list = [a.strip() for a in str(actions_str).split(",") if a.strip()]

    bots_dir = Path("bots") / bot_name
    if bots_dir.exists():
        console.print(f"[red]Pasta bots/{bot_name}/ ja existe.[/]")
        sys.exit(1)

    uc_dir = bots_dir / "use_cases"
    uc_dir.mkdir(parents=True, exist_ok=True)
    (uc_dir / "__init__.py").write_text("", encoding="utf-8")

    # selectors.py
    (bots_dir / "selectors.py").write_text(
        f"# Seletores do Bot: {bot_name}\n"
        f"# Adicione seus seletores CSS aqui\n\n"
        f'CAMPO_PRINCIPAL: str = "[name=\'campo\']"\n'
        f"BOTAO_CONFIRMAR: str = \"button:has-text('Confirmar')\"\n",
        encoding="utf-8",
    )

    # use cases
    for action_name in action_list:
        fn_name = action_name.replace("-", "_")
        uc_file = uc_dir / f"{fn_name}_uc.py"
        uc_file.write_text(
            f"from __future__ import annotations\n\n"
            f"from rpa_self_healing import use_case, OK\n"
            f"import bots.{bot_name}.selectors as sel\n\n\n"
            f'@use_case("{bot_name}", "{action_name}")\n'
            f"async def {fn_name}(driver, **kwargs):\n"
            f'    await driver.goto("{url}")\n'
            f'    return OK(msg="{action_name} executado")\n',
            encoding="utf-8",
        )

    # __init__.py
    class_name = "".join(w.capitalize() for w in bot_name.split("_")) + "Bot"
    (bots_dir / "__init__.py").write_text(
        f"from __future__ import annotations\n\n"
        f"from bots.base import bot\n\n\n"
        f'@bot(name="{bot_name}", description="Bot {bot_name}", url="{url}")\n'
        f"class {class_name}:\n"
        f"    pass  # actions auto-descobertas de use_cases/\n",
        encoding="utf-8",
    )

    console.print(f"\n[green]Bot '{bot_name}' criado com sucesso![/]\n")
    console.print(f"  [dim]bots/{bot_name}/[/]")
    console.print(f"  [dim]  __init__.py[/]        — {class_name} com @bot decorator")
    console.print(f"  [dim]  selectors.py[/]       — seletores CSS")
    console.print(f"  [dim]  use_cases/[/]")
    for action_name in action_list:
        fn_name = action_name.replace("-", "_")
        console.print(f"  [dim]    {fn_name}_uc.py[/]  — @use_case(\"{action_name}\")")
    console.print(f"\n[cyan]Para testar:[/] uv run rpa-cli {bot_name} {action_list[0]}\n")


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Uso: rpa-cli [--list | --healing-stats | --cache-stats | --cache-clear\n"
            "             | scaffold <bot> [--url URL] [--actions a,b,c]\n"
            "             | <bot> [<action> [--param val ...]]]"
        )
        sys.exit(0)

    # Global flags
    if "--list" in args:
        _print_list()
        return

    if "--healing-stats" in args:
        _print_healing_stats()
        return

    if "--cache-stats" in args:
        _print_cache_stats()
        return

    if "--cache-clear" in args:
        from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache

        kwargs = _parse_kwargs(args)
        bot_filter = kwargs.get("bot")
        RepairCache().clear(bot_name=bot_filter if isinstance(bot_filter, str) else None)
        print(f"Cache limpo{f' para bot={bot_filter}' if bot_filter else ''}.")
        return

    # Scaffold command
    if args[0] == "scaffold":
        if len(args) < 2:
            print("Uso: rpa-cli scaffold <nome_do_bot> [--url URL] [--actions login,coleta]")
            sys.exit(1)
        bot_name = args[1]
        kwargs = _parse_kwargs(args[2:])
        _scaffold_bot(bot_name, kwargs)
        return

    # Bot routing
    bot_id = args[0]
    remaining = args[1:]

    if not remaining or remaining[0].startswith("--"):
        _print_bot_help(bot_id)
        return

    action_name = remaining[0]
    kwargs = _parse_kwargs(remaining[1:])
    asyncio.run(_run_bot_action(bot_id, action_name, kwargs))


if __name__ == "__main__":
    main()
