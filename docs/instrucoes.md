# Super Prompt: Self-Healing RPA — Framework Multi-RPA Self-Healing com Playwright e IA

**Versao 3.0 — Atualizado em 24 de Marco de 2026**
Criado por Tiago Pereira Ramos — Baseado em pesquisa aplicada de Self-Healing Automation 2025/2026

---

## 1. Visao Geral do Projeto

Self-Healing RPA e um framework Python para Automacao de Processos Roboticos (RPA) com:

- **Multi-bot** — N bots independentes, cada um com seletores proprios
- **Self-Healing em dois niveis** — Locator Healing (seletor quebrou) + Flow Healing (logica quebrou) com LLM multi-provider
- **Deteccao Proativa** — detecta iminencia de falha antes de ocorrer, via DOM monitoring
- **Cache Persistente de Reparos** — reparos sao reutilizados sem custo de inferencia
- **CLI unificado (rpa-cli)** — auto-discovery de bots e acoes via `@action` decorator
- **Clean Architecture rigorosa** — Domain / Application / Infrastructure / Bots
- **Page Object Model** — seletores isolados em `selectors.py` por bot
- **UV + pyproject.toml** — zero pip, zero requirements.txt
- **Git Auto-Commit** — seletores curados sao versionados automaticamente
- **Observabilidade de Healing** — metricas de custo, taxa de sucesso, cache hits

---

## 2. Stack Tecnologica

| Componente         | Tecnologia                                    |
| ------------------ | --------------------------------------------- |
| Runtime            | Python 3.11+                                  |
| Gerenciador        | UV (PEP 517, hatchling)                       |
| Browser            | Playwright (async)                            |
| LLM Principal      | OpenRouter (SDK OpenAI-compat)                |
| LLM Alternativo    | Anthropic SDK direto                          |
| LLM Local (offline)| Ollama (llama3.3)                             |
| Cache              | JSON persistente (Redis opcional)             |
| Git                | gitpython                                     |
| Logging            | Loguru + JSONL TransactionTracker             |
| Testes             | pytest + pytest-asyncio (`asyncio_mode=auto`) |
| Linting            | Ruff (`py311`, line-length 120)               |
| Demo Bot           | expandtesting.com/login                       |

---

## 3. Skills Obrigatorias — Base de Conhecimento

A IA DEVE LER OS 9 ARQUIVOS ABAIXO ANTES DE QUALQUER MODIFICACAO:

```
docs/skills/
├── boas_praticas-1.md          # Convencoes de codigo, tipagem, logging
├── cli_e_roteamento-2.md       # CLI dinamico, @action, registry
├── git_e_self_healing-3.md     # Git auto-commit, SelectorRepository
├── logging_tracker-4.md        # TransactionTracker, @tracked, JSONL
├── playwright_self_healing-5.md # Driver, HealingOrchestrator, 2 niveis
├── rpa_development-6.md        # Como criar bots, BaseBot, use cases
├── llm_providers-7.md          # LLMRouter, providers, prompts
├── cache_e_memoria-8.md        # RepairCache, regra de ouro, singleton
└── observabilidade-9.md        # HealingStats, metricas, relatorios
```

---

## 4. Regras Criticas (Resumo das Skills)

| Regra       | Obrigatorio                                | Proibido                                    |
| ----------- | ------------------------------------------ | ------------------------------------------- |
| UV          | `uv sync --extra dev`                      | `pip install`, `requirements.txt`           |
| Playwright  | `driver.click("LABEL", sel.LABEL)`         | `async_playwright()` direto                 |
| Logging     | `with TransactionTracker(...)`             | `print()`                                   |
| CLI         | Receber `**kwargs` nos bots                | Modificar `cli.py`                          |
| Git         | Nunca alterar SelectorRepository           | Trocar regex por AST                        |
| Bots        | `BOT_CLASS = MinhaClasse` + `@action`      | Seletores hardcodados                       |
| LLM         | Usar `LLMRouter` centralizado              | Instanciar cliente LLM direto no bot        |
| Cache       | Consultar `RepairCache` antes de healing   | Chamar LLM sem checar cache                 |
| Healing     | Nivel 1 (locator) antes de Nivel 2 (flow)  | Pular para flow sem tentar locator          |
| Custo       | Logar tokens consumidos em cada healing    | Ignorar custo de inferencia                 |
| Tipos       | `StrEnum`, dataclasses, `str | None`       | `datetime.utcnow()`                        |
| Imports     | `from __future__ import annotations`       | Imports circulares                          |

---

## 5. Arquitetura de Self-Healing (MAPE-K Loop)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAPE-K Self-Healing Loop                     │
│                                                                 │
│  Monitor → Detect → Analyze → Plan → Execute → Learn           │
│                                                                 │
│  ┌──────────┐  sucesso  ┌───────────────────────────────────┐  │
│  │Playwright│ ────────► │      Step Concluido               │  │
│  │ Driver   │           └───────────────────────────────────┘  │
│  │(codigo   │  falha                                           │
│  │determi-  │ ────────► ┌─────────────────────────────────┐   │
│  │nistico)  │           │  HealingOrchestrator (central)  │   │
│  └──────────┘           │                                 │   │
│       ▲                 │  1. Cache check (obrigatorio)   │   │
│       │                 │     ↓ miss                      │   │
│       │                 │  2. NIVEL 1 — LocatorHealer     │   │
│       │                 │     • LLM Haiku → novo seletor  │   │
│       │                 │     • validate(count() > 0)     │   │
│       │                 │     • retry × MAX_ATTEMPTS      │   │
│       │                 │     ↓ falha                     │   │
│       │                 │  3. NIVEL 2 — FlowHealer        │   │
│       │  codigo curado  │     • LLM Sonnet → reescrita   │   │
│       └──────────────── │     • _exec_sandboxed(code)    │   │
│                         │     • cache de fluxo           │   │
│                         └─────────────────────────────────┘   │
│                                       ↑                        │
│                            RepairCache (JSON/Redis)            │
│                         (consulta ANTES de chamar LLM)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Estrutura de Arquivos do Projeto

