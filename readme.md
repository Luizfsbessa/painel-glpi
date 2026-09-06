# Painel Gerencial & Relatórios GLPI

Plataforma de inteligência, acompanhamento de chamados e relatórios gerenciais integrada ao **GLPI**, desenvolvida em **Python** utilizando **Streamlit** e **Pandas**. 
O sistema consolida dados de incidentes e requisições, calcula SLAs dinâmicos baseados na criticidade e automatiza envios de resumos gerenciais.

---

## 📋 Sobre o Projeto

Este painel foi desenvolvido em **Streamlit** para centralizar a gestão e o monitoramento de indicadores de TI, chamados e relatórios do GLPI. A aplicação conta com uma interface lateral otimizada, autenticação segura para envios automatizados e múltiplos módulos analíticos (como SLA, Zabbix e chamados operacionais).

---

## 🛠️ Principais Funcionalidades

- **Integração Automatizada com GLPI:** Script de sincronização via API REST que busca novos chamados, atualiza status, datas de solução e recalcula o SLA de forma inteligente.
- **SLA Dinâmico por Criticidade:** Prazos de atendimento adaptados por nível de prioridade:
  - *Muito Baixa:* 2h
  - *Alta:* 4h
  - *Média:* 6h
  - *Baixa:* 10h
- **Módulos e Visões Gerenciais:**
  1. **Dashboard Geral:** Visão macro dos indicadores e métricas principais.
  2. **Relatórios Gerenciais / Metas:** Acompanhamento de volumetria frente às metas estabelecidas por área.
  3. **Relatório de Incidentes & SLA:** Monitoramento focado na conformidade de prazos.
  4. **Chamados Operacionais:** Listagem e filtros detalhados das demandas correntes.
  5. **Visão Exclusiva Zabbix:** Isolamento e análise de chamados gerados por monitoramento automático.
  6. **Gestão de Backlog & Pendentes:** Controle de chamados abertos e identificação de gargalos.
  7. **Problemas e Mudanças:** Acompanhamento de processos ITIL complementares.
  8. **Desempenho por Técnico:** Análise de produtividade e distribuição de carga de trabalho.
  9. **Comparativo entre Períodos:** Análise evolutiva de volumetria entre janelas temporais.
- **Integração com Microsoft Teams:** Envio automatizado de resumos operacionais direto para o canal de gestão mediante autenticação segura.
- **Organização Consistente:** Todas as tabelas e visualizações são automaticamente ordenadas em ordem crescente pelo **ID do chamado**.
---

## 🛠️ Tecnologias Utilizadas

- **Python** (Linguagem principal)
- **Streamlit** (Interface gráfica web e painéis)
- **Pandas / OpenPyXL** (Manipulação e leitura de bases Excel)
- **Requests / Urllib3** (Comunicação com a API REST do GLPI)
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
---

## ⚙️ Como Executar o Projeto Localmente

1. Clone o repositório para a sua máquina:
   ```bash
   git clone <url-do-repositorio>
   cd <nome-do-repositorio>
2. Instale as dependências necessárias:
  pip install -r requirements.txt
3. Certifique-se de que o arquivo de dados (relatorio glpi.xlsx) está na raiz do projeto.
4. Execute o script de atualização da base (opcional, caso queira buscar dados novos do GLPI antes de abrir o painel):
  python atualizar_glpi.py
5. Inicie a aplicação Streamlit:
  streamlit run app.py
