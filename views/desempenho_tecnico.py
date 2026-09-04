import streamlit as st
import pandas as pd
from utils.ui_helpers import mostrar_dataframe

def renderizar(*args, **kwargs):
    # Tratamento flexível para aceitar qualquer ordem de argumentos do app.py
    df_base = None
    cols = kwargs.get('cols', {})
    start_dt = kwargs.get('start_dt')
    end_dt = kwargs.get('end_dt')

    for arg in args:
        if isinstance(arg, pd.DataFrame):
            df_base = arg
        elif isinstance(arg, dict):
            cols = arg
        elif hasattr(arg, 'strftime'):
            if start_dt is None:
                start_dt = arg
            else:
                end_dt = arg

    if df_base is None:
        df_base = kwargs.get('df_completo') or kwargs.get('df_periodo_sem_zabbix')

    if df_base is None or df_base.empty:
        st.warning("Nenhum dado disponível na base carregada.")
        return

    dt_inicio_str = start_dt.strftime('%d/%m/%Y') if hasattr(start_dt, 'strftime') else "Início"
    dt_fim_str = end_dt.strftime('%d/%m/%Y') if hasattr(end_dt, 'strftime') else "Fim"

    st.subheader(f"👨‍💻 Performance da Área & Desempenho por Técnico ({dt_inicio_str} a {dt_fim_str})")

    # Identificação flexível de colunas
    col_tecnico = cols.get('tecnico') or next((c for c in df_base.columns if any(k in str(c).lower() for k in ['técnico', 'tecnico', 'atribuído', 'atribuido', 'responsável'])), None)
    col_tipo = cols.get('tipo') or next((c for c in df_base.columns if any(k in str(c).lower() for k in ['tipo', 'type', 'categoria'])), None)
    col_status = cols.get('status') or next((c for c in df_base.columns if any(k in str(c).lower() for k in ['status', 'estado'])), None)
    col_prioridade = cols.get('prioridade') or next((c for c in df_base.columns if any(k in str(c).lower() for k in ['prioridade', 'priority'])), None)

    # --- ABAS DE NAVEGAÇÃO ---
    tab_geral, tab_individual = st.tabs([
        "🌐 Visão Geral da Área", 
        "👤 Visão Individual por Técnico"
    ])

    # ---------------------------------------------------------
    # ABA 1: VISÃO GERAL DA ÁREA
    # ---------------------------------------------------------
    with tab_geral:
        total_chamados = len(df_base)
        
        # Incidentes vs Requisições
        n_incidentes = 0
        n_requisicoes = 0
        if col_tipo and col_tipo in df_base.columns:
            s_tipo = df_base[col_tipo].astype(str).str.lower()
            n_incidentes = len(df_base[s_tipo.str.contains('incidente', na=False)])
            n_requisicoes = len(df_base[s_tipo.str.contains('requisi|solicita', na=False)])
        else:
            n_requisicoes = total_chamados

        # SLA (Simulado ou baseado em coluna se existir)
        sla_pct = "N/A"
        col_sla = next((c for c in df_base.columns if 'sla' in str(c).lower() and 'cumprido' in str(c).lower()), None)
        if col_sla and col_sla in df_base.columns:
            cumpridos = len(df_base[df_base[col_sla].astype(str).str.contains('sim|yes|ok|cumprido', case=False, na=False)])
            sla_pct = f"{(cumpridos / total_chamados * 100):.1f}%" if total_chamados > 0 else "0.0%"

        # Cards de KPI da Área
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Chamados", f"{total_chamados:,}".replace(',', '.'))
        c2.metric("Incidentes vs Requisições", f"{n_incidentes:,} / {n_requisicoes:,}".replace(',', '.'))
        c3.metric("SLA Geral", sla_pct)

        st.divider()

        # Ranking de Técnicos por Volume
        st.markdown("### 🏆 Ranking de Volume por Técnico")
        if col_tecnico and col_tecnico in df_base.columns:
            df_ranking = df_base[col_tecnico].value_counts().reset_index()
            df_ranking.columns = ['Técnico', 'Total de Chamados']
            df_ranking['% da Equipe'] = (df_ranking['Total de Chamados'] / total_chamados * 100).round(1).astype(str) + '%'
            
            mostrar_dataframe(df_ranking)
        else:
            st.info("Coluna de técnico não identificada para gerar o ranking.")

    # ---------------------------------------------------------
    # ABA 2: VISÃO INDIVIDUAL POR TÉCNICO
    # ---------------------------------------------------------
    with tab_individual:
        if col_tecnico and col_tecnico in df_base.columns:
            tecnicos_unicos = sorted([str(t) for t in df_base[col_tecnico].dropna().unique() if str(t).strip() != ''])
            
            selecao_tecnico = st.selectbox("Selecione o Técnico:", ["-- Selecione um Técnico --"] + tecnicos_unicos)

            if selecao_tecnico != "-- Selecione um Técnico --":
                df_tec = df_base[df_base[col_tecnico].astype(str) == selecao_tecnico]
                tot_tec = len(df_tec)

                st.markdown(f"### Desempenho de: {selecao_tecnico}")
                
                # KPIs do Técnico
                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Chamados Atribuídos", tot_tec)
                
                # Chamados Concluídos do Técnico
                concluidos_tec = 0
                if col_status and col_status in df_tec.columns:
                    concluidos_tec = len(df_tec[df_tec[col_status].astype(str).str.contains('solucionado|fechado|closed|resolved|concluído', case=False, na=False)])
                tc2.metric("Chamados Concluídos", concluidos_tec)
                
                # Participação no Total
                part_tec = (tot_tec / total_chamados * 100) if total_chamados > 0 else 0
                tc3.metric("Participação na Área", f"{part_tec:.1f}%")

                st.divider()

                st.markdown("#### Detalhamento dos Chamados do Técnico")
                mostrar_dataframe(df_tec.loc[:, ~df_tec.columns.duplicated()])
            else:
                st.info("👆 Selecione um técnico acima para visualizar a performance individual detalhada.")
        else:
            st.warning("Coluna de técnico não encontrada na base de dados.")

# Alias de compatibilidade
def exibir(*args, **kwargs):
    renderizar(*args, **kwargs)