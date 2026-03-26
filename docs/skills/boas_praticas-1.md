---
skill: 1
description: Boas praticas e convencoes obrigatorias para todo codigo no framework Self-Healing RPA
---

# Skill 1 -- Boas Praticas e Convencoes

Regras obrigatorias para qualquer desenvolvedor ou IA que trabalhe neste projeto.
Baseado na implementacao real do framework Self-Healing RPA v3.2.

---

## 1. Python e Gerenciamento de Dependencias

- **Python 3.11+** obrigatorio (`pyproject.toml`: `requires-python = ">=3.11"`)
- **UV exclusivo** -- NUNCA usar `pip install` ou `requirements.txt`
- Build system: **hatchling** (`[build-system] requires = ["hatchling"]`)
- Instalar: `uv sync --extra dev`
- Rodar: `uv run rpa-cli ...` ou `uv run pytest`

```toml
# pyproject.toml (trecho real)
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "self-healing-rpa"
version = "3.2.0"
requires-python = ">=3.11"
```

## 2. Import Obrigatorio

Todo arquivo `.py` do projeto DEVE comecar com:

```python
from __future__ import annotations
```

Sem excecoes. Isso garante avaliacao lazy de type hints e compatibilidade.

## 3. Logging -- Loguru Exclusivo

- **NUNCA** usar `print()` em codigo de producao
- **SEMPRE** usar `from loguru import logger`
- Configuracao centralizada em `rpa_self_healing/infrastructure/logging/rpa_logger.py`

```python
from loguru import logger

logger.info("[DRIVER] goto https://example.com")
logger.warning("[HEALER] Healing ativado")
logger.error("[ERRO] Falha critica")
```

## 4. Enumeracoes -- StrEnum

Todas as enumeracoes usam `StrEnum` (Python 3.11+):

```python
# rpa_self_healing/domain/entities.py
from enum import StrEnum

class HealingLevel(StrEnum):
    LOCATOR = "LOCATOR"
    FLOW = "FLOW"
    PROACTIVE = "PROACTIVE"

class ActionStatus(StrEnum):
    SUCESSO = "sucesso"
    ERRO_LOGICO = "erro_logico"
    ERRO_TECNICO = "erro_tecnico"
```

## 5. Dataclasses para Estruturas de Dados

Entidades do dominio sao `@dataclass`, nunca dicts soltos ou Pydantic:

```python
# rpa_self_healing/domain/entities.py
@dataclass
class HealingEvent:
    bot: str
    selector_label: str
    broken_selector: str
    healed_selector: str | None = None
    healing_level: HealingLevel = HealingLevel.LOCATOR
    # ...

@dataclass
class HealingResult:
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
class HealingStats:
    session_id: str
    bot: str
    healing_attempts: int = 0
    # ... (possui metodo to_dict())
```

## 6. Type Hints -- Convencoes

Usar sintaxe moderna do Python 3.11+. NUNCA importar `Optional`, `List`, `Dict` de `typing`:

```python
# CORRETO
str | None
dict[str, Any]
Path | None
list[tuple[str, str]]
bool | None

# ERRADO -- nunca usar
Optional[str]
Dict[str, Any]
List[Tuple[str, str]]
```

## 7. Datetime -- Timezone-Aware

SEMPRE usar `datetime.now(timezone.utc)`. NUNCA `datetime.utcnow()`:

```python
# rpa_self_healing/domain/entities.py
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

## 8. Arquitetura Clean -- Camadas

```
Domain (entities.py)
  |
Application (healing_orchestrator.py, locator_healer.py, flow_healer.py)
  |
Infrastructure (playwright_driver.py, git_service.py, rpa_logger.py, llm_router.py, repair_cache.py)
  |