```
self_healing_rpa/
├── pyproject.toml                # UV + hatchling, deps, scripts, ruff
├── .env.example                  # Template de variaveis de ambiente
├── .env                          # NUNCA versionar
├── README.md                     # Manual do framework
│
├── docs/
│   ├── instrucoes.md             # Super prompt (este arquivo)
│   └── skills/                   # 9 skills obrigatorias
│       ├── boas_praticas-1.md
│       ├── cli_e_roteamento-2.md
│       ├── git_e_self_healing-3.md
│       ├── logging_tracker-4.md
│       ├── playwright_self_healing-5.md
│       ├── rpa_development-6.md
│       ├── llm_providers-7.md
│       ├── cache_e_memoria-8.md
│       └── observabilidade-9.md
│
├── cli.py                        # Entry point do rpa-cli (NUNCA modificar para acoes)
│
├── rpa_self_healing/             # Motor central (NUNCA logica de bot aqui)
│   ├── __init__.py               # from rpa_self_healing.config import settings
│   ├── config.py                 # Settings (instancia attrs no __init__)
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities.py           # HealingLevel, ActionStatus, HealingEvent,
│   │   │                         # HealingResult, RepairRecord, FlowRepairRecord,
│   │   │                         # HealingStats (com to_dict())
│   │   └── interfaces.py        # ILLMProvider, IRepairCache (ABCs)
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── locator_healer.py     # Nivel 1: suggest() — puro LLM caller
│   │   ├── flow_healer.py        # Nivel 2: suggest() — puro LLM caller
│   │   └── healing_orchestrator.py  # Coordenador central MAPE-K
│   │
│   └── infrastructure/
│       ├── __init__.py
│       ├── driver/
│       │   ├── __init__.py
│       │   ├── playwright_driver.py   # PlaywrightDriver (async context manager)
│       │   └── context_capture.py     # DOM, a11y tree, screenshot, elementos
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── llm_router.py          # Multi-provider com fallback chain
│       │   ├── openrouter_provider.py  # OpenAI-compat SDK
│       │   ├── anthropic_provider.py   # Anthropic SDK direto
│       │   └── ollama_provider.py      # Fallback offline
│       ├── cache/
│       │   ├── __init__.py
│       │   └── repair_cache.py        # JSON persistente + singleton
│       ├── git/
│       │   ├── __init__.py
│       │   ├── git_service.py         # Auto-commit de seletores curados
│       │   └── selector_repository.py # Regex para editar selectors.py
│       └── logging/
│           ├── __init__.py
│           └── rpa_logger.py          # Loguru config + TransactionTracker + @tracked
│
├── bots/
│   ├── base.py                   # BaseBot + @action decorator + get_actions()
│   ├── registry.py               # Auto-discovery de bots (importlib)
│   │
│   ├── _template/                # Template para novos bots (BOT_CLASS omitido)
│   │   ├── __init__.py
│   │   ├── selectors.py
│   │   └── use_cases/
│   │       ├── __init__.py
│   │       └── exemplo_uc.py
│   │
│   ├── expandtesting/            # Bot de DEMO (Self-Healing showcase)
│   │   ├── __init__.py           # ExpandTestingBot com @action
│   │   ├── selectors.py          # Seletores reais + variantes quebradas
│   │   └── use_cases/
│   │       ├── __init__.py
│   │       ├── login_uc.py
│   │       ├── login_invalido_uc.py
│   │       └── demo_healing_uc.py
│   │
│   └── tjms/                     # Bot exemplo (TJMS)
│       ├── __init__.py
│       ├── selectors.py
│       └── use_cases/
│           ├── __init__.py
│           └── consultar_processo_uc.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # _stub_env fixture (monkeypatch + reset singleton)
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py             # 5 testes (env vars, bool/int, isolamento)
│   │   ├── test_repair_cache.py       # 10 testes (CRUD, stats, clear, singleton)
│   │   ├── test_locator_healer.py     # 3 testes (suggest, vazio, params)
│   │   ├── test_flow_healer.py        # 3 testes (suggest, vazio, params)
│   │   ├── test_healing_orchestrator.py # 8 testes (cache, healing, escalacao)
│   │   ├── test_selector_repository.py  # 6 testes (update, preserva, healing date)
│   │   └── test_llm_router.py         # 3 testes (no providers, fallback, all fail)
│   └── integration/
│       └── __init__.py
│
└── logs/                         # Auto-criado em runtime
    ├── rpa.log
    ├── rpa_transactions.jsonl
    ├── healing_events.jsonl
    └── screenshots/
```

---

## 7. Codigo-Fonte Completo

### 7.1 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "self-healing-rpa"
version = "3.0.0"
description = "Framework Multi-RPA Self-Healing com Playwright e IA"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.44.0",
    "openai>=1.30.0",
    "anthropic>=0.25.0",
    "gitpython>=3.1.43",
    "loguru>=0.7.2",
    "python-dotenv>=1.0.1",
    "rich>=13.7.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.7",
    "pytest-mock>=3.14.0",
    "ruff>=0.4.0",
]

[project.scripts]
rpa-cli = "cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["rpa_self_healing", "bots"]

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

### 7.2 .env.example

