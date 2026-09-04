# 📊 Painel Gerencial & Relatórios GLPI - Frescatto

Aplicação interativa em Python e Streamlit desenvolvida para análise executiva, acompanhamento de métricas de atendimento, SLAs, alertas automatizados do Zabbix e gestão de backlog a partir de exportações de dados do GLPI.

---

## 🛠️ Funcionalidades Principais

* **Dashboard Executivo:** Visão consolidada de volumetria, atendimentos da equipe, taxa de conformidade de SLA e incidentes por prioridade.
* **Alertas Zabbix:** Isolamento e tratamento de chamados gerados via automação do Zabbix, com higienização de títulos e métricas de recorrência.
* **Acompanhamento de Metas:** Indicadores visuais alinhados com as metas gerenciais mensais.
* **Gestão de Backlog & Pendentes:** Identificação rápida de chamados ativos e alerta de chamados críticos parados há mais de 5 dias.
* **Integração Microsoft Teams:** Envio automatizado de relatórios gerenciais via Webhook (Adaptive Cards) diretamente para o canal da equipe.
* **Exportação de Dados:** Download simplificado em formato CSV para consolidação executiva.

---

## 📂 Arquitetura do Projeto

A aplicação segue uma estrutura modular em camadas para facilitar a manutenção e escalabilidade:

```text
painel_glpi/
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Parâmetros gerais, metas e URLs de Webhook
│
├── utils/
│   ├── __init__.py
│   ├── data_processing.py      # Tratamento, higienização e parsing (Pandas)
│   ├── integrations.py         # Envio de notificações para o Teams
│   └── ui_helpers.py           # Estilos CSS e formatadores de tabelas
│
├── views/                      # Módulos das telas do painel
│   ├── __init__.py
│   ├── chamados_operacionais.py
│   ├── comparativo_periodos.py
│   ├── dashboard_geral.py
│   ├── desempenho_tecnico.py
│   ├── gestao_backlog.py
│   ├── incidentes_sla.py
│   ├── problemas_mudancas.py
│   ├── relatorios_gerenciais.py
│   └── visao_zabbix.py
│
├── app.py                      # Ponto de entrada (Entrypoint Streamlit)
├── requirements.txt            # Dependências do projeto
└── README.md                   # Documentação do sistema