Bots (bots/expandtesting/, bots/registry.py)
```

Regras de dependencia:
- **Domain** tem ZERO imports de application ou infrastructure
- **Application** importa apenas domain
- **Infrastructure** importa domain e application
- **Bots** usam infrastructure via injecao (PlaywrightDriver)
- NUNCA instanciar `Playwright`, `LLMRouter`, `RepairCache` ou `GitService` diretamente em bots

## 9. Nomenclatura

| Elemento             | Convencao         | Exemplo                |
| -------------------- | ----------------- | ---------------------- |
| Arquivos             | `snake_case.py`   | `healing_orchestrator.py` |
| Classes              | `PascalCase`      | `PlaywrightDriver`     |
| Seletores            | `UPPER_SNAKE_CASE`| `CAMPO_USERNAME`       |
| Metodos privados     | Prefixo `_`       | `_do_heal()`           |
| Constantes de config | `UPPER_SNAKE_CASE`| `GIT_AUTO_COMMIT`      |

## 10. Testes

- Framework: **pytest** + **pytest-asyncio**
- Modo async: `asyncio_mode = "auto"` (configurado em `pyproject.toml`)
- Diretorio: `tests/` (com subdiretorios `tests/unit/`, etc.)
- Mock: **pytest-mock** (`pytest-mock>=3.14.0`)
- Rodar: `uv run pytest`

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## 11. Linting -- Ruff

Configuracao obrigatoria no `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- `E` = pycodestyle errors
- `F` = pyflakes
- `I` = isort (ordenacao de imports)
- `UP` = pyupgrade (modernizacao de sintaxe)

## 12. Variaveis de Ambiente

- Toda configuracao vem do `.env` via `rpa_self_healing/config.py` (classe `Settings`)
- NUNCA versionar `.env` -- manter `.env.example` atualizado
- Singleton: `from rpa_self_healing.config import settings`

## 13. Async First

- Todo codigo de automacao e `async`/`await`
- NUNCA bloquear o event loop com operacoes sincronas pesadas
- Usar `asyncio.sleep()`, nunca `time.sleep()` em codigo async

## 14. Seguranca (Regras Obrigatorias)

Derivadas de auditoria SAST/DAST/ASA/SCA real. Violacao BLOQUEIA commit.

### SEC-1: Execucao de codigo dinamico
- NUNCA usar `exec()`, `eval()`, `compile()` sem validacao AST previa via `validate_generated_code()` (`rpa_self_healing/domain/code_validator.py`).
- Namespace de execucao DEVE usar `__builtins__: {}`.
- Novos metodos Playwright permitidos: atualizar `_ALLOWED_PAGE_ATTRS` em `code_validator.py`.

### SEC-2: Credenciais e segredos
- PROIBIDO hardcodar credenciais, tokens ou chaves de API.
- Credenciais vem de `os.getenv()` ou secrets manager.
- Nova credencial DEVE ser adicionada ao `.env.example` (sem valor real).
- Falha ao carregar credencial: levantar `EnvironmentError`.

### SEC-3: Dados nao confiaveis (prompt injection)
- Dados de paginas web sao INPUT NAO CONFIAVEL.
- Delimitar com tags XML (`<page_data>...</page_data>`) e truncar (`max_len`).
- NUNCA interpolar dados de usuario em strings executaveis. Usar `repr()`.

### SEC-4: Path traversal e CLI inputs
- Validar inputs de CLI com regex antes de uso.
- Paths de usuario: verificar com `.resolve().relative_to()`.
- Nomes de bots: apenas `[a-z][a-z0-9_]{0,49}`.

### SEC-5: Tratamento de excecoes
- PROIBIDO `except Exception: pass`. Sempre logar.
- PROIBIDO `assert` para verificacoes de seguranca. Usar `if/raise`.

### SEC-6: Rede e URLs externas
- URLs de env validadas: scheme `http`/`https`, host nao em blocklist de metadata.
- Chamadas LLM com timeout explicito (`asyncio.wait_for`, 30s).
- Browser contexts: `accept_downloads=False`, `permissions=[]`, `bypass_csp=False`.

### SEC-7: Cache e integridade
- Codigo do cache DEVE ser re-validado via AST antes de execucao.

### SEC-8: Dependencias
- Usar `~=` (compatible release) no `pyproject.toml`. NUNCA `>=` sem upper bound.
- `pip-audit` no CI.

### SEC-9: Dados sensiveis em logs
- NUNCA logar credenciais, tokens ou passwords.
- Mascarar PII (usernames) com hash parcial.

### SEC-10: Concorrencia
- Singletons com `threading.Lock()`.

## 15. Atalhos v3.2 -- OK / FAIL / @use_case

A partir da v3.2, use cases podem ser criados com decorators em vez de classes:

```python
from rpa_self_healing import use_case, OK, FAIL

@use_case("meu_bot", "minha-action")
async def minha_action(driver, **kwargs):
    return OK(msg="done")
    # ou: return FAIL("erro logico")
```

Ambos os estilos (v3.1 classes e v3.2 decorators) sao validos. Para novos bots, prefira v3.2.
