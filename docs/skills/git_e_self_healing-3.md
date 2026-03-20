---
skill: 3
description: Git auto-commit e persistencia de seletores curados via self-healing
---

# Skill 3 -- Git e Self-Healing Persistente

O framework persiste seletores curados diretamente no codigo-fonte (`selectors.py`)
e faz commit automatico via Git. Dois componentes trabalham juntos:
`SelectorRepository` (escrita no arquivo) e `GitService` (commit).

---

## 1. GitService

**Arquivo:** `rpa_self_healing/infrastructure/git/git_service.py`

Usa a biblioteca `gitpython` para auto-commit de seletores curados.

### Configuracao

- `GIT_AUTO_COMMIT=true` (padrao) -- commita apos cada healing nivel 1 bem-sucedido
- `GIT_AUTO_PUSH=false` (padrao) -- NUNCA alterar para `true` sem autorizacao explicita

### Graceful Degradation

Se nao existir repositorio `.git`, o servico loga um warning e retorna `False`.
O healing continua funcionando normalmente (cache local + log):

```python
# git_service.py (trecho real)
def _load_repo(self):
    if not settings.GIT_AUTO_COMMIT:
        return None
    try:
        import git
        return git.Repo(search_parent_directories=True)
    except Exception:
        logger.warning("[GIT] Repositorio Git nao encontrado -- graceful degradation")
        return None
```

### Mensagem de Commit

O metodo `commit_healed_selector()` cria mensagens detalhadas com prefixo `feat(self-healing):`:

```python
# git_service.py (formato real do commit)
message = (
    f"feat(self-healing): Ajustado seletor para '{label}'\n\n"
    f"Bot: {bot_name}\n"
    f"Seletor anterior: {old_selector}\n"
    f"Novo seletor:     {new_selector}\n"
    f"Nivel de healing: {healing_level} (Nivel {'1' if healing_level == 'LOCATOR' else '2'})\n"
    f"LLM utilizado:    {llm_model}\n"
    f"Tokens usados:    {tokens_in} input + {tokens_out} output\n"
    f"Confianca:        {confidence:.2f}\n\n"
    f"Correcao automatica -- Framework Self-Healing RPA v3.0"
)
```

### Assinatura do Metodo

```python
def commit_healed_selector(
    self,
    selectors_file: Path,
    label: str,
    old_selector: str,
    new_selector: str,
    bot_name: str,
    healing_level: str = "LOCATOR",
    llm_model: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    confidence: float = 0.0,
) -> bool:
```

## 2. SelectorRepository

**Arquivo:** `rpa_self_healing/infrastructure/git/selector_repository.py`

Atualiza o `selectors.py` de um bot usando **REGEX apenas** -- NUNCA usar AST ou code formatters.

### Regras

- Usa regex para localizar o pattern `LABEL: str = "value"` com comentario opcional
- Adiciona comentario `# Healing: YYYY-MM-DD` apos atualizacao
- Preserva comentarios existentes e formatacao
- Se ja existe `# Healing:` no comentario, atualiza a data

```python
# selector_repository.py (implementacao real)
class SelectorRepository:
    def update(self, selectors_file: Path, label: str, new_selector: str) -> bool:
        content = selectors_file.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"^(?P<name>{re.escape(label)})\s*:\s*str\s*=\s*['\"](?P<value>[^'\"]*)['\"](?P<comment>.*)$",
            re.MULTILINE,
        )
        match = pattern.search(content)
        if not match:
            return False

        # Atualiza ou adiciona tag de healing
        healing_tag = f"  # Healing: {date.today().isoformat()}"
        if "# Healing:" in comment_part:
            # Atualiza data existente
            comment_part = re.sub(r"#\s*Healing:\s*\S+", f"# Healing: {date.today().isoformat()}", comment_part)
            new_line = f"{label}: str = \"{new_selector}\"{comment_part}"
        else:
            new_line = f'{label}: str = "{new_selector}"{healing_tag}'

        updated = content.replace(old_line, new_line, 1)
        selectors_file.write_text(updated, encoding="utf-8")
        return True
```

### Formato do selectors.py

```python
# bots/expandtesting/selectors.py
CAMPO_USERNAME: str = "input#username"       # Healing: 2026-03-24
CAMPO_PASSWORD: str = "input#password"
BOTAO_LOGIN: str = "button[type='submit']"   # Formulario principal
```

## 3. Fluxo Completo de Persistencia

Chamado pelo `PlaywrightDriver._persist_healed_selector()` apos healing nivel 1 bem-sucedido:

```
1. HealingOrchestrator.heal() retorna HealingResult(success=True, selector="...", event=...)
2. PlaywrightDriver._do_heal() detecta result.success and result.selector
3. PlaywrightDriver._persist_healed_selector() e chamado:
   a. SelectorRepository.update() -- atualiza selectors.py com novo seletor + tag Healing
   b. GitService.commit_healed_selector() -- git add + git commit com mensagem detalhada
   c. Se commit bem-sucedido: orchestrator.stats.git_commits += 1
```

```python
# playwright_driver.py (implementacao real)
def _persist_healed_selector(self, label: str, old_selector: str, result) -> None:
    if not self._selectors_file or not result.event:
        return
    updated = self._selector_repo.update(
        self._selectors_file, label, result.selector,
    )
    if not updated:
        return
    event = result.event
    committed = self._git.commit_healed_selector(
        selectors_file=self._selectors_file,
        label=label,
        old_selector=old_selector,
        new_selector=result.selector,
        bot_name=self._bot_name,
        healing_level=str(result.level),
        llm_model=f"{event.llm_model} ({event.llm_provider})" if event.llm_model else "",
        tokens_in=event.tokens_in,
        tokens_out=event.tokens_out,
        confidence=event.confidence,
    )
    if committed and self._orchestrator:
        self._orchestrator.stats.git_commits += 1
```

## 4. Rastreabilidade no Git

Commits de healing sao facilmente rastreavels:

```bash
git log --oneline --grep="self-healing"
git log --all --follow -- bots/expandtesting/selectors.py
```

## 5. Comportamento por Ambiente

| Variavel           | Padrao  | Descricao                                     |
| ------------------ | ------- | --------------------------------------------- |
| `GIT_AUTO_COMMIT`  | `true`  | Commita apos cada healing nivel 1 bem-sucedido |
| `GIT_AUTO_PUSH`    | `false` | NUNCA alterar sem autorizacao                  |

- Sem `.git`: graceful degradation -- healing funciona via cache + log
- CI/CD: recomendado `GIT_AUTO_COMMIT=false`, healing apenas em cache
