# Seletores do Bot: TJMS
# Última atualização: 2026-03-23
# Site: https://esaj.tjms.jus.br
# Self-Healing: Automático (ver docs/skills/playwright_self_healing-5.md)
# ATENÇÃO: seletores são PLACEHOLDER — ajustar com inspeção real do portal

CAMPO_NUMERO_PROCESSO: str = "#numeroDigitoAnoUnificado"
CAMPO_FORO:            str = "#foroNumeroUnificado"
BOTAO_PESQUISAR:       str = "#pbEnviar"
RESULTADO_TITULO:      str = ".esajTabelaProcesso .esajSubTituloDoLayout"
RESULTADO_PARTES:      str = ".nomeParteEAdvogado"
RESULTADO_MOVIMENTOS:  str = ".even td, .odd td"
MENSAGEM_ERRO:         str = ".esajAlertWarning"
