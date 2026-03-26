---
skill: 6
description: Estrutura obrigatoria de bots RPA, decorador @action, use cases e selectors
globs: bots/**/*.py, bots/base.py
---

# Skill 6 -- Desenvolvimento de Bots RPA

## 1. Estrutura de Diretorio

Todo bot vive em `bots/<bot_name>/` com a seguinte estrutura:

```
bots/
├── base.py                    # BaseBot + @action decorator
├── registry.py                # Auto-discovery de BOT_CLASS
├── _template/                 # Template para novos bots (BOT_CLASS omitido)
│   ├── __init__.py
│   ├── selectors.py
│   └── use_cases/
│       ├── __init__.py
│       └── exemplo_uc.py
└── expandtesting/             # Bot de referencia
    ├── __init__.py
    ├── selectors.py
    └── use_cases/
        ├── __init__.py
        ├── login_uc.py
        ├── login_invalido_uc.py
        ├── demo_healing_uc.py
        └── flow_completo_uc.py
```

Para criar um novo bot: `cp -r bots/_template/ bots/nome_do_bot/`

O template (`bots/_template/`) NAO define `BOT_CLASS`, portanto nao aparece no CLI.

## 2. `BaseBot` (`bots/base.py`)

```python
class BaseBot:
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
        """Resolve automaticamente para bots/<bot>/selectors.py"""
        mod = sys.modules.get(type(self).__module__)
        if mod and mod.__file__:
            return Path(mod.__file__).parent / "selectors.py"
        return Path("selectors.py")
```

Atributos de classe obrigatorios:
- `name` -- identificador usado pelo CLI (ex: `"expandtesting"`)
- `description` -- texto exibido em `rpa-cli --list`
- `url` -- URL base do sistema alvo

O construtor recebe uma instancia de `PlaywrightDriver`.

## 3. Decorador `@action("name")`

Definido em `bots/base.py`:

```python
def action(name: str | None = None):
    def decorator(fn: Callable) -> Callable:
        fn._action_name = name or fn.__name__.lstrip("_").replace("_", "-")
        return fn
    return decorator
```

Comportamento:
- Define o atributo `_action_name` no metodo
- Se `name` nao for informado, deriva do nome do metodo: `_minha_action` vira `minha-action`
- NAO existe `add_argument` -- parametros chegam como `**kwargs` vindos do CLI
- `get_actions()` descobre automaticamente todos os metodos com `_action_name`

## 4. Exemplo Completo: `bots/expandtesting/__init__.py`

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

Regras criticas:
- `BOT_CLASS` no final do modulo e OBRIGATORIO para auto-discovery
- Imports de use cases sao **lazy** (dentro do metodo `@action`) para evitar imports circulares
- Cada `@action` retorna `dict` e delega para um use case

## 5. Padrao de Use Case (`LoginUC`)

```python
from __future__ import annotations

import os

import bots.expandtesting.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker

LOGIN_URL = "https://practice.expandtesting.com/login"


class LoginUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(
        self,
        username: str = "",
        password: str = "",
        **kwargs,
    ) -> dict:
        # SEC-2: credenciais NUNCA hardcoded — vem do env ou argumento
        username = username or os.getenv("BOT_USERNAME", "")
        password = password or os.getenv("BOT_PASSWORD", "")
        if not username or not password:
            raise EnvironmentError(
                "Credenciais nao configuradas. Defina BOT_USERNAME e BOT_PASSWORD "
                "no ambiente ou passe como argumento."
            )

        with TransactionTracker(
            bot_name="expandtesting",
            action="login",
            item_id=username,
        ) as tracker:
            await self._driver.goto(LOGIN_URL)
            await self._driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
            await self._driver.fill("CAMPO_PASSWORD", sel.CAMPO_PASSWORD, password)
            await self._driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

            # Erro logico (credenciais invalidas)
            if await self._driver.is_visible(sel.FLASH_ERRO):
                msg = await self._driver.get_text("FLASH_MSG", sel.FLASH_MSG)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}

            # Sucesso
            tracker.add_data("redirect_url", self._driver.page.url)
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
```

