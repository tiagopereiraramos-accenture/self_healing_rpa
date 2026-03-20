---
skill: 8
description: Cache persistente de reparos -- consulta obrigatoria antes de qualquer chamada LLM
globs: rpa_self_healing/infrastructure/cache/**/*.py, rpa_self_healing/application/healing_orchestrator.py
---

# Skill 8 -- Cache e Memoria de Reparos

## REGRA DE OURO

O cache DEVE ser consultado ANTES de qualquer chamada ao LLM.
Chamar LLM sem checar o cache e **PROIBIDO**.

## 1. `RepairCache`

Localizado em `rpa_self_healing/infrastructure/cache/repair_cache.py`. Implementa a interface `IRepairCache`.

### Singleton

```python
cache = RepairCache.get_instance()    # retorna a instancia singleton
RepairCache.reset_instance()           # limpa o singleton (para testes)
```

### Persistencia

Arquivo JSON em `CACHE_FILE` (default: `rpa_self_healing/infrastructure/cache/repair_cache.json`).

Estrutura do JSON:

```json
{
  "locators": {
    "CAMPO_USERNAME|input#user-name": {
      "healed": "input[name='username']",
      "bot": "expandtesting",
      "healed_at": "2026-03-23T14:23:01+00:00",
      "hit_count": 7,
      "last_hit": "2026-03-23T15:01:44+00:00",
      "confidence": 0.94
    }
  },
  "flows": {
    "expandtesting|preencher_username": {
      "healed_code": "await page.fill(\"input[name='username']\", value)",
      "healed_at": "2026-03-23T14:25:11+00:00",
      "hit_count": 2
    }
  }
}
```

## 2. Cache de Locators

### Chave

```python
def _locator_key(self, label: str, broken: str) -> str:
    return f"{label}|{broken}"
```

### `get_locator(label, broken) -> str | None`

- Busca pela chave `"{label}|{broken}"`
- Se encontrar: incrementa `hit_count`, atualiza `last_hit`, salva, loga economia estimada, retorna seletor curado
- Se nao encontrar: loga MISS, retorna `None`

```python
# Log de HIT:
# [CACHE] HIT  'CAMPO_USERNAME' -> 'input[name="username"]' (hit #8 | economia: $0.000520)

# Log de MISS:
# [CACHE] MISS 'BOTAO_LOGIN' — chamando LLM...
```

### `set_locator(label, broken, healed, bot_name, confidence)`

Salva nova entrada apos healing bem-sucedido + validacao pelo LLM:

```python
self._data["locators"][key] = {
    "healed": healed,
    "bot": bot_name,
    "healed_at": datetime.now(timezone.utc).isoformat(),
    "hit_count": 0,
    "last_hit": "",
    "confidence": confidence,
}
```

## 3. Cache de Flows

### Chave

```python
def _flow_key(self, step_name: str, bot_name: str) -> str:
    return f"{bot_name}|{step_name}"
```

### `get_flow(step_name, bot_name) -> str | None`

Retorna `healed_code` se existir, incrementa `hit_count`.

### `set_flow(step_name, bot_name, healed_code)`

Salva codigo curado com `healed_at` e `hit_count=0`.

## 4. Estatisticas

### `get_stats() -> dict`

```python
{
    "total_entries": 14,        # locators + flows
    "total_hits": 47,           # soma de hit_count dos locators
    "estimated_savings_usd": 0.003055,  # hits * _COST_PER_TOKEN * 260
    "most_used_label": "CAMPO_USERNAME|input#user-name",  # chave com mais hits
    "top_bot": "expandtesting",  # bot com mais entradas
}
```

Estimativa de economia: `_COST_PER_TOKEN = 0.00000025`, savings = `total_hits * 0.00000025 * 260`

### `clear(bot_name=None)`

- Sem argumento: limpa tudo (`{"locators": {}, "flows": {}}`)
- Com `bot_name`: filtra locators por `v["bot"] != bot_name` e flows por prefixo da chave

## 5. Fluxo Cache-First no HealingOrchestrator

O `HealingOrchestrator` (`rpa_self_healing/application/healing_orchestrator.py`) impoe a regra cache-first:

```python
# 1. Consultar cache (OBRIGATORIO)
cached = self._cache.get_locator(label, broken_selector)
if cached:
    self._stats.cache_hits += 1
    if await validate(cached):
        return self._locator_success(...)  # retorna imediatamente
    # Cache stale — prosseguir para LLM

# 2. Se miss, chamar LLM com retries
for _ in range(settings.LLM_MAX_HEALING_ATTEMPTS):
    suggestion = await self._locator.suggest(...)
    new_selector = suggestion.get("selector")
    if new_selector and await validate(new_selector):
        # 3. Apos sucesso + validacao, salvar no cache
        self._cache.set_locator(label, broken_selector, new_selector, bot_name, confidence)
        return self._locator_success(...)
```

O mesmo padrao se aplica ao flow cache:
1. `self._cache.get_flow(label, bot_name)` -- se hit, retorna imediatamente
2. Se miss, chama LLM
3. Apos sucesso, `self._cache.set_flow(label, bot_name, code)`

## 6. Comandos CLI

```bash
# Ver estatisticas do cache
uv run rpa-cli --cache-stats

# Limpar todo o cache
uv run rpa-cli --cache-clear

# Limpar cache de um bot especifico
uv run rpa-cli --cache-clear --bot expandtesting
```

Saida de `--cache-stats`:

```
╔══════════════════════════════════════════════╗
║        RELATORIO DE CACHE -- Self-Healing RPA        ║
╠══════════════════════════════════════════════╣
║ Entradas no cache:          14               ║
║ Cache hits (total):         47               ║
║ Chamadas LLM evitadas:      47               ║
║ Economia estimada:          $ 0.003055       ║
║ Seletor mais reutilizado:   CAMPO_USERNAME   ║
║ Bot com mais reparos:       expandtesting    ║
╚══════════════════════════════════════════════╝
```

## 7. Regras Inviolaveis

1. **SEMPRE consultar cache antes de chamar LLM** -- esta e a regra de ouro
2. **NUNCA instanciar `RepairCache` diretamente em bots** -- o `HealingOrchestrator` gerencia
3. **Usar `RepairCache.get_instance()`** para obter o singleton
4. **Usar `RepairCache.reset_instance()`** apenas em testes
5. **Sem TTL** -- entradas nao expiram automaticamente (seletores curados sao estaveis)
