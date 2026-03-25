---
skill: 4
description: Logging com Loguru, TransactionTracker e decorator @tracked
---

# Skill 4 -- Logging e TransactionTracker

Todo use case de bot DEVE ser rastreado via `TransactionTracker` ou `@tracked`.
O logging e configurado com Loguru e os eventos sao persistidos em arquivos JSONL.

**Arquivo:** `rpa_self_healing/infrastructure/logging/rpa_logger.py`

---

## 1. Configuracao do Loguru

Duas saidas configuradas automaticamente ao importar o modulo:

```python
# rpa_logger.py (configuracao real)
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,          # Padrao: "INFO" (via .env)
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)
logger.add(
    settings.LOG_DIR / "rpa.log",
    level="DEBUG",                     # Arquivo sempre em DEBUG
    rotation="10 MB",                  # Rotaciona a cada 10MB
    retention="7 days",                # Mantem 7 dias de historico
    encoding="utf-8",
)
```

Diretorios criados automaticamente na inicializacao:

```python
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)           # logs/
(settings.LOG_DIR / "screenshots").mkdir(parents=True, exist_ok=True)  # logs/screenshots/
```

## 2. Arquivos JSONL

Dois arquivos de rastreamento (append-only):

| Arquivo                        | Conteudo                          | Quem escreve          |
| ------------------------------ | --------------------------------- | --------------------- |
| `logs/rpa_transactions.jsonl`  | Auditoria de transacoes RPA       | `TransactionTracker`  |
| `logs/healing_events.jsonl`    | Eventos individuais de healing    | `log_healing_event()` |

```python
# rpa_logger.py
def log_healing_event(event: dict[str, Any]) -> None:
    _append_jsonl(_HEALING_FILE, event)
```

## 3. TransactionTracker -- Context Manager

O `TransactionTracker` e um context manager **sincrono** (nao async):

```python
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

with TransactionTracker(
    bot_name="expandtesting",
    action="login",
    item_id=username,
) as tracker:
    await driver.goto(LOGIN_URL)
    await driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
    await driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

    # Erro logico (credenciais invalidas, dados ausentes, etc.)
    if erro:
        tracker.fail("mensagem de erro")

    # Dados extras para auditoria
    tracker.add_data("redirect_url", driver.page.url)

    # Metricas de healing (chamar no final)
    tracker.add_healing_stats(driver.get_healing_stats())
```

### API Publica

```python
class TransactionTracker:
    def __init__(self, bot_name: str, action: str, item_id: str = "") -> None: ...

    @property
    def item_id(self) -> str: ...       # Getter

    @item_id.setter
    def item_id(self, value: str) -> None: ...  # Setter

    def fail(self, msg: str) -> None:
        """Marca transacao como erro_logico."""

    def add_data(self, key: str, value: Any) -> None:
        """Adiciona dados extras ao registro JSONL."""

    def add_healing_stats(self, stats: dict[str, Any]) -> None:
        """Adiciona metricas de healing ao registro."""
```

### Comportamento do `__exit__`

Ao sair do context manager:

1. Se houve excecao nao tratada: status = `"erro_tecnico"`, loga erro
2. Calcula `duration_ms` com `datetime.now(timezone.utc)`
3. Escreve registro JSONL em `rpa_transactions.jsonl`
4. Se status == `"sucesso"`: loga com `logger.success`
5. Se status == `"erro_logico"`: loga com `logger.warning`
6. Se `_healing_stats` presente: chama `_print_healing_report()`
7. Retorna `False` -- NUNCA suprime excecoes

### Registro JSONL de Transacao

```json
{
  "ts": "2026-03-24T14:23:01+00:00",
  "bot": "expandtesting",
  "action": "login",
  "item_id": "user123",
  "status": "sucesso",
  "msg": "",
  "duration_ms": 3421,
  "redirect_url": "https://example.com/secure",
  "healing": {
    "session_id": "...",
    "bot": "expandtesting",
    "healing_attempts": 1,
    "healing_successes": 1,
    "cache_hits": 0,
    "total_cost_usd": 0.000031,
    "git_commits": 1
  }
}
```

## 4. Healing Report

O metodo `_print_healing_report()` exibe um relatorio formatado via logger
quando existem tentativas de healing na sessao:

