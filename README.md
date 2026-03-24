# Self-Healing RPA — Framework Multi-RPA Self-Healing

Framework Python para Automacao de Processos Roboticos (RPA) com self-healing em dois niveis, alimentado por LLM multi-provider.

## Recursos

- **Self-Healing em 2 niveis**: Nivel 1 (seletor CSS via LLM) + Nivel 2 (reescrita de codigo via LLM)
- **Multi-bot**: N bots independentes com seletores proprios
- **Cache de reparos**: Reutiliza correcoes sem custo de inferencia
- **Git auto-commit**: Seletores curados sao versionados automaticamente
- **CLI dinamico**: `@action` decorator para auto-discovery de acoes
- **Multi-provider LLM**: OpenRouter -> Anthropic -> Ollama (fallback offline)
- **Clean Architecture**: Domain / Application / Infrastructure / Bots
- **Observabilidade**: Metricas de custo, tokens, taxa de sucesso, cache hits
- **Zero Boilerplate (v3.2)**: `@use_case`, `OK()`, `FAIL()`, `@bot`, `scaffold`

## Quick Start

```bash
# 1. Instalar dependencias
uv sync --extra dev

# 2. Instalar Chromium para Playwright
uv run playwright install chromium

# 3. Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com sua OPENROUTER_API_KEY ou ANTHROPIC_API_KEY

# 4. Rodar testes
uv run pytest tests/ -v

# 5. Listar bots disponiveis
uv run rpa-cli --list

# 6. Demo de self-healing ao vivo
uv run rpa-cli expandtesting demo-healing --nivel locator
```

## Criar um Bot em 30 segundos (v3.2)

```bash
# Gerar estrutura completa
uv run rpa-cli scaffold meu_bot --url https://sistema.com --actions login,coleta,download
```

Isso gera automaticamente:

```
bots/meu_bot/
  __init__.py        — @bot decorator (auto-discovery)
  selectors.py       — seletores CSS
  use_cases/
    login_uc.py      — @use_case("meu_bot", "login")
    coleta_uc.py     — @use_case("meu_bot", "coleta")
    download_uc.py   — @use_case("meu_bot", "download")
```

Cada use case gerado usa o estilo zero boilerplate:

```python
from rpa_self_healing import use_case, OK
import bots.meu_bot.selectors as sel

@use_case("meu_bot", "login")
async def login(driver, username="", password="", **kwargs):
    await driver.goto("https://sistema.com")
    await driver.fill("CAMPO_USERNAME", sel.CAMPO_PRINCIPAL, username)
    await driver.click("BOTAO_LOGIN", sel.BOTAO_CONFIRMAR)
    return OK(url=driver.page.url)
```

Sem classes, sem TransactionTracker, sem imports de ActionStatus. O framework cuida de tudo.

## v3.2 vs v3.1 — Comparacao

### Antes (v3.1) — 20 linhas
```python
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker
import bots.meu_bot.selectors as sel

class LoginUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, username="", **kwargs) -> dict:
        with TransactionTracker(bot_name="meu_bot", action="login", item_id=username) as tracker:
            await self._driver.goto("https://...")
            await self._driver.fill("CAMPO", sel.CAMPO, username)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
```

### Depois (v3.2) — 8 linhas
```python
from rpa_self_healing import use_case, OK
import bots.meu_bot.selectors as sel

@use_case("meu_bot", "login")
async def login(driver, username="", **kwargs):
    await driver.goto("https://...")
    await driver.fill("CAMPO", sel.CAMPO, username)
    return OK(url=driver.page.url)
```

**Ambos os estilos funcionam.** O v3.1 classico continua 100% compativel.

## Arquitetura

```
MAPE-K Self-Healing Loop
─────────────────────────
PlaywrightDriver
    ├── sucesso → step concluido
    └── falha → HealingOrchestrator
                    ├── 1. Cache check (obrigatorio)
                    ├── 2. Nivel 1 — LocatorHealer (LLM Haiku)
                    │       └── validate(count() > 0)
                    └── 3. Nivel 2 — FlowHealer (LLM Sonnet)
                            └── _exec_sandboxed(code)
```