```env
# === LLM Providers ===
OPENROUTER_API_KEY=sk-or-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434

# === Estrategia LLM ===
LLM_PROVIDER=openrouter
LLM_LOCATOR_MODEL=anthropic/claude-haiku-4-5
LLM_FLOW_MODEL=anthropic/claude-sonnet-4-5
LLM_FALLBACK_MODEL=ollama/llama3.3
LLM_MAX_HEALING_ATTEMPTS=2

# === Git ===
GIT_AUTO_COMMIT=true
GIT_AUTO_PUSH=false

# === Cache ===
CACHE_BACKEND=json
CACHE_FILE=rpa_self_healing/infrastructure/cache/repair_cache.json
REDIS_URL=redis://localhost:6379/0

# === Playwright ===
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO=300
PLAYWRIGHT_TIMEOUT=10000
PLAYWRIGHT_HEALING_TIMEOUT=20000

# === Logging ===
LOG_LEVEL=INFO
LOG_DIR=logs/
SCREENSHOT_ON_FAILURE=true
```

### 7.3 rpa_self_healing/config.py

```python
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent


class Settings:
    """Configuracoes centrais do framework, lidas do .env.

    Instanciada uma unica vez como singleton (settings).
    Em testes, crie uma nova instancia apos monkeypatch.setenv().
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
```

**Decisao arquitetural**: Atributos de instancia no `__init__` (nao class-level) para permitir isolamento em testes via `monkeypatch.setattr("rpa_self_healing.config.settings", Settings())` sem `importlib.reload()`.

### 7.4 rpa_self_healing/domain/entities.py

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class HealingLevel(StrEnum):
    """Nivel de healing aplicado pelo framework."""
    LOCATOR = "LOCATOR"
    FLOW = "FLOW"
    PROACTIVE = "PROACTIVE"


class ActionStatus(StrEnum):
    """Status padrao de retorno de actions dos bots."""
    SUCESSO = "sucesso"
    ERRO_LOGICO = "erro_logico"
    ERRO_TECNICO = "erro_tecnico"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HealingEvent:
    """Registro de um evento de healing para logs e observabilidade."""
    bot: str
    selector_label: str
    broken_selector: str
    healed_selector: str | None = None
    healing_level: HealingLevel = HealingLevel.LOCATOR
    llm_provider: str = ""
    llm_model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    from_cache: bool = False
    confidence: float = 0.0
    duration_ms: int = 0
    success: bool = False
    ts: str = field(default_factory=_now_iso)


@dataclass
class HealingResult:
    """Resultado de uma tentativa de healing retornado pelo HealingOrchestrator."""
    success: bool
    selector: str | None = None
    code: str | None = None
    level: HealingLevel = HealingLevel.LOCATOR
    from_cache: bool = False
    event: HealingEvent | None = None


@dataclass
class RepairRecord:
    healed: str
    bot: str
    healed_at: str
    hit_count: int = 0
    last_hit: str = ""
    confidence: float = 0.0


@dataclass
class FlowRepairRecord:
    healed_code: str
    healed_at: str
    hit_count: int = 0


@dataclass
class HealingStats:
    """Metricas acumuladas de healing durante uma sessao."""
    session_id: str
    bot: str
    healing_attempts: int = 0
    healing_successes: int = 0
    healing_failures: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    level1_used: int = 0
    level2_used: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_healing_ms: int = 0
    git_commits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "bot": self.bot,
            "healing_attempts": self.healing_attempts,
            "healing_successes": self.healing_successes,
            "healing_failures": self.healing_failures,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "level1_used": self.level1_used,
            "level2_used": self.level2_used,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_usd": self.total_cost_usd,
            "total_healing_ms": self.total_healing_ms,
            "git_commits": self.git_commits,
        }
```

### 7.5 rpa_self_healing/domain/interfaces.py

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ILLMProvider(ABC):
    """Contrato para providers de LLM (OpenRouter, Anthropic, Ollama)."""

    @abstractmethod
    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        """Retorna {"content": str, "tokens_in": int, "tokens_out": int, "cost_usd": float}."""


class IRepairCache(ABC):
    """Contrato para cache persistente de reparos."""

    @abstractmethod
    def get_locator(self, label: str, broken: str) -> str | None: ...

    @abstractmethod
    def set_locator(self, label: str, broken: str, healed: str, bot_name: str, confidence: float = 0.0) -> None: ...

    @abstractmethod
    def get_flow(self, step_name: str, bot_name: str) -> str | None: ...

    @abstractmethod
    def set_flow(self, step_name: str, bot_name: str, healed_code: str) -> None: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def clear(self, bot_name: str | None = None) -> None: ...
```

### 7.6 rpa_self_healing/application/locator_healer.py

```python
from __future__ import annotations

from typing import Any


class LocatorHealer:
    """Nivel 1 — sugere seletor CSS alternativo via LLM.

    NAO faz: cache, validacao de count(), git commit, stats.
    Isso e responsabilidade do HealingOrchestrator.
    """

    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(
        self,
        broken_selector: str,
        label: str,
        page_ctx: dict[str, Any],
        error: str = "",
    ) -> dict[str, Any]:
        result = await self._llm.heal_locator(
            broken_selector=broken_selector,
            intent=f"executar {label}",
            context=page_ctx,
            error=error,
        )
        new_selector = result.get("content", "").strip()
        return {
            "selector": new_selector or None,
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            "confidence": result.get("confidence", 0.9),
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
        }
```

### 7.7 rpa_self_healing/application/flow_healer.py