Pontos obrigatorios no use case:
- Construtor recebe `PlaywrightDriver`
- `execute()` aceita `**kwargs` e usa `TransactionTracker` como context manager
- **SEC-2: Credenciais NUNCA hardcoded** — usar `os.getenv()` com fallback vazio e `EnvironmentError` se ausente
- Interacoes com a pagina usam `self._driver.fill("LABEL", sel.SELECTOR, valor)`
- `tracker.add_healing_stats(self._driver.get_healing_stats())` antes do retorno
- Erros de negocio usam `tracker.fail("msg")` (NAO levantam excecao)

## 6. Arquivo de Selectors (`selectors.py`)

```python
# Seletores do Bot: ExpandTesting
# Ultima atualizacao: 2026-03-23
# Site: https://practice.expandtesting.com/login
# Self-Healing: Automatico (ver docs/skills/playwright_self_healing-5.md)

# -- Login page --
CAMPO_USERNAME: str = "input#username"
CAMPO_PASSWORD: str = "input#password"
BOTAO_LOGIN:    str = "button[type='submit']"

# -- Flash messages --
FLASH_SUCESSO:  str = "div#flash.flash.success"
FLASH_ERRO:     str = "div#flash.flash.error"
FLASH_MSG:      str = "div#flash"

# -- Secure area --
BOTAO_LOGOUT:   str = "a[href='/logout']"
SECURE_AREA:    str = "h2"

# -- Seletores QUEBRADOS (para demo de healing) --
CAMPO_USERNAME_QUEBRADO: str = "input#username"
BOTAO_LOGIN_QUEBRADO:    str = "#submit-btn-broken"
```

Formato obrigatorio:
- Variaveis em UPPER_SNAKE_CASE com type hint `: str`
- Valores sao seletores CSS validos
- Comentarios agrupam por secao da pagina

## 7. Retorno de Actions

O dict de retorno DEVE incluir `status: ActionStatus`:

```python
from rpa_self_healing.domain.entities import ActionStatus

# Valores possiveis:
ActionStatus.SUCESSO        # "sucesso"
ActionStatus.ERRO_LOGICO    # "erro_logico" -- erro de negocio (credenciais, validacao)
ActionStatus.ERRO_TECNICO   # "erro_tecnico" -- excecao nao tratada
```

## 9. Estilo v3.2 — @use_case + @bot

### Use case com @use_case

```python
from rpa_self_healing import use_case, OK, FAIL
import bots.meu_bot.selectors as sel

@use_case("meu_bot", "login")
async def login(driver, username="", password="", **kwargs):
    await driver.goto("https://sistema.com")
    await driver.fill("CAMPO_USERNAME", sel.CAMPO_USERNAME, username)
    await driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)
    return OK(url=driver.page.url)
```

### Bot com @bot (auto-discovery)

```python
from bots.base import bot

@bot(name="meu_bot", description="Meu bot", url="https://sistema.com")
class MeuBot:
    pass  # actions auto-descobertas de use_cases/
```

O decorator `@bot`:
- Herda `BaseBot` automaticamente
- Auto-descobre use cases decorados com `@use_case` na pasta `use_cases/`
- Define `BOT_CLASS` automaticamente no modulo

### Geracao com scaffold

```bash
uv run rpa-cli scaffold meu_bot --url https://sistema.com --actions login,coleta
```

### Helpers OK / FAIL

```python
return OK(url="...", token="abc")
# => {"status": ActionStatus.SUCESSO, "url": "...", "token": "abc"}

return FAIL("credenciais invalidas")
# => {"status": ActionStatus.ERRO_LOGICO, "msg": "credenciais invalidas"}
```

## 10. Regras Inviolaveis

1. **NUNCA modifique `cli.py` para adicionar novas actions** -- basta usar `@action` + `BOT_CLASS`
2. **Imports lazy** dentro de metodos `@action` para evitar imports circulares
3. **Um use case por arquivo** em `use_cases/`
4. **`TransactionTracker` obrigatorio** em todo use case
5. **`tracker.fail(msg)` para erros logicos**, nao excecoes
6. **`tracker.add_healing_stats()`** deve ser chamado antes do retorno bem-sucedido
7. **Para novos bots, prefira `@use_case` + `@bot` (v3.2) em vez de classes**
8. **SEC-2: PROIBIDO hardcodar credenciais** -- usar `os.getenv()` + `EnvironmentError`
9. **SEC-4: Validar input do CLI** -- `bot_name` deve ser `[a-z][a-z0-9_]{0,49}`, paths verificados com `relative_to()`
