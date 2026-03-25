---
skill: 2
description: CLI dinamico e roteamento de bots -- NUNCA adicionar add_argument() para actions
---

# Skill 2 -- CLI e Roteamento Dinamico

O `cli.py` e o ponto de entrada unico do framework. Todos os parametros de actions
sao parseados dinamicamente -- NUNCA adicionar `add_argument()` para parametros de bots.

---

## 1. Entry Point

Definido no `pyproject.toml`:

```toml
[project.scripts]
rpa-cli = "cli:main"
```

Execucao: `uv run rpa-cli <bot_id> <action> [--param value ...]`
Scaffold: `uv run rpa-cli scaffold <bot_name> [--url URL] [--actions a,b,c]`

## 2. Parsing Dinamico -- `_parse_kwargs()`

A funcao `_parse_kwargs` converte argumentos da linha de comando em um `dict[str, Any]`:

```python
# cli.py (implementacao real)
def _parse_kwargs(args: list[str]) -> dict[str, Any]:
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
```

Comportamento:
- `--username user` resulta em `{"username": "user"}`
- `--headless` (sem valor) resulta em `{"headless": True}`
- Hifens em keys viram underscores: `--my-param` -> `my_param`

## 3. Regra de Ouro

> **NUNCA adicionar `add_argument()` ao CLI para parametros de bot actions.**
> Todos os `--param value` sao parseados automaticamente e injetados como `**kwargs`.

Para criar uma nova action, basta decorar o metodo com `@action("nome")` na classe do bot.
O CLI descobre automaticamente.

## 4. Flags Globais

Tratadas pelo `cli.py` ANTES do roteamento -- nao chegam aos bots:

```bash
uv run rpa-cli --list                        # Rich table com todos os bots registrados
uv run rpa-cli --healing-stats               # Relatorio de healings do healing_events.jsonl
uv run rpa-cli --cache-stats                 # Hits, misses, economia estimada do RepairCache
uv run rpa-cli --cache-clear                 # Limpa todo o cache de reparos
uv run rpa-cli --cache-clear --bot mybot     # Limpa cache apenas do bot especificado
```

## 5. Roteamento de Bots -- `_run_bot_action()`

Fluxo real de `_run_bot_action`:

1. Obtem a classe do bot via `get_bot_class(bot_id)` do registry
2. Determina `selectors_file = Path("bots") / bot_id / "selectors.py"`
3. Pop do kwarg `headless` e converte para `bool` (tratamento especial)
4. Cria `PlaywrightDriver` como async context manager
5. Instancia o bot passando o driver: `bot = bot_class(driver)`
6. Chama `bot.get_actions()[action_name](**kwargs)`
7. Exibe resultado como JSON formatado no terminal

```python
# cli.py (trecho real)
async def _run_bot_action(bot_id: str, action_name: str, kwargs: dict[str, Any]) -> None:
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
            console.print(f"[red]Action '{action_name}' nao encontrada em '{bot_id}'.[/]")
            sys.exit(1)
        result = await actions[action_name](**kwargs)
```

## 6. Registry -- Auto-Discovery de Bots

O `bots/registry.py` descobre bots automaticamente:

```python
# bots/registry.py (implementacao real)
def _discover() -> dict[str, Any]:
    bots: dict[str, Any] = {}
    for bot_dir in _BOTS_DIR.iterdir():
        if not bot_dir.is_dir() or bot_dir.name.startswith("_") or bot_dir.name == "__pycache__":
            continue
        init_file = bot_dir / "__init__.py"
        if not init_file.exists():
            continue
        module_name = f"bots.{bot_dir.name}"
        mod = importlib.import_module(module_name)
        bot_class = getattr(mod, "BOT_CLASS", None)
        if bot_class is None:
            continue
        bots[bot_dir.name] = bot_class
    return bots
```

Regras de discovery:
- Diretorios que comecam com `_` sao ignorados
- `__pycache__` e ignorado
- O diretorio precisa ter `__init__.py`
- O modulo precisa exportar `BOT_CLASS`

## 7. Ajuda por Bot -- `_print_bot_help()`

Ao chamar `uv run rpa-cli <bot_id>` sem action, exibe actions disponiveis:

```python
# cli.py
def _print_bot_help(bot_id: str) -> None:
    bot_class = get_bot_class(bot_id)
    bot = bot_class.__new__(bot_class)
    bot._driver = None
    actions = bot.get_actions()
    # Exibe nome, descricao, URL e lista de actions
```

## 8. Listagem de Bots -- `_print_list()`

`uv run rpa-cli --list` exibe uma Rich Table com colunas: ID, Nome, Descricao, Actions.

## 9. Exemplos de Uso

```bash
# Executar action de um bot
uv run rpa-cli expandtesting login --username user --password pass

# Executar com browser visivel
uv run rpa-cli expandtesting login --username user --password pass --headless false

# Listar bots disponiveis
uv run rpa-cli --list

# Ver actions de um bot
uv run rpa-cli expandtesting

# Estatisticas
uv run rpa-cli --healing-stats
uv run rpa-cli --cache-stats
```

## 10. Como Adicionar uma Nova Action

Nao e necessario alterar `cli.py`. Basta:

1. Adicionar metodo com `@action("nome")` na classe do bot
2. Receber parametros como keyword arguments
3. Retornar `dict` com resultado

O CLI descobre e roteia automaticamente.

## 11. Scaffold — Gerador de Bots

O comando `scaffold` gera a estrutura completa de um novo bot no estilo v3.2:

```bash
uv run rpa-cli scaffold meu_bot --url https://site.com --actions login,coleta
```

### O que e gerado

```
bots/meu_bot/
├── __init__.py          # @bot decorator com auto-discovery
├── selectors.py         # Arquivo de seletores vazio
└── use_cases/
    ├── __init__.py
    ├── login_uc.py      # @use_case com OK/FAIL
    └── coleta_uc.py     # @use_case com OK/FAIL
```

### Estilo do codigo gerado

O bot gerado usa o estilo v3.2:
- `__init__.py` usa o decorator `@bot` para auto-discovery (herda `BaseBot` automaticamente e define `BOT_CLASS`)
- Cada use case usa `@use_case` com retornos `OK()` / `FAIL()`
- Actions sao auto-descobertas a partir da pasta `use_cases/`