```python
from __future__ import annotations

from typing import Any


class FlowHealer:
    """Nivel 2 — reescreve bloco de codigo Playwright via LLM.

    NAO faz: cache, execucao do codigo, stats.
    Isso e responsabilidade do HealingOrchestrator e PlaywrightDriver.
    """

    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(
        self,
        step_name: str,
        failed_code: str,
        error: str,
        page_ctx: dict[str, Any],
    ) -> dict[str, Any]:
        result = await self._llm.heal_flow(
            step_name=step_name,
            failed_code=failed_code,
            error=error,
            context=page_ctx,
        )
        code = result.get("content", "").strip()
        return {
            "code": code or None,
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "cost_usd": result.get("cost_usd", 0.0),
            "model": result.get("model", ""),
            "provider": result.get("provider", ""),
        }
```

### 7.8 rpa_self_healing/application/healing_orchestrator.py

```python
from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.entities import (
    HealingEvent,
    HealingLevel,
    HealingResult,
    HealingStats,
)
from rpa_self_healing.infrastructure.logging.rpa_logger import log_healing_event


class HealingOrchestrator:
    """Coordena o fluxo completo de self-healing: cache -> Nivel 1 -> Nivel 2.

    Fluxo MAPE-K:
        Monitor  -> detecta falha (excecao Playwright) ou proativa
        Analyze  -> consulta cache + captura contexto da pagina
        Plan     -> decide nivel 1 (seletor) ou nivel 2 (reescrita de codigo)
        Execute  -> chama LLM via LocatorHealer/FlowHealer, valida resultado
        Knowledge -> persiste no RepairCache, loga evento

    Nunca instancie esta classe em bots — ela e gerenciada pelo PlaywrightDriver.
    """

    def __init__(self, bot_name: str) -> None:
        self._bot_name = bot_name
        self._stats = HealingStats(session_id=str(uuid.uuid4()), bot=bot_name)
        # Lazy-init de infraestrutura (so criados na 1a chamada de healing)
        self._cache = None
        self._locator = None
        self._flow = None

    def _ensure_ready(self) -> None:
        """Inicializa cache, LLM e healers sob demanda."""
        if self._cache is not None:
            return
        from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache
        from rpa_self_healing.infrastructure.llm.llm_router import LLMRouter
        from rpa_self_healing.application.locator_healer import LocatorHealer
        from rpa_self_healing.application.flow_healer import FlowHealer

        self._cache = RepairCache.get_instance()
        llm = LLMRouter()
        self._locator = LocatorHealer(llm)
        self._flow = FlowHealer(llm)

    @property
    def stats(self) -> HealingStats:
        return self._stats

    async def heal(
        self,
        label: str,
        broken_selector: str,
        page_ctx: dict[str, Any],
        error: str,
        validate: Callable[[str], Awaitable[bool]],
        failed_code: str = "",
    ) -> HealingResult:
        """Tenta curar um seletor quebrado: cache -> Nivel 1 -> Nivel 2."""
        self._ensure_ready()
        t0 = time.monotonic()

        # Nivel 1: Locator Healing
        self._stats.healing_attempts += 1
        self._stats.level1_used += 1

        # 1. Cache (obrigatorio — skill-8)
        cached = self._cache.get_locator(label, broken_selector)
        if cached:
            self._stats.cache_hits += 1
            if await validate(cached):
                return self._locator_success(
                    label, broken_selector, cached, t0, from_cache=True,
                )
        else:
            self._stats.cache_misses += 1

        # 2. LLM com retries
        for _ in range(settings.LLM_MAX_HEALING_ATTEMPTS):
            suggestion = await self._locator.suggest(
                broken_selector=broken_selector,
                label=label,
                page_ctx=page_ctx,
                error=error,
            )
            self._track_tokens(suggestion)

            new_selector = suggestion.get("selector")
            if new_selector and await validate(new_selector):
                self._cache.set_locator(
                    label, broken_selector, new_selector,
                    self._bot_name, suggestion.get("confidence", 0.9),
                )
                return self._locator_success(
                    label, broken_selector, new_selector, t0,
                    suggestion=suggestion,
                )

        # Nivel 2: Flow Healing (escalacao)
        logger.warning(
            f"[FLOW] Escalando para Flow Healing — '{label}' "
            f"falhou {settings.LLM_MAX_HEALING_ATTEMPTS}x no Nivel 1"
        )
        self._stats.level2_used += 1
        return await self._try_flow(label, failed_code, error, page_ctx, t0)

    async def heal_flow_direct(
        self,
        label: str,
        failed_code: str,
        error: str,
        page_ctx: dict[str, Any],
    ) -> HealingResult:
        """Forca Flow Healing (Nivel 2) diretamente, sem tentar Nivel 1."""
        self._ensure_ready()
        self._stats.healing_attempts += 1
        self._stats.level2_used += 1
        return await self._try_flow(label, failed_code, error, page_ctx, time.monotonic())

    # helpers internos (ver codigo-fonte completo para detalhes)
    # _try_flow(), _locator_success(), _track_tokens()
```

**Decisao arquitetural**: O `HealingOrchestrator` e o unico dono de cache check, retry logic, stats tracking e escalacao. `LocatorHealer` e `FlowHealer` sao puros LLM callers.

### 7.9 rpa_self_healing/infrastructure/driver/playwright_driver.py

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from rpa_self_healing.config import settings
from rpa_self_healing.domain.entities import HealingLevel, HealingStats
from rpa_self_healing.infrastructure.driver.context_capture import capture_context
from rpa_self_healing.infrastructure.git.git_service import GitService
from rpa_self_healing.infrastructure.git.selector_repository import SelectorRepository