## Estrutura do Projeto

```
self_healing_rpa/
├── pyproject.toml              # UV + hatchling
├── cli.py                      # Entry point (rpa-cli) + scaffold
├── rpa_self_healing/           # Motor central
│   ├── config.py               # Settings (.env)
│   ├── shortcuts.py            # OK(), FAIL(), @use_case (v3.2)
│   ├── domain/                 # Entidades + interfaces (zero deps)
│   ├── application/            # LocatorHealer, FlowHealer, HealingOrchestrator, Pipeline
│   └── infrastructure/         # Driver, LLM, Cache, Git, Logging
├── bots/                       # Bots independentes
│   ├── base.py                 # BaseBot + @action + @bot decorator
│   ├── registry.py             # Auto-discovery
│   └── expandtesting/          # Bot de demo
├── tests/                      # 66 testes unitarios
└── docs/                       # Manual + Skills + super prompt
```

## Pipeline (v3.1+)

Encadeie use cases em sequencia com branching condicional:

```python
from rpa_self_healing.application.pipeline import Pipeline

result = await Pipeline(driver, bot_name="meu_bot") \
    .step("login", login) \
    .step("coleta", coletar, when=lambda r: r.get("role") == "admin") \
    .step("download", baixar, forward=["token"]) \
    .on_error(notificar_erro) \
    .run(username="user")
```

Funciona com `@use_case` (v3.2) e com classes (v3.1).

```bash
# Demo do pipeline
uv run rpa-cli expandtesting flow-completo
```

## CLI

```bash
# Bots
uv run rpa-cli --list
uv run rpa-cli expandtesting login
uv run rpa-cli expandtesting login --username user --password pass
uv run rpa-cli expandtesting demo-healing --nivel locator
uv run rpa-cli expandtesting demo-healing --nivel flow
uv run rpa-cli expandtesting demo-healing --nivel ambos

# Scaffold (v3.2)
uv run rpa-cli scaffold meu_bot --url https://sistema.com --actions login,coleta

# Observabilidade
uv run rpa-cli --healing-stats
uv run rpa-cli --cache-stats
uv run rpa-cli --cache-clear

# Debug (browser visivel)
uv run rpa-cli expandtesting demo-healing --headless false
```

## Helpers Rapidos (v3.2)

```python
from rpa_self_healing import OK, FAIL, use_case

# Sucesso
return OK(url="https://...", token="abc")
# => {"status": "sucesso", "url": "https://...", "token": "abc"}

# Erro logico
return FAIL("Credenciais invalidas", tentativas=3)
# => {"status": "erro_logico", "msg": "Credenciais invalidas", "tentativas": 3}
```

## Configuracao (.env)

```env
# LLM
OPENROUTER_API_KEY=sk-or-...
LLM_PROVIDER=openrouter
LLM_LOCATOR_MODEL=anthropic/claude-haiku-4-5
LLM_FLOW_MODEL=anthropic/claude-sonnet-4-5

# Git
GIT_AUTO_COMMIT=true
GIT_AUTO_PUSH=false

# Playwright
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO=300
PLAYWRIGHT_TIMEOUT=10000
```

## Documentacao Completa

- **Manual do Framework**: `docs/manual.md` — Guia completo para iniciantes
- **Super Prompt**: `docs/instrucoes.md` — Recria o projeto do zero
- **Skills (regras obrigatorias)**: `docs/skills/*.md` — 10 arquivos de referencia
- **Memoria de IA**: As skills sao lidas pela IA antes de qualquer modificacao

## Stack

- Python 3.11+ / UV / hatchling
- Playwright (async)
- OpenRouter + Anthropic + Ollama (LLM)
- gitpython / Loguru / Rich
- pytest + pytest-asyncio / Ruff

## Licenca

Criado por Tiago Pereira Ramos — Self-Healing RPA v3.2
