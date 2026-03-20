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
├── cli.py                      # Entry point (rpa-cli)
├── rpa_self_healing/           # Motor central
│   ├── config.py               # Settings (.env)
│   ├── domain/                 # Entidades + interfaces (zero deps)
│   ├── application/            # LocatorHealer, FlowHealer, HealingOrchestrator
│   └── infrastructure/         # Driver, LLM, Cache, Git, Logging
├── bots/                       # Bots independentes
│   ├── base.py                 # BaseBot + @action decorator
│   ├── registry.py             # Auto-discovery
│   ├── _template/              # Template para novos bots
│   └── expandtesting/          # Bot de demo
├── tests/                      # 38 testes unitarios
└── docs/                       # Skills + super prompt
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

# Observabilidade
uv run rpa-cli --healing-stats
uv run rpa-cli --cache-stats
uv run rpa-cli --cache-clear

# Debug (browser visivel)
uv run rpa-cli expandtesting demo-healing --headless false
```

## Criar um Novo Bot

```bash
# 1. Copiar template
cp -r bots/_template/ bots/meu_bot/
```

```python
# 2. bots/meu_bot/__init__.py
from bots.base import BaseBot, action

class MeuBot(BaseBot):
    name = "meu_bot"
    description = "Descricao do bot"
    url = "https://sistema.com"

    @action("minha-action")
    async def _minha_action(self, **kwargs) -> dict:
        from bots.meu_bot.use_cases.minha_action_uc import MinhaActionUC
        return await MinhaActionUC(self._driver).execute(**kwargs)

BOT_CLASS = MeuBot  # Obrigatorio para auto-discovery
```

```python
# 3. bots/meu_bot/selectors.py
CAMPO_PRINCIPAL: str = "[name='campo']"
BOTAO_CONFIRMAR: str = "button:has-text('Confirmar')"
```

```python
# 4. bots/meu_bot/use_cases/minha_action_uc.py
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker
import bots.meu_bot.selectors as sel

class MinhaActionUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        with TransactionTracker(bot_name="meu_bot", action="minha-action") as tracker:
            await self._driver.goto("https://sistema.com")
            await self._driver.fill("CAMPO_PRINCIPAL", sel.CAMPO_PRINCIPAL, "valor")
            await self._driver.click("BOTAO_CONFIRMAR", sel.BOTAO_CONFIRMAR)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO}
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

- **Super Prompt**: `docs/instrucoes.md` — Recria o projeto do zero
- **Skills (regras obrigatorias)**: `docs/skills/*.md` — 9 arquivos de referencia
- **Memoria de IA**: As skills sao lidas pela IA antes de qualquer modificacao

## Stack

- Python 3.11+ / UV / hatchling
- Playwright (async)
- OpenRouter + Anthropic + Ollama (LLM)
- gitpython / Loguru / Rich
- pytest + pytest-asyncio / Ruff

## Licenca

Criado por Tiago Pereira Ramos — Self-Healing RPA v3.0