class PlaywrightDriver:
    """Driver Playwright com self-healing integrado em dois niveis.

    Uso:
        async with PlaywrightDriver(
            selectors_file=Path("bots/mybot/selectors.py"),
            bot_name="mybot",
        ) as driver:
            await driver.goto("https://example.com")
            await driver.click("BUTTON", sel.BUTTON)

    NUNCA instancie async_playwright() diretamente em bots ou use cases.
    """

    def __init__(
        self,
        selectors_file: Path | None = None,
        bot_name: str = "unknown",
        headless: bool | None = None,
    ) -> None:
        self._selectors_file = selectors_file
        self._bot_name = bot_name
        self._headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self._pw = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        # Healing: lazy-init (so criado na 1a falha)
        self._orchestrator = None
        self._git = GitService()
        self._selector_repo = SelectorRepository()

    async def __aenter__(self) -> PlaywrightDriver:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            slow_mo=settings.PLAYWRIGHT_SLOW_MO,
        )
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._page.set_default_timeout(settings.PLAYWRIGHT_TIMEOUT)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @property
    def page(self) -> Page:
        assert self._page is not None, "Driver nao inicializado."
        return self._page

    # API publica
    async def goto(self, url: str) -> None: ...
    async def click(self, label: str, selector: str, force_flow_heal: bool = False) -> None: ...
    async def fill(self, label: str, selector: str, value: str) -> None: ...
    async def get_text(self, label: str, selector: str) -> str: ...
    async def wait_for(self, label: str, selector: str) -> None: ...
    async def is_visible(self, selector: str, heal: bool = False) -> bool: ...
    async def detect_broken_selectors(self, pairs: list[tuple[str, str]]) -> list[tuple[str, str]]: ...
    async def heal_proactive(self, broken: list[tuple[str, str]]) -> None: ...
    def get_healing_stats(self) -> dict[str, Any]: ...

    # _exec_sandboxed: wraps LLM code in async def __heal__() for await support
    async def _exec_sandboxed(self, code: str, **kwargs: Any) -> Any:
        local_vars: dict[str, Any] = {"page": self.page, **kwargs}
        lines = "\n".join(f"    {line}" for line in code.strip().splitlines())
        fn_code = f"async def __heal__():\n{lines}"
        exec(compile(fn_code, "<healing>", "exec"), local_vars)
        return await local_vars["__heal__"]()

    def _get_orchestrator(self):
        if self._orchestrator is None:
            from rpa_self_healing.application.healing_orchestrator import HealingOrchestrator
            self._orchestrator = HealingOrchestrator(bot_name=self._bot_name)
        return self._orchestrator
```

**Decisao arquitetural**: O driver delega TODO healing ao `HealingOrchestrator`. `_exec_sandboxed` envolve o codigo em `async def __heal__():` para suportar `await` em codigo gerado pelo LLM.

### 7.10 rpa_self_healing/infrastructure/llm/llm_router.py

```python
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider

_LOCATOR_SYSTEM = (
    "Voce e um especialista em automacao web com Playwright.\n"
    "Retorne APENAS o seletor CSS mais adequado. Sem explicacoes. Sem markdown.\n"
    "Prioridade: aria-label > data-testid > id > name > role+texto > CSS class"
)

_FLOW_SYSTEM = (
    "Voce e especialista em Playwright Python async.\n"
    "Retorne APENAS codigo Python valido. Sem markdown. Sem explicacoes.\n"
    "O codigo sera executado via exec() em contexto de automacao.\n"
    "Use apenas: page.click(), page.fill(), page.wait_for_selector(), "
    "page.locator(), page.goto(). Nunca use imports dentro do codigo."
)


class LLMRouter:
    """Central LLM router: OpenRouter -> Anthropic -> Ollama."""

    def __init__(self) -> None:
        self._providers: list[tuple[str, ILLMProvider]] = self._build_chain()

    def _build_chain(self) -> list[tuple[str, ILLMProvider]]:
        chain: list[tuple[str, ILLMProvider]] = []
        provider = settings.LLM_PROVIDER.lower()
        if provider == "openrouter" and settings.OPENROUTER_API_KEY:
            from rpa_self_healing.infrastructure.llm.openrouter_provider import OpenRouterProvider
            chain.append(("openrouter", OpenRouterProvider()))
        if settings.ANTHROPIC_API_KEY:
            from rpa_self_healing.infrastructure.llm.anthropic_provider import AnthropicProvider
            chain.append(("anthropic", AnthropicProvider()))
        from rpa_self_healing.infrastructure.llm.ollama_provider import OllamaProvider
        chain.append(("ollama", OllamaProvider()))
        if not chain:
            raise RuntimeError("Nenhum LLM provider disponivel.")
        return chain

    async def _call(self, system: str, user: str, model: str) -> dict[str, Any]:
        last_err: Exception | None = None
        for name, provider in self._providers:
            try:
                return await provider.complete(system, user, model)
            except Exception as exc:
                logger.warning(f"[LLM] Provider '{name}' falhou: {exc}")
                last_err = exc
        raise RuntimeError(f"Todos os providers LLM falharam. Ultimo erro: {last_err}")

    async def heal_locator(self, broken_selector, intent, context, error="") -> dict[str, Any]:
        # Monta prompt com elementos interativos + a11y tree + URL
        # Chama self._call(_LOCATOR_SYSTEM, user, settings.LLM_LOCATOR_MODEL)
        ...

    async def heal_flow(self, step_name, failed_code, error, context) -> dict[str, Any]:
        # Monta prompt com codigo falho + erro + elementos
        # Chama self._call(_FLOW_SYSTEM, user, settings.LLM_FLOW_MODEL)
        ...
```

### 7.11 rpa_self_healing/infrastructure/cache/repair_cache.py

```python
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import IRepairCache

