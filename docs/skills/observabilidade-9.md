---
skill: 9
description: Metricas, logs, eventos de healing e relatorios de observabilidade
globs: rpa_self_healing/infrastructure/logging/**/*.py, rpa_self_healing/domain/entities.py
---

# Skill 9 -- Observabilidade e Metricas

## 1. Tres Fontes de Dados

| Fonte | Formato | Caminho |
|---|---|---|
| Log geral | Loguru plaintext | `logs/rpa.log` |
| Transacoes | JSON Lines | `logs/rpa_transactions.jsonl` |
| Eventos de healing | JSON Lines | `logs/healing_events.jsonl` |

### Configuracao Loguru (`rpa_logger.py`)

```python
# Console (stderr)
logger.add(sys.stderr, level=settings.LOG_LEVEL, colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

# Arquivo
logger.add(settings.LOG_DIR / "rpa.log",
    level="DEBUG", rotation="10 MB", retention="7 days", encoding="utf-8")
```

Screenshots sao salvos em `logs/screenshots/` com formato `{label}_{timestamp}.png`.

## 2. `HealingStats` (dataclass)

Definida em `rpa_self_healing/domain/entities.py`. Acumula metricas de healing durante uma sessao.

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

## 3. `HealingEvent` (dataclass)

Cada evento de healing e registrado em `logs/healing_events.jsonl`:

```python
@dataclass
class HealingEvent:
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
```

Gravacao via `log_healing_event(event.__dict__)` que chama `_append_jsonl()`.

## 4. `TransactionTracker`

Context manager obrigatorio em todo use case. Definido em `rpa_self_healing/infrastructure/logging/rpa_logger.py`.

```python
with TransactionTracker(bot_name="expandtesting", action="login", item_id=username) as tracker:
    # ... interacoes com o driver ...
    tracker.add_healing_stats(self._driver.get_healing_stats())
```

Ao sair do bloco `with`:
- Calcula `duration_ms`
- Grava registro em `logs/rpa_transactions.jsonl` com: ts, bot, action, item_id, status, msg, duration_ms, healing (se presente)
- Se `_healing_stats` estiver presente e houver tentativas, imprime o relatorio de healing

### API publica:

- `tracker.fail(msg)` -- marca como `erro_logico` (NAO levanta excecao)
- `tracker.add_data(key, value)` -- dados extras no registro JSONL
- `tracker.add_healing_stats(stats)` -- metricas de healing para o relatorio

## 5. Relatorio de Healing (automatico)

Impresso pelo `TransactionTracker._print_healing_report()` ao final do use case, se houve healing:

```
=======================================================
  SELF-HEALING REPORT -- expandtesting
=======================================================
  Tentativas de healing:   3
  Bem-sucedidos:           3  (100%)
  Cache hits:              1
  Nivel 1 (locator):       3
  Nivel 2 (flow):          0
  Tokens consumidos:       777
  Custo estimado:          $ 0.000093
  Commits Git:             2
=======================================================
```

## 6. Relatorios via CLI

### `uv run rpa-cli --healing-stats`

Le `logs/healing_events.jsonl` e exibe:
- Total de healings
- Taxa de sucesso (percentual)
- Custo total (USD)
- Cache hits (quantidade)
- Modelo mais usado

```
Periodo: ultimos 7 dias
Total de healings:   23
Taxa de sucesso:     95.6%
Custo total:         $0.0021
Economia por cache:  18 hits
Modelo mais usado:   claude-haiku-4-5
```

### `uv run rpa-cli --cache-stats`

Le o `repair_cache.json` e exibe:
- Entradas no cache
- Total de hits
- Economia estimada (USD)
- Seletor mais reutilizado
- Bot com mais reparos

## 7. Timestamps

Todos os timestamps usam UTC com ISO 8601:

```python
datetime.now(timezone.utc).isoformat()
```

## 8. Enums de Status

```python
class HealingLevel(StrEnum):
    LOCATOR = "LOCATOR"
    FLOW = "FLOW"
    PROACTIVE = "PROACTIVE"

class ActionStatus(StrEnum):
    SUCESSO = "sucesso"
    ERRO_LOGICO = "erro_logico"
    ERRO_TECNICO = "erro_tecnico"
```

## 9. Regras Inviolaveis

1. **Todo use case DEVE usar `TransactionTracker`** como context manager
2. **`tracker.add_healing_stats()`** DEVE ser chamado antes do retorno bem-sucedido
3. **Nunca suprimir excecoes** -- `TransactionTracker.__exit__` retorna `False`
4. **Erros de negocio usam `tracker.fail(msg)`**, nao excecoes
5. **Screenshots** sao salvos em `logs/screenshots/{label}_{timestamp}.png`
6. **Logs JSONL** sao append-only -- nunca sobrescrever