```python
# rpa_logger.py (formato real)
def _print_healing_report(self) -> None:
    s = self._healing_stats
    attempts = s.get("healing_attempts", 0)
    if not attempts:
        return
    successes = s.get("healing_successes", 0)
    rate = int(successes / attempts * 100) if attempts else 0
    tokens = s.get("total_tokens_in", 0) + s.get("total_tokens_out", 0)
    cost = s.get("total_cost_usd", 0.0)
    lines = [
        f"{'=' * 55}",
        f"  SELF-HEALING REPORT -- {self._bot_name}",
        f"{'=' * 55}",
        f"  Tentativas de healing:   {attempts}",
        f"  Bem-sucedidos:           {successes}  ({rate}%)",
        f"  Cache hits:              {s.get('cache_hits', 0)}",
        f"  Nivel 1 (locator):       {s.get('level1_used', 0)}",
        f"  Nivel 2 (flow):          {s.get('level2_used', 0)}",
        f"  Tokens consumidos:       {tokens}",
        f"  Custo estimado:          $ {cost:.6f}",
        f"  Commits Git:             {s.get('git_commits', 0)}",
        f"{'=' * 55}",
    ]
    logger.info("\n" + "\n".join(lines))
```

## 5. Decorator `@tracked` -- Alternativa ao Context Manager

O decorator `@tracked` envolve automaticamente o metodo com `TransactionTracker`
e injeta `tracker` como keyword argument:

```python
from rpa_self_healing.infrastructure.logging.rpa_logger import tracked, TransactionTracker

class MeuUseCase:
    @tracked("meu_bot", "minha_action")
    async def execute(self, param1: str = "", tracker: TransactionTracker | None = None, **kwargs) -> dict:
        tracker.item_id = param1
        await self._driver.goto("https://example.com")
        # ...
        tracker.add_data("key", "value")
        tracker.fail("mensagem")  # em caso de erro logico
        return {"status": "sucesso"}
```

### Implementacao Real

```python
# rpa_logger.py
def tracked(bot_name: str, action_name: str):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            with TransactionTracker(bot_name=bot_name, action=action_name) as tracker:
                kwargs["tracker"] = tracker
                result = await fn(self, *args, **kwargs)
                if hasattr(self, "_driver") and self._driver is not None:
                    tracker.add_healing_stats(self._driver.get_healing_stats())
                return result
        return wrapper
    return decorator
```

O decorator:
- Injeta `tracker` como kwarg na funcao decorada
- Adiciona `healing_stats` automaticamente se `self._driver` existir
- Funciona apenas com metodos `async` de classes que possuem `self._driver`

## 6. Decorator @use_case (v3.2 -- Recomendado)

O decorator `@use_case` de `rpa_self_healing/shortcuts.py` e a forma mais simples
de criar um use case com tracking automatico:

```python
from rpa_self_healing import use_case, OK, FAIL

@use_case("meu_bot", "minha-action")
async def minha_action(driver, **kwargs):
    # tracker e injetado automaticamente como kwarg
    tracker = kwargs.get("tracker")
    tracker.item_id = kwargs.get("usuario", "")

    await driver.goto("https://...")
    return OK(url=driver.page.url)
```

Diferenca entre `@tracked`, `@use_case` e `TransactionTracker` manual:

| Feature | TransactionTracker | @tracked | @use_case |
|---------|-------------------|----------|-----------|
| Requer classe | Sim | Sim | Nao |
| Healing stats automatico | Manual | Automatico | Automatico |
| Tracker disponivel | Sim | Via kwarg | Via kwarg |
| Compativel com Pipeline | Sim | Sim | Sim |
| Estilo recomendado | v3.0 | v3.0 | v3.2 |

## 7. Estrutura JSONL de Healing Event

Gerado pelo `HealingOrchestrator` via `log_healing_event(event.__dict__)`:

```json
{
  "bot": "expandtesting",
  "selector_label": "CAMPO_USERNAME",
  "broken_selector": "input#user-name",
  "healed_selector": "input[name='username']",
  "healing_level": "LOCATOR",
  "llm_provider": "openrouter",
  "llm_model": "claude-haiku-4-5",
  "tokens_in": 247,
  "tokens_out": 12,
  "cost_usd": 0.000031,
  "from_cache": false,
  "confidence": 0.94,
  "duration_ms": 1842,
  "success": true,
  "ts": "2026-03-24T14:23:01+00:00"
}
```