_COST_PER_TOKEN = 0.00000025


class RepairCache(IRepairCache):
    """Cache persistente (JSON) de seletores e fluxos curados.

    Regra de ouro (skill-8): cache DEVE ser consultado ANTES de qualquer LLM.
    Use RepairCache.get_instance() para obter o singleton.
    Em testes, use RepairCache.reset_instance() para limpar.
    """

    _instance: RepairCache | None = None

    def __init__(self, cache_file: Path | None = None) -> None:
        self._file = cache_file or settings.CACHE_FILE
        self._data: dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> RepairCache:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # Locator cache: key = "{label}|{broken}", value = {healed, bot, healed_at, ...}
    # Flow cache: key = "{bot_name}|{step_name}", value = {healed_code, healed_at, ...}
    # get_stats(): total_entries, total_hits, estimated_savings_usd, most_used_label, top_bot
    # clear(bot_name=None): limpa tudo ou por bot
```

### 7.12 rpa_self_healing/infrastructure/git/selector_repository.py

```python
from __future__ import annotations

import re
from pathlib import Path
from loguru import logger


class SelectorRepository:
    """Updates a bot's selectors.py in-place using Regex.
    Never refactor to use AST or formatters — preserves comments and formatting.
    """

    def update(self, selectors_file: Path, label: str, new_selector: str) -> bool:
        # Regex: ^LABEL\s*:\s*str\s*=\s*['"]value['"]comment$
        # Substitui valor, adiciona/atualiza comentario # Healing: YYYY-MM-DD
        ...
```

### 7.13 rpa_self_healing/infrastructure/git/git_service.py

```python
from __future__ import annotations

from pathlib import Path
from loguru import logger
from rpa_self_healing.config import settings


class GitService:
    """Auto-commits healed selectors.py files.
    Graceful degradation when no .git repository is present.
    GIT_AUTO_PUSH is always False by default.
    """

    def __init__(self) -> None:
        self._repo = self._load_repo()

    def commit_healed_selector(
        self, selectors_file, label, old_selector, new_selector,
        bot_name, healing_level="LOCATOR", llm_model="",
        tokens_in=0, tokens_out=0, confidence=0.0,
    ) -> bool:
        # Commit message: feat(self-healing): Ajustado seletor para '{label}'
        # Inclui: bot, old/new selector, healing level, LLM model, tokens, confidence
        ...
```

### 7.14 rpa_self_healing/infrastructure/logging/rpa_logger.py

```python
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from loguru import logger
from rpa_self_healing.config import settings

# Loguru setup: stderr (colored) + file (rpa.log, 10MB rotation, 7 days)
logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL, ...)
logger.add(settings.LOG_DIR / "rpa.log", level="DEBUG", rotation="10 MB", retention="7 days")


class TransactionTracker:
    """Context manager que rastreia uma transacao RPA para auditoria."""

    def __init__(self, bot_name: str, action: str, item_id: str = "") -> None: ...
    def __enter__(self) -> TransactionTracker: ...
    def __exit__(self, exc_type, exc_val, _tb) -> bool: ...
    def fail(self, msg: str) -> None: ...
    def add_data(self, key: str, value: Any) -> None: ...
    def add_healing_stats(self, stats: dict[str, Any]) -> None: ...

    @property
    def item_id(self) -> str: ...
    @item_id.setter
    def item_id(self, value: str) -> None: ...


def tracked(bot_name: str, action_name: str):
    """Decorator que envolve um use case com TransactionTracker.
    Injeta tracker como kwarg na funcao decorada."""
    ...


def log_healing_event(event: dict[str, Any]) -> None:
    """Appends healing event to healing_events.jsonl."""
    ...
```

### 7.15 rpa_self_healing/infrastructure/driver/context_capture.py

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from rpa_self_healing.config import settings

if TYPE_CHECKING:
    from playwright.async_api import Page


async def capture_context(page: "Page", label: str = "") -> dict[str, Any]:
    """Capture DOM context, accessibility tree, and screenshot for LLM healing.

    Returns:
        url, title, html (50KB max), elements (top 60 interactive),
        accessibility_tree (3000 chars), screenshot_path
    """
    ...
```

### 7.16 rpa_self_healing/infrastructure/llm/openrouter_provider.py

```python
from __future__ import annotations
from typing import Any
from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class OpenRouterProvider(ILLMProvider):
    """Calls OpenRouter using the openai-compatible SDK."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        # Returns: content, tokens_in, tokens_out, cost_usd, provider, model
        ...
```

### 7.17 rpa_self_healing/infrastructure/llm/anthropic_provider.py

```python
from __future__ import annotations
from typing import Any
from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class AnthropicProvider(ILLMProvider):
    """Calls Anthropic SDK directly — fallback when OpenRouter is unavailable."""

    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        model_id = model.split("/")[-1]  # Strip provider prefix
        response = await self._client.messages.create(
            model=model_id, max_tokens=512, system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Returns: content, tokens_in, tokens_out, cost_usd, provider, model
        ...
```

### 7.18 rpa_self_healing/infrastructure/llm/ollama_provider.py

```python
from __future__ import annotations
from typing import Any
from rpa_self_healing.config import settings
from rpa_self_healing.domain.interfaces import ILLMProvider


class OllamaProvider(ILLMProvider):
    """Offline fallback — calls local Ollama instance via openai-compatible API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
        )

    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        model_id = model.split("/")[-1]
        # cost_usd = 0.0 (local model)
        ...
```

### 7.19 bots/base.py

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver


