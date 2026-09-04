import os
import unicodedata
import streamlit as st
import pandas as pd
from datetime import time, date

# Importações de Módulos Locais
from config import settings
from utils.ui_helpers import aplicar_estilos_customizados
from utils.data_processing import carregar_e_tratar_dados, buscar_coluna
from utils.integrations import enviar_notificacao_teams
from views.incidentes_sla import renderizar as renderizar_incidentes_sla
from views.dashboard_geral import renderizar as renderizar_dashboard_geral
from views import comparativo_periodos

# Importação das Visões
from views import (
    dashboard_geral,
    relatorios_gerenciais,
    incidentes_sla,
    chamados_operacionais,
    visao_zabbix,
    gestao_backlog,
    problemas_mudancas,
    desempenho_tecnico,
    comparativo_periodos
)

st.set_page_config(page_title=settings.APP_TITLE, layout="wide")
aplicar_estilos_customizados()

st.title("📊 Painel Gerencial & Relatórios GLPI")
st.caption("Plataforma de inteligência e acompanhamento de chamados (Frescatto)")

# --- BARRA LATERAL (CARREGAMENTO) ---
st.sidebar.header("📁 Fonte de Dados")
uploaded_file = st.sidebar.file_uploader("Envie o arquivo exportado do GLPI (.csv ou .xlsx)", type=["csv", "xlsx", "xls"])

dict_bases = carregar_e_tratar_dados(uploaded_file) if uploaded_file else (
    carregar_e_tratar_dados(settings.CAMINHO_PADRAO_LOCAL) if os.path.exists(settings.CAMINHO_PADRAO_LOCAL) else {}
)

if uploaded_file is None and os.path.exists(settings.CAMINHO_PADRAO_LOCAL):
    st.sidebar.info(f"📂 Arquivo local em uso: `{settings.CAMINHO_PADRAO_LOCAL}`")

df_raw = dict_bases.get("Chamados", pd.DataFrame())
df_problemas = dict_bases.get("Problemas", pd.DataFrame())
df_mudancas = dict_bases.get("Mudanças", pd.DataFrame())

