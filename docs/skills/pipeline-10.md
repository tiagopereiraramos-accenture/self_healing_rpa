---
skill: 10
description: Pipeline declarativo para encadear use cases com branching, forward de dados e error handling
globs: rpa_self_healing/application/pipeline.py
---

# Skill 10 -- Pipeline de Steps

O `Pipeline` orquestra use cases em sequencia, com branching condicional,
forwarding de dados entre steps e error handling centralizado.

---

## 1. Uso Basico

```python
from rpa_self_healing.application.pipeline import Pipeline

result = await Pipeline(self._driver, bot_name="meu_bot") \
    .step("login", LoginUC) \
    .step("coleta", ColetarDadosUC) \
    .step("download", BaixarArquivoUC) \
    .on_error(notificar_erro) \
    .run(username="user", password="pass")
```

O pipeline:
1. Executa cada step na ordem
2. Se um step falha (`ERRO_LOGICO` ou `ERRO_TECNICO`), chama o error handler e para
3. Rastreia tudo via `TransactionTracker` automaticamente
4. Retorna resultado consolidado com metricas

## 2. API Fluent

### `.step(name, uc_class, when=None, forward=None)`

Adiciona um step ao pipeline.

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `name` | `str` | Nome do step (aparece em logs e metricas) |
| `uc_class` | `type` ou `Callable` | Classe UC com `__init__(driver)` e `execute(**kwargs)`, ou funcao decorada com `@use_case` |
| `when` | `Callable` | Condicao: recebe resultado do step anterior, retorna `bool` |
| `forward` | `list[str]` | Chaves do resultado a injetar como kwargs nos steps seguintes |

### `.on_error(handler, stop=True)`

Define handler de erro.

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `handler` | `async (step_name, result, driver)` | Funcao async chamada na falha |
| `stop` | `bool` | `True` (padrao): para o pipeline. `False`: continua |

### `.run(**kwargs)`

Executa todos os steps. Retorna `dict` com resultado consolidado.

## 3. Branching Condicional -- `when`

```python
result = await Pipeline(driver, bot_name="meu_bot") \
    .step("login", LoginUC) \
    .step("admin-panel", AdminPanelUC, when=lambda r: r.get("role") == "admin") \
    .step("coleta", ColetarDadosUC) \
    .run()
```

- Se `when` retorna `False`, o step e **pulado** (nao falha)
- O step pulado aparece no resultado com `{"skipped": True}`
- `when` recebe o `dict` retornado pelo step **anterior**

## 4. Forward de Dados -- `forward`

```python
result = await Pipeline(driver, bot_name="meu_bot") \
    .step("login", LoginUC, forward=["token", "session_id"]) \
    .step("coleta", ColetarDadosUC) \
    .run(username="user")
```

- O step `coleta` recebe `token` e `session_id` como kwargs (alem de `username`)
- So as chaves listadas em `forward` sao passadas adiante
- Kwargs originais do `.run()` sao sempre passados a todos os steps

## 5. Error Handling

```python
async def notificar_erro(step_name: str, result: dict, driver) -> None:
    """Integrar com Slack, Teams, email, etc."""
    await slack.send(f"Pipeline falhou no step '{step_name}': {result.get('msg')}")

result = await Pipeline(driver, bot_name="meu_bot") \
    .step("login", LoginUC) \
    .step("coleta", ColetarDadosUC) \
    .on_error(notificar_erro, stop=True) \
    .run()
```

- `stop=True` (padrao): pipeline para apos erro
- `stop=False`: loga erro e continua para o proximo step
- Excecoes no handler sao capturadas e logadas (nao propagam)
- Excecoes nao tratadas em steps sao convertidas para `ERRO_TECNICO`

## 6. Resultado Consolidado

```python
{
    "status": "sucesso",           # sucesso se zero falhas
    "steps_completed": 3,
    "steps_skipped": 0,
    "steps_failed": 0,
    "steps_total": 3,
    "results": [
        {"step": "login", "status": "sucesso", ...},
        {"step": "coleta", "status": "sucesso", ...},
        {"step": "download", "status": "sucesso", ...},
    ],
    "last_result": {...},          # resultado do ultimo step executado
}
```

## 7. Rastreamento Automatico

O Pipeline cria um `TransactionTracker` automaticamente:
- `action = "pipeline"`
- `item_id = "login|coleta|download"` (nomes dos steps)
- Dados extras: `steps_completed`, `steps_skipped`, `steps_failed`, `steps_total`
- Healing stats: adicionadas automaticamente ao final
- Se um step falha, o tracker registra `erro_logico`

## 8. Exemplo Completo -- Flow do ExpandTesting

```python
# bots/expandtesting/use_cases/flow_completo_uc.py

class FlowCompletoUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        from bots.expandtesting.use_cases.login_uc import LoginUC

        return await Pipeline(self._driver, bot_name="expandtesting") \
            .step("login", LoginUC) \
            .step("verificar-secure", VerificarSecureAreaUC) \
            .step("logout", LogoutUC) \
            .on_error(notificar_erro) \
            .run(**kwargs)
```

```bash
uv run rpa-cli expandtesting flow-completo
uv run rpa-cli expandtesting flow-completo --username practice --password SuperSecretPassword!
```

## 9. Regras

- Cada step e um use case independente (mesma estrutura de `bots/<bot>/use_cases/`)
- O Pipeline vive em `rpa_self_healing/application/pipeline.py`
- NUNCA colocar logica de negocio dentro do Pipeline — ele e apenas orquestrador
- Use cases dentro do pipeline podem ter seus proprios `TransactionTracker` internos
- O self-healing funciona normalmente dentro de cada step

## 10. Compatibilidade com @use_case (v3.2)

O Pipeline aceita tanto classes quanto funcoes decoradas com @use_case:

```python
from rpa_self_healing import use_case, OK

@use_case("meu_bot", "step-a")
async def step_a(driver, **kwargs):
    return OK(valor=42)

@use_case("meu_bot", "step-b")
async def step_b(driver, valor=0, **kwargs):
    return OK(dobro=valor * 2)

result = await Pipeline(driver, bot_name="meu_bot") \
    .step("a", step_a, forward=["valor"]) \
    .step("b", step_b) \
    .run()
```