def action(name: str | None = None):
    """Decorator que registra um metodo como action do bot."""
    def decorator(fn: Callable) -> Callable:
        fn._action_name = name or fn.__name__.lstrip("_").replace("_", "-")
        return fn
    return decorator


class BaseBot:
    """Classe base para todos os bots do framework.

    Subclasses DEVEM:
        1. Definir atributos de classe: name, description, url
        2. Decorar actions com @action("nome-da-action")
        3. Expor BOT_CLASS = MinhaClasse no final do modulo
    """

    name: str = ""
    description: str = ""
    url: str = ""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    def get_actions(self) -> dict[str, Callable]:
        """Auto-descobre actions decoradas com @action."""
        actions: dict[str, Callable] = {}
        for attr_name in dir(self):
            if attr_name.startswith("__"):
                continue
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "_action_name"):
                actions[method._action_name] = method
        return actions

    @property
    def selectors_file(self) -> Path:
        import sys
        mod = sys.modules.get(type(self).__module__)
        if mod and mod.__file__:
            return Path(mod.__file__).parent / "selectors.py"
        return Path("selectors.py")
```

### 7.20 bots/registry.py

```python
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
from loguru import logger

_BOTS_DIR = Path(__file__).parent
_registry: dict[str, Any] | None = None


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
        if bot_class is not None:
            bots[bot_dir.name] = bot_class
    return bots


def get_registry() -> dict[str, Any]: ...
def get_bot_class(bot_id: str) -> Any: ...
```

### 7.21 bots/expandtesting/__init__.py (Bot de Demo)

```python
from __future__ import annotations

from bots.base import BaseBot, action

LOGIN_URL = "https://practice.expandtesting.com/login"