if not df_raw.empty:
    cols = {
        'tec': buscar_coluna(df_raw, ['Atribuído - Técnico', 'Técnico', 'Tecnico']),
        'tipo': buscar_coluna(df_raw, ['Tipo', 'tipo']),
        'prio': buscar_coluna(df_raw, ['Prioridade', 'prioridade']),
        'cat': buscar_coluna(df_raw, ['Categoria', 'categoria']),
        'id': buscar_coluna(df_raw, ['ID', 'id', 'Id']),
        'tit': buscar_coluna(df_raw, ['Título', 'Titulo', 'Name', 'name']),
        'req': buscar_coluna(df_raw, ['Requerente - Requerente', 'Requerente', 'requerente']),
        'status': buscar_coluna(df_raw, ['Status', 'status']),
        'grupo': buscar_coluna(df_raw, ['Atribuído - Grupo técnico', 'Grupo técnico', 'Grupo']),
        'loc': buscar_coluna(df_raw, ['Localização', 'Localizacao', 'localizacao', 'Entidade', 'entidade'])
    }

    # FILTRO DE PERÍODO NA BARRA LATERAL
    st.sidebar.divider()
    st.sidebar.header("📅 Filtro de Período")
    
    dt_validas = df_raw['dt_abertura'].dropna()
    min_dt = dt_validas.min() if not dt_validas.empty else pd.Timestamp(2020, 1, 1)
    max_dt = dt_validas.max() if not dt_validas.empty else pd.Timestamp(2026, 12, 31)

    min_date_val, max_date_val = min_dt.date(), max_dt.date()

    col_d1, col_d2 = st.sidebar.columns(2)
    with col_d1:
        padrao_inicio = max(date(date.today().year, 1, 1), min_date_val)
        dt_ini = st.date_input("Data Inicial", value=padrao_inicio, min_value=min_date_val, max_value=max_date_val, format="DD/MM/YYYY")
    with col_d2:
        dt_fim = st.date_input("Data Final", value=max_date_val, min_value=min_date_val, max_value=max_date_val, format="DD/MM/YYYY")

    start_dt = pd.Timestamp.combine(dt_ini or min_date_val, time(0, 0, 0))
    end_dt = pd.Timestamp.combine(dt_fim or max_date_val, time(23, 59, 59))
    
    df_periodo = df_raw[(df_raw['dt_abertura'] >= start_dt) & (df_raw['dt_abertura'] <= end_dt)].copy()
    df_periodo_sem_zabbix = df_periodo[~df_periodo['is_zabbix']].copy()

    if df_periodo_sem_zabbix.empty and df_periodo.empty:
        st.warning("⚠️ Nenhum chamado encontrado para o período selecionado.")
        st.stop()

    # CÁLCULO DE MÉTRICAS GERAIS
    tot_geral, tot_humanos = len(df_periodo), len(df_periodo_sem_zabbix)
    tot_zbx = len(df_periodo[df_periodo['is_zabbix']])
    
    if cols['tipo'] and cols['tipo'] in df_periodo_sem_zabbix.columns:
        df_inc = df_periodo_sem_zabbix[df_periodo_sem_zabbix[cols['tipo']].astype(str).str.contains('Incidente', case=False, na=False)]
        sla_taxa_str = f"{((len(df_inc[~df_inc['sla_estourado']]) / len(df_inc)) * 100):.1f}%" if len(df_inc) > 0 else "N/A"
    else:
        sla_taxa_str = "N/A"

    status_fechados = ['Solucionado', 'Fechado', 'Closed', 'Resolved']
    df_bk = df_periodo[~df_periodo[cols['status']].astype(str).str.strip().isin(status_fechados)].copy() if cols['status'] else pd.DataFrame()
    if not df_bk.empty:
        df_bk['dias_em_aberto'] = ((pd.Timestamp.now() - df_bk['dt_abertura']).dt.total_seconds() / 86400).apply(lambda x: max(0, int(x)) if pd.notna(x) else 0)
        criticos_cnt = len(df_bk[(~df_bk['is_zabbix']) & (df_bk['dias_em_aberto'] >= 5)])
    else:
        criticos_cnt = 0

    # -------------------------------------------------------------------------
    # PREPARAÇÃO DADOS PARA O TEAMS
    # -------------------------------------------------------------------------
    df_fechados_notif = df_periodo_sem_zabbix[df_periodo_sem_zabbix['dt_solucao'].notna()].copy() if 'dt_solucao' in df_periodo_sem_zabbix.columns else pd.DataFrame()
    if not df_fechados_notif.empty:
        df_fechados_notif['tempo_vida_horas'] = (df_fechados_notif['dt_solucao'] - df_fechados_notif['dt_abertura']).dt.total_seconds() / 3600.0
        df_fechados_notif = df_fechados_notif[df_fechados_notif['tempo_vida_horas'] >= 0]
        tms_h = df_fechados_notif['tempo_vida_horas'].mean()
        tms_notif_str = f"{tms_h / 24:.1f} dias" if tms_h >= 48 else f"{tms_h:.1f} hrs"
        pct_24h_str = f"{(len(df_fechados_notif[df_fechados_notif['tempo_vida_horas'] <= 24]) / len(df_fechados_notif) * 100):.1f}%"
    else:
        tms_notif_str, pct_24h_str = "N/A", "N/A"

    # 1. Backlog Crítico de INCIDENTES (>3 dias em aberto)
    criticos_inc_cnt = 0
    col_tipo = cols.get('tipo')
    
    if not df_bk.empty and col_tipo and col_tipo in df_bk.columns:
        mask_zabbix = ~df_bk['is_zabbix']
        mask_dias = df_bk['dias_em_aberto'] >= 3
        mask_tipo = df_bk[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)
        
        df_bk_inc = df_bk[mask_zabbix & mask_dias & mask_tipo]
        criticos_inc_cnt = len(df_bk_inc)

    # 2. String de Incidentes por Prioridade
    prio_notif_str = ""
    if cols['tipo'] and cols['prio'] and cols['tipo'] in df_periodo_sem_zabbix.columns and cols['prio'] in df_periodo_sem_zabbix.columns:
        df_inc_prio = df_periodo_sem_zabbix[df_periodo_sem_zabbix[cols['tipo']].astype(str).str.contains('Incidente', case=False, na=False)]
        if not df_inc_prio.empty:
            prio_counts = df_inc_prio[cols['prio']].value_counts()
            prio_notif_str = "\n".join([f"• {prio}: {qtd}" for prio, qtd in prio_counts.items()])

    # 3. Cálculo Unificado da Quantidade de Meses
    qtd_meses = max(1, (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1)

    # 4. String de Volume por Área
    def remover_acentos(texto):
        return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').lower()

    areas_notif_str = ""
    col_grupo = cols.get('grupo')

    if col_grupo and col_tipo and col_grupo in df_periodo_sem_zabbix.columns:
        target_map = getattr(settings, 'TARGETS_POR_AREA', {})
        grupos_unicos = df_periodo_sem_zabbix[col_grupo].dropna().unique()

        linhas_area = []
        for grp in sorted(grupos_unicos):
            df_grp = df_periodo_sem_zabbix[df_periodo_sem_zabbix[col_grupo] == grp]
            
            # Incidentes e SLA da Área
            df_grp_inc = df_grp[df_grp[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)]
            tot_inc_grp = len(df_grp_inc)
            
            if 'sla_estourado' in df_grp_inc.columns and tot_inc_grp > 0:
                estourados_grp = len(df_grp_inc[df_grp_inc['sla_estourado']])
                dentro_sla_grp = tot_inc_grp - estourados_grp
                taxa_sla_grp = (dentro_sla_grp / tot_inc_grp) * 100
                sla_str_area = f" | {taxa_sla_grp:.1f}% de SLA ({estourados_grp} estourados)"
            elif tot_inc_grp > 0:
                sla_str_area = " | SLA N/A"
            else:
                sla_str_area = ""
            
            # Requisições
            df_grp_req = df_grp[df_grp[col_tipo].astype(str).str.contains('Requisi', case=False, na=False)]
            tot_req_grp = len(df_grp_req)
            
            vol_total_area = tot_inc_grp + tot_req_grp
            
            # Target por Área
            grp_norm = remover_acentos(grp)
            target_val_base = None

            for chave_target, val in target_map.items():
                chave_norm = remover_acentos(chave_target)
                if chave_norm in grp_norm or grp_norm in chave_norm:
                    target_val_base = val
                    break

            target_val = (target_val_base * qtd_meses) if target_val_base is not None else None

            target_str = ""
            if target_val is not None and target_val > 0:
                pct_diff = ((vol_total_area - target_val) / target_val) * 100
                if pct_diff > 0:
                    target_str = f" (+{pct_diff:.1f}% Acima do Target)"
                elif pct_diff < 0:
                    target_str = f" ({pct_diff:.1f}% Abaixo do Target)"
                else:
                    target_str = " (0.0% Na Meta)"
            elif target_val is not None and target_val == 0:
                target_str = " (Target: 0)"

            # Montagem das linhas
            linha_1 = f"• **{grp}:**{target_str}  "
            linha_2 = f"↳ {tot_inc_grp} Incidentes{sla_str_area}  "
            linha_3 = f"↳ {tot_req_grp} Requisições"

            bloco_area = f"{linha_1}\n{linha_2}\n{linha_3}"
            linhas_area.append(bloco_area)
            
        areas_notif_str = "\n\n".join(linhas_area)

    # 5. Cálculo do Target Geral de Atendimento
    target_chamados_base = getattr(settings, 'TARGET_MENSAL_CHAMADOS', None)
    target_chamados = (target_chamados_base * qtd_meses) if target_chamados_base else None

    target_atend_str = ""
    if target_chamados and target_chamados > 0:
        pct_diff = ((tot_humanos - target_chamados) / target_chamados) * 100
        if pct_diff > 0:
            target_atend_str = f" (+{pct_diff:.1f}% Acima do Target)"
        elif pct_diff < 0:
            target_atend_str = f" ({pct_diff:.1f}% Abaixo do Target)"
        else:
            target_atend_str = " (0.0% Na Meta)"

    tot_humanos_fmt = f"{tot_humanos}{target_atend_str}"

    # ------------------------------------------------------------------
    # BOTÃO DE PRÉ-VISUALIZAÇÃO (TESTE SEM ENVIAR)
    # ------------------------------------------------------------------
    if st.sidebar.button("👁️ Pré-visualizar Notificação (Teste)", use_container_width=True):
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Pré-visualização da Mensagem:")
        st.sidebar.markdown(f"**📅 Período de Análise:** {start_dt.strftime('%d/%m/%Y')} até {end_dt.strftime('%d/%m/%Y')}")
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"**Total Volumetria:** {tot_geral}\n\n"
            f"**Atendimento:** {tot_humanos_fmt}\n\n"
            f"**Alertas Zabbix:** {tot_zbx}\n\n"
            f"**SLA de Incidentes:** {sla_taxa_str}\n\n"
            f"**Backlog de Incidentes (>3 dias):** {criticos_inc_cnt}\n\n"
            f"**Tempo Médio Solução (TMS):** {tms_notif_str}\n\n"
            f"**Resolvidos em < 24h:** {pct_24h_str}"
        )
        st.sidebar.markdown("---")
        st.sidebar.markdown("**🚨 Incidentes por Prioridade:**")
        st.sidebar.markdown(prio_notif_str if prio_notif_str else "Nenhum")
        st.sidebar.markdown("---")
        st.sidebar.markdown("**🏢 Volume por Área (Incidente / Requisição):**")
        st.sidebar.markdown(areas_notif_str if areas_notif_str else "Nenhum")

    # ------------------------------------------------------------------
    # BOTÕES DA LATERAL (ENVIO TEAMS)
    # ------------------------------------------------------------------
    st.sidebar.divider()
    st.sidebar.markdown("📢 **Integração Teams**")
    if st.sidebar.button("🚀 Enviar Resumo no Teams", use_container_width=True):
        com_sucesso = enviar_notificacao_teams(
            settings.WEBHOOK_TEAMS_URL,
            start_dt.strftime('%d/%m/%Y'), end_dt.strftime('%d/%m/%Y'),
            tot_geral, tot_humanos_fmt, sla_taxa_str, criticos_inc_cnt, tot_zbx,
            tms_str=tms_notif_str, pct_resolv_24h=pct_24h_str,
            prio_str=prio_notif_str, areas_str=areas_notif_str
        )
        if com_sucesso:
            st.sidebar.success("✅ Resumo enviado com sucesso no canal Gestão-GLPI!")
        else:
            st.sidebar.error("❌ Falha ao enviar para o Teams. Verifique a URL do Webhook.")

    st.sidebar.divider()
    st.sidebar.markdown("📥 **Exportar Relatório Consolidado**")
    df_resumo_executivos = pd.DataFrame([
        {"Indicador / Métrica": "Período Analisado", "Valor": f"{start_dt.strftime('%d/%m/%Y')} a {end_dt.strftime('%d/%m/%Y')}"},
        {"Indicador / Métrica": "Volumetria Total de Chamados", "Valor": tot_geral},
        {"Indicador / Métrica": "Atendimentos Equipe (Humano)", "Valor": tot_humanos},
        {"Indicador / Métrica": "Alertas Zabbix", "Valor": tot_zbx},
        {"Indicador / Métrica": "SLA de Incidentes (%)", "Valor": sla_taxa_str},
        {"Indicador / Métrica": "Backlog Crítico (> 5 Dias em Aberto)", "Valor": criticos_cnt}
    ])

    st.sidebar.download_button(
        label="📄 Baixar Resumo Executivo (CSV)",
        data=df_resumo_executivos.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"resumo_executivo_glpi_{start_dt.strftime('%d%m%Y')}_a_{end_dt.strftime('%d%m%Y')}.csv",
        mime="text/csv"
    )

    # NAVEGAÇÃO DE MÓDULOS
    modulo = st.sidebar.radio(
        "Selecione o Módulo / Relatório",
        [
            "1 - Dashboard Geral", "2 - Relatórios Gerenciais / Metas", "3 - Relatório de Incidentes & SLA",
            "4 - Chamados Operacionais", "5 - Visão Exclusiva Zabbix", "6 - Gestão de Backlog & Pendentes",
            "7 - Problemas e Mudanças", "8 - Desempenho por Técnico", "9 - Comparativo entre Períodos"
        ]
    )

    # ROTEAMENTO PARA AS VISÕES
    if modulo == "1 - Dashboard Geral":
        dashboard_geral.renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt, df_completo=df_periodo)
    elif modulo == "2 - Relatórios Gerenciais / Metas":
        relatorios_gerenciais.exibir(df_periodo_sem_zabbix, cols)
    elif modulo == "3 - Relatório de Incidentes & SLA":
        incidentes_sla.renderizar_incidentes_sla(df_periodo_sem_zabbix, cols, start_dt, end_dt)
    elif modulo == "4 - Chamados Operacionais":
        chamados_operacionais.renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt, df_completo=df_periodo)
    elif modulo == "5 - Visão Exclusiva Zabbix":
        visao_zabbix.exibir(df_periodo, cols, start_dt, end_dt)
    elif modulo == "6 - Gestão de Backlog & Pendentes":
        gestao_backlog.renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt, df_completo=df_periodo)
    elif modulo == "7 - Problemas e Mudanças":
        problemas_mudancas.renderizar(df_problemas, df_mudancas, start_dt=start_dt, end_dt=end_dt)
    elif modulo == "8 - Desempenho por Técnico":
        desempenho_tecnico.renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt)
    elif modulo == "9 - Comparativo entre Períodos":
        comparativo_periodos.exibir(df_periodo_sem_zabbix, cols, start_dt, end_dt)