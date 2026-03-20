---
skill: 5
description: PlaywrightDriver com self-healing em dois niveis e HealingOrchestrator
---

# Skill 5 -- Playwright Driver e Self-Healing

O `PlaywrightDriver` encapsula toda interacao com Playwright e integra
self-healing automatico em dois niveis. Bots NUNCA instanciam `async_playwright()` diretamente.

---

## 1. PlaywrightDriver -- Async Context Manager

**Arquivo:** `rpa_self_healing/infrastructure/driver/playwright_driver.py`

```python
async with PlaywrightDriver(
    selectors_file=Path("bots/mybot/selectors.py"),
    bot_name="mybot",
    headless=None,    # None = usa settings.PLAYWRIGHT_HEADLESS
) as driver:
    await driver.goto("https://example.com")
    await driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)
```

### Construtor

```python
def __init__(
    self,
    selectors_file: Path | None = None,
    bot_name: str = "unknown",
    headless: bool | None = None,
) -> None:
```

- `selectors_file`: caminho para o `selectors.py` do bot (usado para persistencia)
- `bot_name`: identificador do bot (usado em logs, stats, commits)
- `headless`: se `None`, usa `settings.PLAYWRIGHT_HEADLESS` (padrao: `false`)

### Lifecycle

- `__aenter__`: inicia Playwright, lanca Chromium, cria context e page
- `__aexit__`: fecha browser e para Playwright
- Page timeout: `settings.PLAYWRIGHT_TIMEOUT` (padrao: 10000ms)
- Slow motion: `settings.PLAYWRIGHT_SLOW_MO` (padrao: 300ms)

## 2. API Publica

Todas as acoes (exceto `goto` e `is_visible`) passam por `_with_healing()`:

```python
await driver.goto(url)                                    # Navegacao direta, sem healing
await driver.click(label, selector)                       # Clique com healing
await driver.click(label, selector, force_flow_heal=True) # Forca nivel 2 direto
await driver.fill(label, selector, value)                 # Preenchimento com healing
text = await driver.get_text(label, selector)             # Texto com healing
await driver.wait_for(label, selector)                    # Espera com healing
visible = await driver.is_visible(selector)               # NAO ativa healing por padrao
```

### `is_visible()` -- Comportamento Especial

NAO dispara healing por padrao. Retorna `False` em caso de excecao:

```python
async def is_visible(self, selector: str, heal: bool = False) -> bool:
    try:
        return await self.page.locator(selector).is_visible()
    except Exception:
        return False
```

## 3. Mecanismo de Self-Healing -- `_with_healing()`

Todas as acoes passam por este metodo central:

```python
async def _with_healing(self, label, selector, action, force_flow_heal=False, **kwargs):
    if force_flow_heal:
        return await self._force_flow_heal(label, selector, action, **kwargs)
    try:
        return await self._execute_action(selector, action, **kwargs)
    except Exception as exc:
        logger.warning(f"[HEALER] Healing ativado: '{label}' -- {type(exc).__name__}")
        return await self._do_heal(label, selector, action, exc, **kwargs)
```

## 4. Fluxo de `_do_heal()`

Quando uma acao falha:

1. **Obtem/cria HealingOrchestrator** via `_get_orchestrator()` (lazy init)
2. **Captura contexto da pagina** via `capture_context(page, bot_label)`
3. **Define callback de validacao**: `async (sel) -> bool` usando `page.locator(sel).count() > 0`
4. **Chama `orchestrator.heal()`** com label, broken_selector, contexto, erro, validate
5. **Resultado nivel 1** (novo seletor): `_persist_healed_selector()` + re-executa acao
6. **Resultado nivel 2** (codigo): `_exec_sandboxed(code)`
7. **Tudo falha**: re-raise da excecao original

```python
# playwright_driver.py (implementacao real)
async def _do_heal(self, label, selector, action, exc, **kwargs):
    orchestrator = self._get_orchestrator()
    ctx = await capture_context(self.page, f"{self._bot_name}_{label}")
    failed_code = self._build_failed_code(selector, action, **kwargs)

    async def validate(sel: str) -> bool:
        try:
            return await self.page.locator(sel).count() > 0
        except Exception:
            return False

    result = await orchestrator.heal(
        label=label, broken_selector=selector,
        page_ctx=ctx, error=str(exc), validate=validate,
        failed_code=failed_code,
    )

    # Nivel 1: novo seletor
    if result.success and result.selector:
        self._persist_healed_selector(label, selector, result)
        return await self._execute_action(result.selector, action, **kwargs)

    # Nivel 2: codigo reescrito
    if result.success and result.code:
        try:
            return await self._exec_sandboxed(result.code, **kwargs)
        except Exception as flow_exc:
            logger.error(f"[FLOW] Codigo gerado falhou para '{label}': {flow_exc}")

    raise exc  # Healing falhou
```

## 5. `_exec_sandboxed()` -- Execucao de Codigo Gerado

Envolve o codigo do LLM em uma funcao async e executa via `exec()`:

```python
async def _exec_sandboxed(self, code: str, **kwargs: Any) -> Any:
    local_vars: dict[str, Any] = {"page": self.page, **kwargs}
    lines = "\n".join(f"    {line}" for line in code.strip().splitlines())
    fn_code = f"async def __heal__():\n{lines}"
    exec(compile(fn_code, "<healing>", "exec"), local_vars)
    return await local_vars["__heal__"]()
```

O namespace recebe `page` (instancia Playwright) e quaisquer `kwargs` da acao original.

## 6. `force_flow_heal=True`

Pula nivel 1 e vai direto para `orchestrator.heal_flow_direct()`:

