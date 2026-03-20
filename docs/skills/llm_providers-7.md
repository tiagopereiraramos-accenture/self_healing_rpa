---
skill: 7
description: LLM Router com fallback chain, providers e system prompts para healing
globs: rpa_self_healing/infrastructure/llm/**/*.py, rpa_self_healing/domain/interfaces.py
---

# Skill 7 -- LLM Providers e Router

## 1. Arquitetura

O `LLMRouter` em `rpa_self_healing/infrastructure/llm/llm_router.py` centraliza todas as chamadas LLM. A cadeia de fallback e:

```
OpenRouter (principal) --> Anthropic direto (fallback) --> Ollama local (offline)
```

A IA NUNCA deve instanciar providers diretamente -- sempre usar `LLMRouter`.

## 2. `LLMRouter`

```python
class LLMRouter:
    def __init__(self) -> None:
        self._providers: list[tuple[str, ILLMProvider]] = self._build_chain()
```

### `_build_chain()`

Constroi a lista de providers disponiveis na ordem de prioridade:

1. **OpenRouter** -- instanciado se `LLM_PROVIDER == "openrouter"` E `OPENROUTER_API_KEY` esta definido
2. **Anthropic** -- instanciado se `ANTHROPIC_API_KEY` esta definido
3. **Ollama** -- sempre tentado (fallback offline)

Se nenhum provider estiver disponivel, levanta `RuntimeError`.

### `_call(system, user, model)`

Tenta cada provider em ordem. Se um falhar (excecao), loga warning e tenta o proximo. Se todos falharem, levanta `RuntimeError` com o ultimo erro.

```python
async def _call(self, system: str, user: str, model: str) -> dict[str, Any]:
    last_err: Exception | None = None
    for name, provider in self._providers:
        try:
            result = await provider.complete(system, user, model)
            return result
        except Exception as exc:
            logger.warning(f"[LLM] Provider '{name}' falhou: {exc} — tentando próximo")
            last_err = exc
    raise RuntimeError(f"Todos os providers LLM falharam. Último erro: {last_err}")
```

## 3. Metodos de Alto Nivel

### `heal_locator(broken_selector, intent, context, error)`

Usa o modelo `settings.LLM_LOCATOR_MODEL` (default: `anthropic/claude-haiku-4-5`).

Monta o prompt do usuario com:
- Seletor quebrado, intencao e erro
- URL e titulo da pagina
- Elementos interativos (top 40, do contexto)
- Accessibility tree (truncado em 2000 chars)

Retorna o resultado do provider com campo `confidence` adicionado (heuristica = 0.9).

### `heal_flow(step_name, failed_code, error, context)`

Usa o modelo `settings.LLM_FLOW_MODEL` (default: `anthropic/claude-sonnet-4-5`).

Monta o prompt com:
- Codigo que falhou e mensagem de erro
- URL e elementos disponiveis (top 30)
- Instrucao para reescrever o passo

## 4. System Prompts (exatos do codigo)

### Locator (Nivel 1):

```
Voce e um especialista em automacao web com Playwright.
Retorne APENAS o seletor CSS mais adequado. Sem explicacoes. Sem markdown.
Prioridade: aria-label > data-testid > id > name > role+texto > CSS class
```

### Flow (Nivel 2):

```
Voce e especialista em Playwright Python async.
Retorne APENAS codigo Python valido. Sem markdown. Sem explicacoes.
O codigo sera executado via exec() em contexto de automacao.
Use apenas: page.click(), page.fill(), page.wait_for_selector(), page.locator(), page.goto(). Nunca use imports dentro do codigo.
```

## 5. Interface `ILLMProvider`

Definida em `rpa_self_healing/domain/interfaces.py`:

```python
class ILLMProvider(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str, model: str) -> dict[str, Any]:
        """Retorna {"content": str, "tokens_in": int, "tokens_out": int, "cost_usd": float}."""
```

Todos os providers retornam tambem `"provider"` e `"model"` no dict.

## 6. Providers Implementados

### `OpenRouterProvider` (`openrouter_provider.py`)

```python
class OpenRouterProvider(ILLMProvider):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
```

Usa SDK `openai.AsyncOpenAI` com `base_url` do OpenRouter. `max_tokens=512`, `temperature=0.0`.

### `AnthropicProvider` (`anthropic_provider.py`)

```python
class AnthropicProvider(ILLMProvider):
    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
```

Usa SDK `anthropic.AsyncAnthropic` diretamente. Remove prefixo do modelo (ex: `"anthropic/claude-haiku-4-5"` vira `"claude-haiku-4-5"`).

### `OllamaProvider` (`ollama_provider.py`)

```python
class OllamaProvider(ILLMProvider):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
        )
```

Usa SDK `openai.AsyncOpenAI` com `base_url` apontando para Ollama local. Custo sempre `0.0`.

## 7. Captura de Contexto (`context_capture.py`)

Localizado em `rpa_self_healing/infrastructure/driver/context_capture.py`.

`capture_context(page, label)` extrai:
- **URL** e **titulo** da pagina
- **HTML** truncado em 50 KB
- **Elementos interativos** (top 60): tag, id, name, type, role, aria-label, data-testid, placeholder, texto, visibilidade
- **Accessibility tree** truncado em 3000 chars (via `page.accessibility.snapshot()`)
- **Screenshot** salvo em `logs/screenshots/{label}_{timestamp}.png` (se `SCREENSHOT_ON_FAILURE=true`)

## 8. Configuracao (`.env`)

```env
LLM_PROVIDER=openrouter
LLM_LOCATOR_MODEL=anthropic/claude-haiku-4-5
LLM_FLOW_MODEL=anthropic/claude-sonnet-4-5
LLM_FALLBACK_MODEL=ollama/llama3.3
LLM_MAX_HEALING_ATTEMPTS=2

OPENROUTER_API_KEY=sk-or-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
```

## 9. Regras Inviolaveis

1. **NUNCA instanciar providers diretamente** -- sempre usar `LLMRouter`
2. **NUNCA modificar system prompts** sem atualizar esta skill
3. **Prioridade de seletor**: aria-label > data-testid > id > name > role+texto > CSS class
4. **`LLM_MAX_HEALING_ATTEMPTS`** controla quantas tentativas de Nivel 1 antes de escalar para Nivel 2
