# Manual do Desenvolvedor — Self-Healing RPA Framework

**Versao 3.1** | Criado por Tiago Pereira Ramos

Este manual explica, passo a passo, tudo que voce precisa saber para usar o
framework. Mesmo que voce nunca tenha trabalhado com RPA, Playwright ou IA,
vai conseguir acompanhar.

---

## Indice

1. [O que e este framework?](#1-o-que-e-este-framework)
2. [Instalacao e primeiro uso](#2-instalacao-e-primeiro-uso)
3. [Como o CLI funciona](#3-como-o-cli-funciona)
4. [Entendendo a estrutura de pastas](#4-entendendo-a-estrutura-de-pastas)
5. [Criando seu primeiro bot](#5-criando-seu-primeiro-bot)
6. [Seletores — como o bot encontra elementos na pagina](#6-seletores)
7. [Use cases — onde vive a logica do bot](#7-use-cases)
8. [Self-healing — o que acontece quando algo quebra](#8-self-healing)
9. [Pipeline — encadeando acoes em sequencia](#9-pipeline)
10. [Logging e rastreamento](#10-logging-e-rastreamento)
11. [Cache de reparos](#11-cache-de-reparos)
12. [Configuracao (.env)](#12-configuracao)
13. [Testes](#13-testes)
14. [Perguntas frequentes](#14-perguntas-frequentes)
15. [Glossario](#15-glossario)

---

## 1. O que e este framework?

Imagine que voce tem um robo (bot) que entra num site, preenche formularios e
baixa arquivos automaticamente. Agora imagine que o site muda — um botao troca
de lugar, um campo muda de nome. Normalmente o bot quebraria e voce teria que
arrumar manualmente.

**Este framework se cura sozinho.** Quando algo quebra, ele:

1. Tira uma screenshot da pagina
2. Analisa o que mudou usando Inteligencia Artificial (LLM)
3. Encontra o novo seletor correto
4. Corrige automaticamente e continua a execucao
5. Salva a correcao para nao precisar de IA na proxima vez
6. Faz commit no Git com a correcao

Tudo isso acontece **em tempo de execucao**, sem voce precisar fazer nada.

---

## 2. Instalacao e primeiro uso

### Pre-requisitos

- **Python 3.11 ou superior** instalado
- **UV** (gerenciador de pacotes) — instale em https://docs.astral.sh/uv/
- **Git** instalado
- Uma chave de API da **OpenRouter** (ou Anthropic, ou Ollama local)

### Passo a passo

```bash
# 1. Clone o repositorio
git clone https://github.com/tiagopereiraramos-accenture/self_healing_rpa.git
cd self_healing_rpa

# 2. Instale as dependencias (nunca use pip — sempre UV)
uv sync --extra dev

# 3. Instale o navegador Chromium (usado pelo Playwright)
uv run playwright install chromium

# 4. Configure as variaveis de ambiente
cp .env.example .env
# Abra o .env e coloque sua chave da OpenRouter em OPENROUTER_API_KEY=

# 5. Verifique que tudo esta funcionando
uv run pytest tests/ -v

# 6. Veja os bots disponiveis
uv run rpa-cli --list

# 7. Rode o bot de demonstracao
uv run rpa-cli expandtesting login
```

Se voce viu o navegador abrir, preencher login e senha, e o terminal mostrar
`"status": "sucesso"`, tudo esta funcionando.

### Importante: nunca use pip

Este projeto usa **UV** com `pyproject.toml`. Esqueqa que `pip install` e
`requirements.txt` existem. Os comandos que voce vai usar sao:

| O que fazer | Comando |
|-------------|---------|
| Instalar dependencias | `uv sync --extra dev` |
| Rodar qualquer coisa | `uv run <comando>` |
| Rodar testes | `uv run pytest` |
| Rodar o CLI | `uv run rpa-cli <bot> <action>` |

---

## 3. Como o CLI funciona

O CLI (`rpa-cli`) e o ponto de entrada unico do framework. Voce nunca precisa
abrir arquivos Python para executar um bot.

### Comandos basicos

```bash
# Listar todos os bots registrados e suas acoes
uv run rpa-cli --list

# Ver ajuda de um bot especifico
uv run rpa-cli expandtesting

# Rodar uma acao de um bot
uv run rpa-cli expandtesting login

# Passar parametros para a acao
uv run rpa-cli expandtesting login --username meuuser --password minhasenha

# Rodar com o navegador visivel (para debug)
uv run rpa-cli expandtesting login --headless false

# Ver relatorio de self-healing
uv run rpa-cli --healing-stats

# Ver estatisticas do cache
uv run rpa-cli --cache-stats

# Limpar o cache de reparos
uv run rpa-cli --cache-clear
```

### Como os parametros funcionam

Qualquer `--parametro valor` que voce passa no terminal chega na action do bot
como um argumento Python. Exemplo:

```bash
uv run rpa-cli expandtesting login --username joao --password 123
```

Dentro do codigo, isso chega como:

```python
async def execute(self, username="practice", password="SuperSecretPassword!", **kwargs):
    # username = "joao"
    # password = "123"
```

Voce **nunca** precisa mexer no `cli.py` para adicionar parametros. Basta
receber `**kwargs` na sua funcao e pronto.

---

## 4. Entendendo a estrutura de pastas

```
self_healing_rpa/
│
├── cli.py                         # Ponto de entrada — NUNCA modifique este arquivo
│
├── bots/                          # Aqui ficam seus bots
│   ├── base.py                    # Classe base (voce herda dela)
│   ├── registry.py                # Auto-discovery (descobre bots automaticamente)
│   ├── _template/                 # Template — copie para criar um novo bot
│   └── expandtesting/             # Bot de demonstracao (referencia)
│       ├── __init__.py            # Registro do bot e suas acoes
│       ├── selectors.py           # Seletores CSS dos elementos da pagina
│       └── use_cases/             # Logica de cada acao
│           ├── login_uc.py
│           ├── login_invalido_uc.py
│           ├── demo_healing_uc.py
│           └── flow_completo_uc.py
│
├── rpa_self_healing/              # Motor do framework — voce NAO mexe aqui
│   ├── config.py                  # Le o .env
│   ├── domain/                    # Tipos e contratos
│   ├── application/               # Logica de healing e pipeline
│   └── infrastructure/            # Playwright, LLM, Cache, Git, Logging
│
├── tests/                         # Testes automatizados
├── docs/                          # Documentacao e skills
├── pyproject.toml                 # Configuracao do projeto
└── .env                           # Suas chaves de API (nunca suba pro Git)
```

**Regra simples**: voce trabalha na pasta `bots/`. O resto e o motor do
framework e voce nao precisa modificar.

---

## 5. Criando seu primeiro bot

### Passo 1: Copie o template

```bash
cp -r bots/_template/ bots/meu_bot/
```

Agora voce tem:

```
bots/meu_bot/
├── __init__.py        # Voce vai editar este
├── selectors.py       # Voce vai editar este
└── use_cases/
    ├── __init__.py
    └── exemplo_uc.py  # Voce vai editar este
```

### Passo 2: Registre o bot

Abra `bots/meu_bot/__init__.py` e edite:

```python
from __future__ import annotations

from bots.base import BaseBot, action


class MeuBot(BaseBot):
    name = "meu_bot"
    description = "Meu primeiro bot — faz login no sistema X"
    url = "https://sistema-x.com.br"

    @action("login")
    async def _login(self, **kwargs) -> dict:
        from bots.meu_bot.use_cases.login_uc import LoginUC
        return await LoginUC(self._driver).execute(**kwargs)

    @action("baixar-relatorio")
    async def _baixar_relatorio(self, **kwargs) -> dict:
        from bots.meu_bot.use_cases.baixar_relatorio_uc import BaixarRelatorioUC
        return await BaixarRelatorioUC(self._driver).execute(**kwargs)


# OBRIGATORIO — sem isso o CLI nao encontra seu bot
BOT_CLASS = MeuBot
```

**O que esta acontecendo aqui:**

- `name` — identificador do bot no CLI (voce roda `uv run rpa-cli meu_bot login`)
- `description` — aparece quando voce roda `uv run rpa-cli --list`
- `url` — URL principal do sistema que o bot acessa
- `@action("login")` — registra o metodo como uma acao do bot
- `BOT_CLASS = MeuBot` — linha obrigatoria para o CLI descobrir seu bot

**Sobre o `@action`**: o nome que voce passa entre aspas e o nome usado no CLI.
Se voce nao passar nome, ele usa o nome do metodo (sem `_` inicial, trocando `_`
por `-`). Exemplo: `_baixar_relatorio` vira `baixar-relatorio`.

### Passo 3: Defina os seletores

Abra `bots/meu_bot/selectors.py` e mapeie os elementos da pagina:

```python
# Seletores do Bot: MeuBot
# Ultima atualizacao: 2026-03-24
# Self-Healing: Automatico

# Pagina de login
CAMPO_USUARIO:   str = "input#username"
CAMPO_SENHA:     str = "input#password"
BOTAO_ENTRAR:    str = "button[type='submit']"

# Pagina principal
MENU_RELATORIOS: str = "a[href='/relatorios']"
TABELA_DADOS:    str = "table.relatorio"
BOTAO_EXPORTAR:  str = "button:has-text('Exportar')"

# Mensagens
MSG_SUCESSO:     str = ".alert-success"
MSG_ERRO:        str = ".alert-danger"
```

**Regras dos seletores:**

- Sempre em `UPPER_SNAKE_CASE`
- Sempre com `: str = "valor"`
- Prioridade: `id` > `name` > `aria-label` > `data-testid` > CSS class
- Se o site mudar e o seletor quebrar, o framework corrige sozinho

### Passo 4: Crie o use case

Crie `bots/meu_bot/use_cases/login_uc.py`:

```python
from __future__ import annotations

import bots.meu_bot.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker


class LoginUC:
    """Use case: login no sistema X."""

    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, usuario: str = "", senha: str = "", **kwargs) -> dict:
        with TransactionTracker(
            bot_name="meu_bot",
            action="login",
            item_id=usuario,
        ) as tracker:
            # 1. Navegar para a pagina
            await self._driver.goto("https://sistema-x.com.br/login")

            # 2. Preencher campos
            await self._driver.fill("CAMPO_USUARIO", sel.CAMPO_USUARIO, usuario)
            await self._driver.fill("CAMPO_SENHA", sel.CAMPO_SENHA, senha)

            # 3. Clicar no botao
            await self._driver.click("BOTAO_ENTRAR", sel.BOTAO_ENTRAR)

            # 4. Verificar resultado
            if await self._driver.is_visible(sel.MSG_ERRO):
                msg = await self._driver.get_text("MSG_ERRO", sel.MSG_ERRO)
                tracker.fail(msg)
                return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}

            # 5. Sucesso
            tracker.add_healing_stats(self._driver.get_healing_stats())
            return {"status": ActionStatus.SUCESSO, "url": self._driver.page.url}
```

**Entenda o padrao:**

1. **`TransactionTracker`** — obrigatorio. Rastreia duracao, status, erros e healing
2. **`self._driver.fill("LABEL", sel.SELECTOR, valor)`** — o primeiro argumento e
   o nome do seletor (para logs e healing), o segundo e o seletor CSS
3. **`ActionStatus.SUCESSO / ERRO_LOGICO / ERRO_TECNICO`** — sempre retorne um desses
4. **`tracker.fail("msg")`** — use para erros de negocio (ex: senha errada)
5. **`tracker.add_healing_stats()`** — sempre chame no final para registrar metricas

### Passo 5: Teste

```bash
# Verificar que seu bot aparece
uv run rpa-cli --list

# Rodar
uv run rpa-cli meu_bot login --usuario joao --senha 123
```

---

## 6. Seletores

Seletores sao os "enderecos" dos elementos na pagina web. O framework usa
seletores CSS do Playwright.

### Exemplos comuns

```python
# Por ID (melhor opcao — mais estavel)
CAMPO_EMAIL: str = "input#email"

# Por name
CAMPO_NOME: str = "input[name='nome']"

# Por type
BOTAO_SUBMIT: str = "button[type='submit']"

# Por texto visivel
BOTAO_CONFIRMAR: str = "button:has-text('Confirmar')"

# Por aria-label (acessibilidade)
BOTAO_FECHAR: str = "[aria-label='Fechar']"

# Por data-testid (se o site usar)
CAMPO_CPF: str = "[data-testid='cpf-input']"

# Por classe CSS (menos estavel — evite se possivel)
MENSAGEM: str = "div.alert.alert-success"

# Combinando tag + classe + hierarquia
LINK_RELATORIO: str = "div.sidebar a.nav-link:has-text('Relatórios')"
```

### Prioridade (da mais estavel para a menos estavel)

1. `aria-label` — quase nunca muda
2. `data-testid` — criado especificamente para testes
3. `id` — unico na pagina
4. `name` — atributo de formulario
5. `role` + texto — acessibilidade
6. Classe CSS — pode mudar frequentemente

### O que acontece se um seletor quebrar?

Se o site mudar e seu seletor parar de funcionar, o framework:

1. Percebe que o elemento nao existe mais
2. Captura o estado atual da pagina (HTML, elementos, screenshot)
3. Envia para a IA perguntando: "esse seletor quebrou, qual e o novo?"
4. A IA responde com o novo seletor
5. O framework testa se o novo seletor funciona
6. Se funcionar: usa, salva no cache, atualiza o `selectors.py` e faz commit no Git
7. Na proxima execucao, ja usa o seletor corrigido sem precisar de IA

**Voce nao precisa fazer nada.** Isso e automatico.

---

## 7. Use cases

Cada acao do bot e um "use case" — um arquivo Python com uma classe que faz uma
coisa especifica.

### Estrutura obrigatoria

```python
from __future__ import annotations

import bots.meu_bot.selectors as sel
from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.driver.playwright_driver import PlaywrightDriver
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker


class NomeDoUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        with TransactionTracker(bot_name="...", action="...") as tracker:
            # sua logica aqui
            return {"status": ActionStatus.SUCESSO}
```

### Comandos do driver disponiveis

```python
# Navegar para uma URL
await self._driver.goto("https://site.com/pagina")

# Clicar em um elemento
await self._driver.click("BOTAO_LOGIN", sel.BOTAO_LOGIN)

# Preencher um campo de texto
await self._driver.fill("CAMPO_EMAIL", sel.CAMPO_EMAIL, "joao@email.com")

# Ler o texto de um elemento
texto = await self._driver.get_text("MENSAGEM", sel.MENSAGEM)

# Esperar um elemento aparecer
await self._driver.wait_for("TABELA", sel.TABELA)

# Verificar se um elemento esta visivel (nao ativa healing)
if await self._driver.is_visible(sel.MSG_ERRO):
    # tratar erro

# Acessar a pagina Playwright diretamente (para casos especiais)
url_atual = self._driver.page.url
await self._driver.page.screenshot(path="evidencia.png")
```

### Tratando erros de negocio

Use `tracker.fail()` para erros que nao sao excecoes (ex: login invalido):

```python
if await self._driver.is_visible(sel.MSG_ERRO):
    msg = await self._driver.get_text("MSG_ERRO", sel.MSG_ERRO)
    tracker.fail(msg)  # marca como erro_logico no log
    return {"status": ActionStatus.ERRO_LOGICO, "msg": msg}
```

Excecoes tecnicas (timeout, elemento nao encontrado, etc.) sao capturadas
automaticamente pelo `TransactionTracker` e registradas como `ERRO_TECNICO`.

### Adicionando dados ao log

```python
tracker.add_data("cpf_processado", "123.456.789-00")
tracker.add_data("arquivo_baixado", "relatorio_2026.pdf")
tracker.add_data("linhas_processadas", 42)
```

Esses dados aparecem no arquivo `logs/rpa_transactions.jsonl`.

---

## 8. Self-healing

O self-healing e o recurso principal do framework. Ele funciona em dois niveis.

### Nivel 1 — Locator Healing (seletor quebrado)

**Quando acontece:** um seletor CSS nao encontra nenhum elemento na pagina.

**O que faz:**
1. Captura screenshot + HTML + arvore de acessibilidade da pagina
2. Consulta o cache — se ja curou esse seletor antes, usa o cache (sem custo)
3. Se nao esta no cache, envia o contexto para a IA (modelo rapido e barato)
4. A IA retorna um novo seletor CSS
5. O framework valida: o novo seletor encontra algo na pagina?
6. Se sim: usa, salva no cache, atualiza `selectors.py`, commit no Git
7. Se nao: tenta de novo (ate `LLM_MAX_HEALING_ATTEMPTS` vezes)
8. Se esgotou tentativas: escala para Nivel 2

### Nivel 2 — Flow Healing (reescrita de codigo)

**Quando acontece:** o Nivel 1 falhou em todas as tentativas.

**O que faz:**
1. Envia para a IA (modelo mais potente): o codigo que falhou + o estado da pagina
2. A IA reescreve o bloco de codigo inteiro
3. O framework executa o codigo gerado em ambiente isolado
4. Se funcionar: salva no cache de fluxo para proximas vezes

### Demonstracao ao vivo

```bash
# Ver o Nivel 1 funcionando (seletor quebrado sendo curado)
uv run rpa-cli expandtesting demo-healing --nivel locator

# Ver o Nivel 2 funcionando (codigo sendo reescrito)
uv run rpa-cli expandtesting demo-healing --nivel flow

# Ver ambos os niveis
uv run rpa-cli expandtesting demo-healing --nivel ambos
```

### Deteccao proativa

Voce pode verificar seletores ANTES de executar acoes:

```python
# Verifica quais seletores estao ausentes na pagina
broken = await self._driver.detect_broken_selectors([
    ("CAMPO_USUARIO", sel.CAMPO_USUARIO),
    ("CAMPO_SENHA", sel.CAMPO_SENHA),
    ("BOTAO_ENTRAR", sel.BOTAO_ENTRAR),
])

# Cura preventivamente
if broken:
    await self._driver.heal_proactive(broken)
```

---

## 9. Pipeline

O Pipeline permite encadear varias acoes em sequencia, como uma "receita".
Se um passo falha, voce pode notificar, pular, ou parar.

### Exemplo simples

```python
from rpa_self_healing.application.pipeline import Pipeline

class FlowCompletoUC:
    def __init__(self, driver: PlaywrightDriver) -> None:
        self._driver = driver

    async def execute(self, **kwargs) -> dict:
        return await Pipeline(self._driver, bot_name="meu_bot") \
            .step("login", LoginUC) \
            .step("coleta", ColetarDadosUC) \
            .step("download", BaixarArquivoUC) \
            .on_error(notificar_erro) \
            .run(**kwargs)
```

Isso executa: login -> coleta -> download. Se qualquer passo falhar, chama
`notificar_erro` e para.

### Condicoes (branching)

```python
result = await Pipeline(self._driver, bot_name="meu_bot") \
    .step("login", LoginUC) \
    .step("admin-panel", AdminPanelUC, when=lambda r: r.get("role") == "admin") \
    .step("coleta", ColetarDadosUC) \
    .run()
```

O step `admin-panel` so executa se o login retornou `"role": "admin"`.
Se nao, e pulado automaticamente.

### Passando dados entre steps

```python
result = await Pipeline(self._driver, bot_name="meu_bot") \
    .step("login", LoginUC, forward=["token"]) \
    .step("coleta", ColetarDadosUC) \
    .run(username="joao")
```

O step `login` retorna `{"status": "sucesso", "token": "abc123"}`.
Como `forward=["token"]`, o step `coleta` recebe `token="abc123"` como parametro.

### Continuar apos erro

```python
result = await Pipeline(self._driver, bot_name="meu_bot") \
    .step("item1", ProcessarItemUC) \
    .step("item2", ProcessarItemUC) \
    .step("item3", ProcessarItemUC) \
    .on_error(notificar_erro, stop=False)  # nao para, continua
    .run()
```

### Error handler

```python
async def notificar_erro(step_name: str, result: dict, driver) -> None:
    """Chamado automaticamente quando um step falha."""
    logger.error(f"Step '{step_name}' falhou: {result.get('msg')}")
    # Aqui voce pode integrar com Slack, Teams, email, etc.
```

### Resultado do pipeline

```python
{
    "status": "sucesso",         # "sucesso" se todos passaram
    "steps_completed": 3,
    "steps_skipped": 0,
    "steps_failed": 0,
    "steps_total": 3,
    "results": [
        {"step": "login", "status": "sucesso", ...},
        {"step": "coleta", "status": "sucesso", ...},
        {"step": "download", "status": "sucesso", ...},
    ],
    "last_result": {...}
}
```

### Rodar o pipeline de demo

```bash
uv run rpa-cli expandtesting flow-completo
```

---

## 10. Logging e rastreamento

Todo use case deve usar o `TransactionTracker`. Ele gera logs automaticos.

### Arquivos de log

```
logs/
├── rpa.log                    # Log geral (rotacao 10MB, retencao 7 dias)
├── rpa_transactions.jsonl     # Registro de cada execucao de use case
├── healing_events.jsonl       # Registro de cada healing realizado
└── screenshots/               # Screenshots de falhas
```

### O que aparece no terminal

```
14:23:01 | INFO     | [DRIVER] expandtesting.login | item=practice
14:23:02 | INFO     | [DRIVER] goto https://practice.expandtesting.com/login
14:23:03 | WARNING  | [HEALER] Healing ativado: 'CAMPO_USERNAME' — TimeoutError
14:23:03 | INFO     | [CACHE] MISS 'CAMPO_USERNAME' — chamando LLM...
14:23:04 | INFO     | [LLM] OpenRouter → anthropic/claude-haiku-4-5
14:23:05 | SUCCESS  | [OK] Healing nivel 1 bem-sucedido: 'CAMPO_USERNAME' -> 'input#username'
14:23:06 | SUCCESS  | [OK] expandtesting.login — 4823ms
```

### Relatorios

```bash
# Ver historico de healings
uv run rpa-cli --healing-stats

# Ver estatisticas do cache
uv run rpa-cli --cache-stats
```

### Relatorio automatico de healing

Ao final de cada use case, se houve healing, o framework imprime automaticamente:

```
=======================================================
  SELF-HEALING REPORT -- expandtesting
=======================================================
  Tentativas de healing:   2
  Bem-sucedidos:           2  (100%)
  Cache hits:              1
  Nivel 1 (locator):       2
  Nivel 2 (flow):          0
  Tokens consumidos:       518
  Custo estimado:          $ 0.000065
  Commits Git:             1
=======================================================
```

---

## 11. Cache de reparos

Quando o framework cura um seletor, ele salva a correcao num cache JSON.
Na proxima vez que o mesmo seletor quebrar, ele usa o cache — sem chamar a IA.

### Como funciona

1. Seletor quebra → framework consulta o cache
2. **Cache HIT**: usa a correcao salva (custo zero, instantaneo)
3. **Cache MISS**: chama a IA, valida, salva no cache para a proxima vez

### Comandos

```bash
# Ver quantas chamadas de IA foram evitadas pelo cache
uv run rpa-cli --cache-stats

# Limpar o cache (forca o framework a chamar a IA de novo)
uv run rpa-cli --cache-clear

# Limpar cache de um bot especifico
uv run rpa-cli --cache-clear --bot expandtesting
```

### Onde o cache fica salvo

Arquivo: `rpa_self_healing/infrastructure/cache/repair_cache.json`

Este arquivo esta no `.gitignore` — nao sobe pro Git. Cada maquina tem seu
proprio cache.

---

## 12. Configuracao

Todas as configuracoes ficam no arquivo `.env` na raiz do projeto.

### Variaveis importantes

```env
# === Sua chave de API (obrigatoria — pelo menos uma) ===
OPENROUTER_API_KEY=sk-or-v1-...     # OpenRouter (recomendado)
ANTHROPIC_API_KEY=                    # Anthropic (alternativa)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama (offline, gratis)

# === Qual IA usar ===
LLM_PROVIDER=openrouter               # openrouter | anthropic | ollama
LLM_LOCATOR_MODEL=anthropic/claude-haiku-4-5   # Modelo para seletores (rapido)
LLM_FLOW_MODEL=anthropic/claude-sonnet-4-5     # Modelo para reescrita (potente)
LLM_MAX_HEALING_ATTEMPTS=2            # Quantas vezes tentar antes de escalar

# === Git ===
GIT_AUTO_COMMIT=true     # Commita automaticamente seletores curados
GIT_AUTO_PUSH=false      # NUNCA mude para true sem autorizacao

# === Playwright ===
PLAYWRIGHT_HEADLESS=false    # false = ve o navegador | true = invisivel
PLAYWRIGHT_SLOW_MO=300       # Delay entre acoes (ms) — bom para debug
PLAYWRIGHT_TIMEOUT=10000     # Tempo maximo de espera por elemento (ms)

# === Logging ===
LOG_LEVEL=INFO               # DEBUG para ver mais detalhes
SCREENSHOT_ON_FAILURE=true   # Salva screenshot quando algo falha
```

### Dicas

- **Para debug**: use `PLAYWRIGHT_HEADLESS=false` e `PLAYWRIGHT_SLOW_MO=500`
- **Para producao**: use `PLAYWRIGHT_HEADLESS=true` e `PLAYWRIGHT_SLOW_MO=0`
- **Sem internet**: configure `LLM_PROVIDER=ollama` e instale o Ollama local
- **Nunca suba `.env` pro Git** — ele esta no `.gitignore`

---

## 13. Testes

```bash
# Rodar todos os testes
uv run pytest tests/ -v

# Rodar apenas testes de um modulo
uv run pytest tests/unit/test_pipeline.py -v

# Rodar um teste especifico
uv run pytest tests/unit/test_pipeline.py::test_pipeline_all_steps_succeed -v
```

Os testes usam mocks — nao abrem navegador nem chamam IA. Sao rapidos e seguros.

Atualmente: **48 testes unitarios** cobrindo cache, healers, orchestrator,
pipeline, selector repository, config e LLM router.

---

## 14. Perguntas frequentes

### "Preciso saber IA/LLM para usar o framework?"

Nao. A IA e completamente transparente. Voce cria seus bots normalmente e o
framework cuida do healing automaticamente.

### "E se a IA errar o seletor?"

O framework valida o seletor antes de usar. Se a IA retornar algo errado, ele
tenta de novo (ate `LLM_MAX_HEALING_ATTEMPTS` vezes). Se esgotar, escala para
o Nivel 2 (reescrita de codigo). Se tudo falhar, lanca a excecao original.

### "Quanto custa usar a IA?"

Muito pouco. Um healing tipico de seletor custa ~$0.00003 (Claude Haiku).
E depois que cura, o cache evita chamar a IA de novo. Voce pode acompanhar
custos com `uv run rpa-cli --healing-stats`.

### "Posso rodar sem internet?"

Sim. Configure `LLM_PROVIDER=ollama` e instale o Ollama com um modelo local
(llama3.3, mistral, etc.). Qualidade menor, mas funciona offline.

### "O que acontece se nao tiver .git?"

O framework funciona normalmente — apenas nao faz commits automaticos.
As correcoes ficam no cache e nos logs.

### "Posso usar Playwright direto no meu use case?"

Sim, via `self._driver.page`. Mas prefira sempre os metodos do driver
(`click`, `fill`, `get_text`) porque eles tem self-healing. Se voce usar
`page.click("#btn")` diretamente, nao tera healing.

### "Como crio um pipeline com muitos steps?"

```python
pipeline = Pipeline(self._driver, bot_name="meu_bot")
for item in lista_de_itens:
    pipeline.step(f"processar-{item}", ProcessarItemUC)
pipeline.on_error(notificar, stop=False)
result = await pipeline.run(itens=lista_de_itens)
```

### "Como vejo o que a IA fez?"

Olhe os arquivos em `logs/`:
- `healing_events.jsonl` — cada healing com seletor antigo, novo, modelo, custo
- `rpa_transactions.jsonl` — cada execucao com status, duracao, healing stats
- `screenshots/` — screenshots do momento da falha

---

## 15. Glossario

| Termo | Significado |
|-------|-------------|
| **Bot** | Automacao que interage com um site especifico |
| **Action** | Uma operacao que o bot sabe fazer (ex: login, baixar arquivo) |
| **Use case (UC)** | Classe Python que implementa uma action |
| **Seletor** | "Endereco" CSS de um elemento na pagina (ex: `input#email`) |
| **Self-healing** | Capacidade do framework de se corrigir automaticamente |
| **Nivel 1** | Healing de seletor — troca o CSS selector |
| **Nivel 2** | Healing de fluxo — reescreve o codigo inteiro |
| **LLM** | Large Language Model — a IA usada para healing (Claude, Llama, etc.) |
| **Cache** | Memoria de correcoes ja feitas (evita chamar IA de novo) |
| **Pipeline** | Sequencia de steps executados em ordem |
| **Step** | Um passo dentro de um pipeline |
| **TransactionTracker** | Rastreador de execucao para auditoria |
| **Driver** | Wrapper do Playwright com healing integrado |
| **UV** | Gerenciador de pacotes Python moderno (substitui pip) |
| **Playwright** | Biblioteca para controlar navegadores web |
| **OpenRouter** | Gateway de APIs de IA (acesso a varios modelos) |
| **MAPE-K** | Monitor, Analyze, Plan, Execute, Knowledge — ciclo de self-healing |