```python
# Uso no bot
await driver.click("STEP_COMPLEXO", sel.STEP_COMPLEXO, force_flow_heal=True)
```

```python
# playwright_driver.py
async def _force_flow_heal(self, label, selector, action, **kwargs):
    orchestrator = self._get_orchestrator()
    ctx = await capture_context(self.page, label)
    failed_code = self._build_failed_code(selector, action, **kwargs)

    result = await orchestrator.heal_flow_direct(
        label=label, failed_code=failed_code,
        error="force_flow_heal", page_ctx=ctx,
    )
    if result.success and result.code:
        return await self._exec_sandboxed(result.code, **kwargs)
    raise RuntimeError(f"Flow healing falhou para '{label}'")
```

## 7. Deteccao Proativa

Verifica seletores ANTES de executar acoes:

```python
# Verificar quais seletores estao ausentes
broken = await driver.detect_broken_selectors([
    ("CAMPO_USERNAME", sel.CAMPO_USERNAME),
    ("CAMPO_PASSWORD", sel.CAMPO_PASSWORD),
    ("BOTAO_LOGIN", sel.BOTAO_LOGIN),
])

# Healing preventivo
if broken:
    await driver.heal_proactive(broken)
```

`detect_broken_selectors()` retorna lista de `(label, selector)` onde `locator.count() == 0`.
`heal_proactive()` chama `orchestrator.heal()` para cada seletor ausente e persiste se curado.

## 8. Metricas -- `get_healing_stats()`

Retorna `dict` com metricas da sessao via `orchestrator.stats.to_dict()`:

```python
stats = driver.get_healing_stats()
# Retorna HealingStats.to_dict() se orchestrator foi criado,
# senao retorna stats zerados
```

## 9. Lazy Init do Orchestrator

O `HealingOrchestrator` so e criado na primeira falha:

```python
def _get_orchestrator(self):
    if self._orchestrator is None:
        from rpa_self_healing.application.healing_orchestrator import HealingOrchestrator
        self._orchestrator = HealingOrchestrator(bot_name=self._bot_name)
    return self._orchestrator
```

---

## 10. HealingOrchestrator

**Arquivo:** `rpa_self_healing/application/healing_orchestrator.py`

Coordenador central do self-healing. Gerencia cache, retries, stats e escalacao.

### `heal()` -- Fluxo Completo

```
1. Cache check (RepairCache.get_locator)
   - Hit + valido: retorna imediatamente (sem LLM)
   - Hit + stale: prossegue para LLM
   - Miss: prossegue para LLM

2. Nivel 1 -- LocatorHealer.suggest() x LLM_MAX_HEALING_ATTEMPTS
   - Cada tentativa: chama LLM, valida com callback, salva no cache se valido
   - Se sucesso: retorna HealingResult(selector=...)

3. Nivel 2 -- FlowHealer.suggest() (escalacao)
   - Ativado se nivel 1 falhou em todas as tentativas
   - Flow cache check primeiro
   - Se sucesso: retorna HealingResult(code=...)
   - Se falha: retorna HealingResult(success=False)
```

### `heal_flow_direct()` -- Bypass do Nivel 1

```python
async def heal_flow_direct(self, label, failed_code, error, page_ctx) -> HealingResult:
    """Forca Flow Healing (Nivel 2) diretamente, sem tentar Nivel 1."""
```

### Lazy Init -- `_ensure_ready()`

Infraestrutura criada sob demanda na primeira chamada:

```python
def _ensure_ready(self) -> None:
    if self._cache is not None:
        return
    self._cache = RepairCache.get_instance()
    llm = LLMRouter()
    self._locator = LocatorHealer(llm)
    self._flow = FlowHealer(llm)
```

### Stats

`HealingStats` dataclass com `to_dict()` para serializacao:

```python
@dataclass
class HealingStats:
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
```

### Validate Callback

O callback de validacao e definido pelo `PlaywrightDriver` e passado ao orchestrator:

```python
async def validate(sel: str) -> bool:
    try:
        return await page.locator(sel).count() > 0
    except Exception:
        return False
```

Tipo: `Callable[[str], Awaitable[bool]]`

---

## 11. LocatorHealer -- Nivel 1

**Arquivo:** `rpa_self_healing/application/locator_healer.py`

Chamador puro de LLM para sugestao de seletores. NAO faz cache, validacao, stats ou git.

```python
class LocatorHealer:
    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(self, broken_selector, label, page_ctx, error="") -> dict[str, Any]:
        """Retorna: {"selector": str|None, "tokens_in": ..., "tokens_out": ...,
                     "cost_usd": ..., "confidence": ..., "model": ..., "provider": ...}"""
```

---

## 12. FlowHealer -- Nivel 2

**Arquivo:** `rpa_self_healing/application/flow_healer.py`

Chamador puro de LLM para reescrita de codigo. NAO faz cache, execucao ou stats.

```python
class FlowHealer:
    def __init__(self, llm_router: Any) -> None:
        self._llm = llm_router

    async def suggest(self, step_name, failed_code, error, page_ctx) -> dict[str, Any]:
        """Retorna: {"code": str|None, "tokens_in": ..., "tokens_out": ...,
                     "cost_usd": ..., "model": ..., "provider": ...}"""
```

---

## 13. Regras Proibidas

```python
# NUNCA instanciar Playwright diretamente em bots
async with async_playwright() as p:   # PROIBIDO
    browser = await p.chromium.launch()

# NUNCA hardcodar seletores em bots
await page.click("#btn")              # PROIBIDO

# NUNCA instanciar LLM ou healers em bots
from rpa_self_healing.infrastructure.llm.llm_router import LLMRouter
llm = LLMRouter()                     # PROIBIDO em bots
```