class ExpandTestingBot(BaseBot):
    name = "expandtesting"
    description = "Bot de demo — login em practice.expandtesting.com. Demonstra Self-Healing ao vivo."
    url = LOGIN_URL

    @action("login")
    async def _login(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_uc import LoginUC
        return await LoginUC(self._driver).execute(**kwargs)

    @action("login-invalido")
    async def _login_invalido(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_invalido_uc import LoginInvalidoUC
        return await LoginInvalidoUC(self._driver).execute(**kwargs)

    @action("demo-healing")
    async def _demo_healing(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.demo_healing_uc import DemoHealingUC
        return await DemoHealingUC(self._driver).execute(**kwargs)


BOT_CLASS = ExpandTestingBot
```

### 7.22 bots/expandtesting/selectors.py

```python
# Seletores do Bot: ExpandTesting
# Ultima atualizacao: 2026-03-23
# Site: https://practice.expandtesting.com/login
# Self-Healing: Automatico (ver docs/skills/playwright_self_healing-5.md)

# Login page
CAMPO_USERNAME: str = "input#username"
CAMPO_PASSWORD: str = "input#password"
BOTAO_LOGIN:    str = "button[type='submit']"

# Flash messages
FLASH_SUCESSO:  str = "div#flash.flash.success"
FLASH_ERRO:     str = "div#flash.flash.error"
FLASH_MSG:      str = "div#flash"

# Secure area
BOTAO_LOGOUT:   str = "a[href='/logout']"
SECURE_AREA:    str = "h2"

# Seletores QUEBRADOS (para demo de healing)
CAMPO_USERNAME_QUEBRADO: str = "input#username"  # Healing: 2026-03-24
BOTAO_LOGIN_QUEBRADO:    str = "#submit-btn-broken"
```

### 7.23 bots/expandtesting/use_cases/login_uc.py

```python
from __future__ import annotations

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"
VALID_USERNAME = "practice"
VALID_PASSWORD = "SuperSecretPassword!"


class LoginUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, username=VALID_USERNAME, password=VALID_PASSWORD, **kwargs) -> dict:
        with TransactionTracker(bot_name="expandtesting", action="login", item_id=username) as tracker:
            await self._driver.goto(LOGIN_URL)
            await self._driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
            await self._driver.fill("CAMPO_PASSWORD", sel.CAMPO_PASSWORD, password)
            await self._driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

            if await self._driver.is_visible(sel.FLASH_ERRO):
                msg = await self._driver.get_text("FLASH_MSG", sel.FLASH_MSG)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}

            tracker.add_data("redirect_url", self._driver.page.url)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
```

### 7.24 bots/expandtesting/use_cases/demo_healing_uc.py

```python
from __future__ import annotations

from loguru import logger

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"


class DemoHealingUC:
    """Demonstra Self-Healing ao vivo usando seletores propositalmente quebrados."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, nivel: str = "locator", **kwargs) -> dict:
        with TransactionTracker(bot_name="expandtesting", action="demo-healing", item_id=nivel) as tracker:
            await self._driver.goto(LOGIN_URL)

            if nivel in ("locator", "ambos"):
                # Seletor QUEBRADO — healing N1 sera ativado
                await self._driver.fill("CAMPO_USERNAME_QUEBRADO", sel.CAMPO_USERNAME_QUEBRADO, "practice")

            if nivel in ("flow", "ambos"):
                # Forca Flow Healing (Nivel 2)
                await self._driver.click("BOTAO_LOGIN_QUEBRADO", sel.BOTAO_LOGIN_QUEBRADO, force_flow_heal=True)

            stats = self._driver.get_healing_stats()
            tracker.add_healing_stats(stats)
            return {"status": ActionStatus.SUCESSO, "nivel_demonstrado": nivel, "healing_stats": stats}
```

### 7.25 cli.py

```python
from __future__ import annotations

"""rpa-cli — Dynamic dispatcher for Self-Healing RPA framework.

Rules (skill-2):
- Never add add_argument() calls for bot actions.
- All --param values are parsed dynamically and injected as **kwargs.
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


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Uso: rpa-cli [--list | --healing-stats | --cache-stats | --cache-clear | <bot> [<action> [--param val ...]]]")
        sys.exit(0)

    # Global flags: --list, --healing-stats, --cache-stats, --cache-clear
    # Bot routing: bot_id action_name **kwargs
    # headless kwarg popped and handled specially
    ...


if __name__ == "__main__":
    main()
```

### 7.26 tests/conftest.py

```python
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

    from rpa_self_healing.config import Settings
    test_settings = Settings()
    monkeypatch.setattr("rpa_self_healing.config.settings", test_settings)

    from rpa_self_healing.infrastructure.cache.repair_cache import RepairCache
    RepairCache.reset_instance()
```

**Decisao**: `Settings()` usa atributos de instancia, permitindo que `monkeypatch.setattr` substitua o singleton sem `importlib.reload()`.

---

## 8. CLI Unificado — Exemplos de Uso

```bash
# Listar bots registrados
uv run rpa-cli --list

# Login com credenciais validas
uv run rpa-cli expandtesting login

# Login com credenciais customizadas
uv run rpa-cli expandtesting login --username user --password pass

# Demo de self-healing (Nivel 1 — locator)
uv run rpa-cli expandtesting demo-healing --nivel locator

# Demo de self-healing (Nivel 2 — flow)
uv run rpa-cli expandtesting demo-healing --nivel flow

# Demo ambos os niveis
uv run rpa-cli expandtesting demo-healing --nivel ambos

# Relatorio de healings historicos
uv run rpa-cli --healing-stats

# Relatorio de cache (hits, economia)
uv run rpa-cli --cache-stats

# Limpar cache
uv run rpa-cli --cache-clear
uv run rpa-cli --cache-clear --bot expandtesting

# Rodar com browser visivel (debug)
uv run rpa-cli expandtesting demo-healing --headless false

# Help de um bot especifico
uv run rpa-cli expandtesting
```

---

## 9. Setup (Checklist)

```bash
cd self_healing_rpa
uv sync --extra dev
uv run playwright install chromium
cp .env.example .env
# Preencher OPENROUTER_API_KEY ou ANTHROPIC_API_KEY no .env
git init && git add . && git commit -m "feat: init self_healing_rpa v3.0"
uv run pytest tests/ -v                              # 38 testes passando
uv run rpa-cli --list                                # expandtesting + tjms
uv run rpa-cli expandtesting demo-healing --nivel locator   # Self-Healing ao vivo
uv run rpa-cli --cache-stats                         # Economia do cache
```

---

## 10. Variaveis de Ambiente (.env.example)

```env
# === LLM Providers ===
OPENROUTER_API_KEY=sk-or-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434

# === Estrategia LLM ===
LLM_PROVIDER=openrouter
LLM_LOCATOR_MODEL=anthropic/claude-haiku-4-5
LLM_FLOW_MODEL=anthropic/claude-sonnet-4-5
LLM_FALLBACK_MODEL=ollama/llama3.3
LLM_MAX_HEALING_ATTEMPTS=2

# === Git ===
GIT_AUTO_COMMIT=true
GIT_AUTO_PUSH=false

# === Cache ===
CACHE_BACKEND=json
CACHE_FILE=rpa_self_healing/infrastructure/cache/repair_cache.json
REDIS_URL=redis://localhost:6379/0

# === Playwright ===
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SLOW_MO=300
PLAYWRIGHT_TIMEOUT=10000
PLAYWRIGHT_HEALING_TIMEOUT=20000

# === Logging ===
LOG_LEVEL=INFO
LOG_DIR=logs/
SCREENSHOT_ON_FAILURE=true
```

---

## 11. Decisoes Arquiteturais Criticas

| Decisao | Motivo |
| ------- | ------ |
| `Settings.__init__` usa atributos de instancia | Testes isolados sem `importlib.reload()` |
| `HealingOrchestrator` e o coordenador central | God Object elimination — Driver delegou toda logica de healing |
| `LocatorHealer.suggest()` e `FlowHealer.suggest()` sao puros LLM callers | Separacao de responsabilidades — sem cache, sem stats |
| `_exec_sandboxed` envolve codigo em `async def __heal__():` | Suporte a `await` em codigo gerado pelo LLM executado via `exec()` |
| `RepairCache.get_instance()` singleton | Compartilhamento entre HealingOrchestrator e CLI sem re-instanciar |
| `@action("name")` decorator | Auto-discovery elimina boilerplate e CLI nunca precisa ser modificado |
| `SelectorRepository` usa Regex | Preservar formatacao e comentarios do selectors.py — AST destruiria |
| Lazy imports dentro de `@action` methods | Evita imports circulares entre bots e infrastructure |
| `validate` callback no orchestrator | Driver fornece `page.locator(sel).count() > 0` sem orquestrador saber de Playwright |

---

## 12. Entregavel Final

Gere todos os arquivos do projeto completos, funcionais e prontos para executar.
Siga rigorosamente a estrutura definida na Secao 6.
Use as skills como regras absolutas — especialmente skill-5 (playwright), skill-7 (llm) e skill-8 (cache).

Apos gerar todos os arquivos, forneca o checklist de setup:

```bash
cd self_healing_rpa
uv sync --extra dev
uv run playwright install chromium
cp .env.example .env
# Preencher OPENROUTER_API_KEY ou ANTHROPIC_API_KEY no .env
git init && git add . && git commit -m "feat: init self_healing_rpa v3.0"
uv run pytest tests/ -v
uv run rpa-cli --list
uv run rpa-cli expandtesting demo-healing --nivel locator
uv run rpa-cli --cache-stats
```
