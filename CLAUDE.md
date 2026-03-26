# CLAUDE.md - Self-Healing RPA Framework

## Project

Framework Python de RPA com self-healing, baseado em Playwright.
Executa codigo gerado por LLM em runtime — seguranca e prioridade absoluta.

## Regras de Seguranca (OBRIGATORIAS)

Estas regras derivam de auditoria SAST/DAST/ASA/SCA real. Violacao de qualquer regra
deve BLOQUEAR o commit ate ser corrigida.

### SEC-1: Execucao de codigo dinamico

- NUNCA usar `exec()`, `eval()` ou `compile()` sem validacao AST previa.
- Todo codigo gerado por LLM DEVE passar por `validate_generated_code()` (modulo `rpa_self_healing/domain/code_validator.py`) ANTES de execucao ou persistencia.
- Namespace de execucao DEVE usar `__builtins__: {}` para bloquear imports implicitos.
- Se precisar adicionar novos metodos Playwright permitidos, atualize `_ALLOWED_PAGE_ATTRS` em `code_validator.py`.

### SEC-2: Credenciais e segredos

- PROIBIDO hardcodar credenciais, tokens ou chaves de API no codigo-fonte.
- Credenciais DEVEM vir de variaveis de ambiente (`os.getenv`) ou secrets manager.
- Toda nova credencial DEVE ser adicionada ao `.env.example` (sem valor real).
- Falha ao carregar credencial obrigatoria DEVE levantar `EnvironmentError` com mensagem clara.
- NUNCA commitar arquivos `.env`, `credentials.json` ou similares.

### SEC-3: Dados nao confiaveis (prompt injection / input validation)

- Dados de paginas web (title, url, elementos DOM, a11y tree) sao INPUT NAO CONFIAVEL.
- Ao incluir dados externos em prompts LLM, SEMPRE delimitar com tags XML (`<page_data>...</page_data>`) e truncar (`max_len`).
- Sanitizar dados antes de incluir em mensagens de commit Git, logs ou qualquer output persistido.
- NUNCA interpolar dados de usuario/pagina diretamente em strings que serao executadas. Usar `repr()` para escapar.

### SEC-4: Path traversal e CLI inputs

- Todo input de CLI (`sys.argv`, argumentos de comando) DEVE ser validado com regex antes de uso.
- Paths construidos a partir de input de usuario DEVEM ser verificados com `.resolve().relative_to()` para garantir que estao dentro do diretorio esperado.
- Nomes de bots: apenas `[a-z][a-z0-9_]{0,49}`.

### SEC-5: Tratamento de excecoes

- PROIBIDO `except Exception: pass` (excecao silenciada). Sempre logar com `logger.debug` ou `logger.warning` no minimo.
- PROIBIDO usar `assert` para verificacoes de seguranca ou pre-condicoes de runtime. Usar `if/raise` com excecao tipada.
- Excecoes de seguranca (permissao, autenticacao, rede) NUNCA devem ser mascaradas.

### SEC-6: Rede e URLs externas

- URLs configuradas via env (ex: `OLLAMA_BASE_URL`) DEVEM ser validadas: scheme permitido (`http`/`https`), host nao esta em blocklist de metadata (169.254.169.254, metadata.google.internal).
- Chamadas HTTP a provedores LLM DEVEM ter timeout explicito (`asyncio.wait_for` com 30s ou configuravel).
- Browser contexts DEVEM ser criados com `accept_downloads=False`, `permissions=[]`, `bypass_csp=False`.

### SEC-7: Cache e integridade de dados

- Codigo lido do cache DEVE ser re-validado via AST antes de execucao (cache pode ter sido adulterado).
- Considerar HMAC para protecao de integridade do cache em ambientes de producao.

### SEC-8: Dependencias (SCA)

- Usar operador `~=` (compatible release) no `pyproject.toml` para limitar versoes de dependencias.
- NUNCA usar `>=` sem upper bound em dependencias de producao.
- Monitorar CVEs com `pip-audit` no CI.

### SEC-9: Dados sensiveis em logs

- NUNCA logar credenciais, tokens, chaves de API ou passwords.
- Mascarar identificadores de usuario (PII) em logs com hash parcial.
- Logs de auditoria devem conter contexto suficiente para troubleshooting sem expor dados sensiveis.

### SEC-10: Concorrencia

- Singletons acessados em contexto async/multi-thread DEVEM usar `threading.Lock()` (double-checked locking).
- Atencao especial a TOCTOU (Time-of-Check-Time-of-Use) em operacoes de arquivo.

## Skills

### pre-commit-review

**Trigger:** Automaticamente antes de cada commit (via hook).

**Instrucao:** Atue como um Engenheiro de Software Principal (Staff Engineer) focado em Clean Architecture, Testabilidade e Operabilidade. Revise TODOS os arquivos staged para commit e valide:

**Qualidade de codigo:**

1. **SOLID & Patterns**: Os 5 principios estao aplicados? Ha if/else ou switch excessivos que deveriam usar Strategy/Factory/Observer? SRP esta respeitado?
2. **Clean Code**: Nomes descritivos, funcoes curtas com objetivo unico, versoes estaveis de bibliotecas.
3. **DRY**: Ha duplicacao de codigo? Logica reutilizavel esta extraida?
4. **KISS**: Ha over-engineering ou complexidade desnecessaria?
5. **Composition over Inheritance**: Ha hierarquias de classes complexas que deveriam usar composicao?
6. **Observabilidade & Erros**: Tratamento de excecoes adequado? Logs estruturados (Info, Warn, Error) com contexto?
7. **Injecao de Dependencia**: O codigo e testavel com mocks/stubs?

**Seguranca (checklist obrigatorio — cada item mapeado a uma regra SEC):**

8. **SEC-1 exec/eval**: Ha uso de `exec()`, `eval()`, `compile()` sem validacao AST previa? Codigo LLM passa por `validate_generated_code()`?
9. **SEC-2 credenciais**: Ha credenciais, tokens ou chaves hardcoded? Estao em `os.getenv`?
10. **SEC-3 prompt injection**: Dados de paginas web estao sanitizados antes de entrar em prompts LLM? Ha interpolacao direta de dados externos em strings executaveis?
11. **SEC-4 path traversal**: Inputs de CLI estao validados? Paths construidos a partir de input de usuario estao verificados com `relative_to()`?
12. **SEC-5 excecoes**: Ha `except Exception: pass`? Ha `assert` usado para checagem de seguranca?
13. **SEC-6 rede**: URLs externas validadas? Timeouts configurados? Browser context restrito?
14. **SEC-7 cache**: Codigo lido do cache e re-validado antes de execucao?
15. **SEC-8 deps**: Dependencias usam `~=` no pyproject.toml?
16. **SEC-9 logs/PII**: Ha dados sensiveis (senhas, tokens, usernames) sendo logados sem mascaramento?
17. **SEC-10 concorrencia**: Singletons tem lock? Ha TOCTOU em operacoes de arquivo?

**Formato da revisao:**

```
## Analise Pre-Commit

### Arquivos revisados
- lista dos arquivos

### Problemas encontrados
- [SEVERIDADE] [SEC-N] arquivo:linha — descricao do problema e sugestao de correcao

### Veredicto
APROVADO — pode commitar
ou
REPROVADO — lista de itens que devem ser corrigidos antes do commit
```

Se encontrar problemas de severidade CRITICA ou ALTA, o commit DEVE ser REPROVADO. Sugira correcoes especificas com codigo.
