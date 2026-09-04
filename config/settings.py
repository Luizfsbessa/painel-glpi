import os

# Título da Aplicação
APP_TITLE = "Painel Gerencial GLPI - Frescatto"

# Arquivo Padrão
CAMINHO_PADRAO_LOCAL = "glpi - 2026-08-31T130944.926.csv"

# Webhooks
WEBHOOK_TEAMS_URL = "https://defaultb7463c0dc3c64f61bf64479832ef06.c1.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/18/workflows/9f1cda338fbb4dc5bc88a1e233ee3a78/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=WST3VyL-iXlXb--Bis6VleDX1qDdFztfsa1rkQRREkA"

# Targets Gerenciais Gerais
TARGET_MENSAL_CHAMADOS = 1134
TARGET_MENSAL_INCIDENTES = 164
TARGET_MENSAL_SLA = 53

# Targets Individuais por Área
TARGETS_POR_AREA = {
    "governança": 86,
    "bi": 11,
    "suporte": 724,
    "desenvolvimento": 194,
    "infraestrutura": 61,
    "seguranca": 22
}