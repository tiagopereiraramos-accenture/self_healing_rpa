# Seletores do Bot: ExpandTesting
# Última atualização: 2026-03-23
# Site: https://practice.expandtesting.com/login
# Self-Healing: Automático (ver docs/skills/playwright_self_healing-5.md)

# ── Login page ──────────────────────────────────────────────────────────────
CAMPO_USERNAME: str = "input#username"
CAMPO_PASSWORD: str = "input#password"
BOTAO_LOGIN:    str = "button[type='submit']"

# ── Flash messages ───────────────────────────────────────────────────────────
FLASH_SUCESSO:  str = "div#flash.flash.success"
FLASH_ERRO:     str = "div#flash.flash.error"
FLASH_MSG:      str = "div#flash"

# ── Secure area ──────────────────────────────────────────────────────────────
BOTAO_LOGOUT:   str = "a[href='/logout']"
SECURE_AREA:    str = "h2"

# ── Seletores QUEBRADOS (para demo de healing) ───────────────────────────────
# Estes seletores são propositalmente inválidos para demonstrar o self-healing.
CAMPO_USERNAME_QUEBRADO: str = "input#username"  # Healing: 2026-03-24
BOTAO_LOGIN_QUEBRADO:    str = "#submit-btn-broken"
