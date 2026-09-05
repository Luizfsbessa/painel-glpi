# Painel Gerencial & Relatórios GLPI

Plataforma de inteligência e acompanhamento de chamados e métricas operacionais, integrada com automações via Webhook para o Microsoft Teams.

---

## 📋 Sobre o Projeto

Este painel foi desenvolvido em **Streamlit** para centralizar a gestão e o monitoramento de indicadores de TI, chamados e relatórios do GLPI. A aplicação conta com uma interface lateral otimizada, autenticação segura para envios automatizados e múltiplos módulos analíticos (como SLA, Zabbix e chamados operacionais).

---

## 🛠️ Principais Funcionalidades

- **Sidebar Unificada**: Interface limpa e contínua, sem espaçamentos ou divisores desnecessários.
- **Navegação Modular**: Seleção rápida de relatórios e painéis especializados divididos por abas e visualizações.
- **Integração com Microsoft Teams**: Envio automatizado de resumos operacionais via webhook com restrição por senha de autorização e feedback visual animado.
- **Processamento de Dados**: Leitura e tratamento dinâmico de planilhas e bases de dados.
- **Links Diretos para o GLPI**: Transformação das colunas de ID em links interativos (`st.column_config.LinkColumn`), abrindo os registros diretamente em novas abas no sistema GLPI.
- **Rotas de URLs Dinâmicas por Módulo**
- **Tratamento de Dados Robusto**: Validação automática contra duplicação de colunas e mapeamento seguro utilizando Pandas e PyArrow no Streamlit.

---

## 📂 Estrutura do Projeto

```text
painel_glpi/
├── app.py                  # Arquivo principal do Streamlit
├── utils/
│   ├── ui_helpers.py       # Estilos CSS customizados e helpers visuais
│   └── data_processing.py  # Tratamento e processamento de dados
├── views/                  # Módulos e relatórios individuais (Dashboard, SLA, Zabbix, etc.)
├── integrations.py         # Lógica de integração e Webhook do Teams
├── erro login.gif          # Ativo visual de erro de autenticação
├── relatorio glpi.xlsx     # Planilha modelo de dados
└── requirements.txt        # Dependências do projeto