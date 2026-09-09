import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.ui_helpers import mostrar_dataframe

def exibir(df_periodo_sem_zabbix, cols, start_dt=None, end_dt=None, df_completo=None):
    df_ger = df_periodo_sem_zabbix.copy()

    dt_inicio_str = start_dt.strftime('%d/%m/%Y') if start_dt else "Início"
    dt_fim_str = end_dt.strftime('%d/%m/%Y') if end_dt else "Fim"

    st.subheader(f"🎯 Visão Gerencial (Targets, Desempenho por Setor & Categorias) ({dt_inicio_str} a {dt_fim_str})")

    if df_ger.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    TARGET_MENSAL_CHAMADOS, TARGET_MENSAL_INCIDENTES, TARGET_MENSAL_SLA = 1134, 164, 53

    # Mapeamento robusto de colunas caso necessário
    col_tipo = cols.get('tipo') or next((c for c in df_ger.columns if 'tipo' in str(c).lower()), None)
    col_cat = cols.get('cat') or next((c for c in df_ger.columns if 'cat' in str(c).lower()), None)
    col_grupo = cols.get('grupo') or next((c for c in df_ger.columns if 'grup' in str(c).lower() or 'equipe' in str(c).lower()), None)
    col_loc = cols.get('loc') or next((c for c in df_ger.columns if 'loc' in str(c).lower() or 'entidade' in str(c).lower()), None)
    col_sla = cols.get('sla_estourado') or next((c for c in df_ger.columns if 'sla' in str(c).lower() or 'estourado' in str(c).lower()), None)
    col_abertura = next((c for c in df_ger.columns if any(p in str(c).lower() for p in ['abertura', 'criacao', 'data_abertura', 'created'])), 'dt_abertura')

    # Garantir coluna AnoMes no df_ger
    if 'dt_abertura' in df_ger.columns and 'AnoMes' not in df_ger.columns:
        df_ger['AnoMes'] = df_ger['dt_abertura'].dt.to_period('M')
    elif col_abertura in df_ger.columns and 'AnoMes' not in df_ger.columns:
        df_ger['dt_abertura'] = pd.to_datetime(df_ger[col_abertura], errors='coerce')
        df_ger['AnoMes'] = df_ger['dt_abertura'].dt.to_period('M')

    if 'AnoMes' not in df_ger.columns:
        st.error("Coluna de data de abertura não encontrada para compilar o relatório gerencial.")
        return

    meses_periodo = sorted(df_ger['AnoMes'].dropna().unique())
    if not meses_periodo:
        st.warning("Nenhum mês válido encontrado para os registros.")
        return

    # Preparar base global para o cálculo do YoY (independentemente do filtro de período da tela)
    df_base_yoy = df_completo.copy() if df_completo is not None and not df_completo.empty else df_ger.copy()
    if 'dt_abertura' in df_base_yoy.columns and 'AnoMes' not in df_base_yoy.columns:
        df_base_yoy['dt_abertura'] = pd.to_datetime(df_base_yoy['dt_abertura'], errors='coerce')
        df_base_yoy['AnoMes'] = df_base_yoy['dt_abertura'].dt.to_period('M')

    # ---------------------------------------------------------
    # 1. TABELA DE TARGETS CUMULATIVOS M/M COM COMPLEMENTOS DE VARIAÇÃO
    # ---------------------------------------------------------
    dados_mm = []
    acc_ch = acc_inc = acc_sla = 0

    for i, m in enumerate(meses_periodo, start=1):
        df_m = df_ger[df_ger['AnoMes'] == m]
        ch_m = len(df_m)
        
        if col_tipo and col_tipo in df_m.columns:
            mask_inc = df_m[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)
        else:
            mask_inc = pd.Series(True, index=df_m.index)
            
        inc_m = mask_inc.sum()
        
        if col_sla and col_sla in df_m.columns:
            sla_m = df_m[mask_inc & (df_m[col_sla] == True)].shape[0]
        else:
            sla_m = 0

        acc_ch += ch_m
        acc_inc += inc_m
        acc_sla += sla_m
        
        tgt_ch, tgt_inc, tgt_sla = TARGET_MENSAL_CHAMADOS * i, TARGET_MENSAL_INCIDENTES * i, TARGET_MENSAL_SLA * i

        # Cálculo YoY utilizando a base completa para buscar o mesmo mês do ano anterior
        m_yoy = m - 12
        df_yoy = df_base_yoy[df_base_yoy['AnoMes'] == m_yoy] if 'AnoMes' in df_base_yoy.columns else pd.DataFrame()
        ch_yoy = len(df_yoy)
        
        if not df_yoy.empty and col_tipo and col_tipo in df_yoy.columns:
            mask_inc_yoy = df_yoy[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)
        else:
            mask_inc_yoy = pd.Series(True, index=df_yoy.index) if not df_yoy.empty else pd.Series(dtype=bool)
            
        inc_yoy = mask_inc_yoy.sum() if not df_yoy.empty else 0
        
        if not df_yoy.empty and col_sla and col_sla in df_yoy.columns:
            sla_yoy = df_yoy[mask_inc_yoy & (df_yoy[col_sla] == True)].shape[0]
        else:
            sla_yoy = 0

        # Cálculo MoM baseado no mês anterior dentro do próprio período filtrado
        if i > 1:
            m_anterior = meses_periodo[i - 2]
            df_ant = df_ger[df_ger['AnoMes'] == m_anterior]
            ch_ant = len(df_ant)
            inc_ant = df_ant[df_ant[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)].shape[0] if (col_tipo and col_tipo in df_ant.columns) else len(df_ant)
            sla_ant = df_ant[(df_ant[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)) & (df_ant[col_sla] == True)].shape[0] if (col_tipo and col_tipo in df_ant.columns and col_sla and col_sla in df_ant.columns) else 0
            
            mom_ch = f"{((ch_m - ch_ant) / ch_ant * 100):+.1f}%" if ch_ant > 0 else "0.0%"
            mom_inc = f"{((inc_m - inc_ant) / inc_ant * 100):+.1f}%" if inc_ant > 0 else "0.0%"
            mom_sla = f"{((sla_m - sla_ant) / sla_ant * 100):+.1f}%" if sla_ant > 0 else "0.0%"
        else:
            mom_ch, mom_inc, mom_sla = "-", "-", "-"

        # Variações YoY e Desvio contra o Target
        yoy_ch = f"{((ch_m - ch_yoy) / ch_yoy * 100):+.1f}%" if ch_yoy > 0 else "N/A"
        yoy_inc = f"{((inc_m - inc_yoy) / inc_yoy * 100):+.1f}%" if inc_yoy > 0 else "N/A"
        yoy_sla = f"{((sla_m - sla_yoy) / sla_yoy * 100):+.1f}%" if sla_yoy > 0 else "N/A"

        desv_mensal_ch = f"{((ch_m - TARGET_MENSAL_CHAMADOS) / TARGET_MENSAL_CHAMADOS * 100):+.1f}%"
        desv_mensal_inc = f"{((inc_m - TARGET_MENSAL_INCIDENTES) / TARGET_MENSAL_INCIDENTES * 100):+.1f}%"
        desv_mensal_sla = f"{((sla_m - TARGET_MENSAL_SLA) / TARGET_MENSAL_SLA * 100):+.1f}%"

        dados_mm.append({
            "Mês": m.strftime('%m/%Y'), 
            "Chamados": ch_m, 
            "Var. MoM (Cham.)": mom_ch,
            "Var. YoY (Cham.)": yoy_ch,
            "Desv. Target (Cham.)": desv_mensal_ch,
            "Cham. Acum.": acc_ch, 
            "Target Cham.": tgt_ch,
            "Desvio Acum. Cham.": f"{((acc_ch - tgt_ch) / tgt_ch * 100):+.1f}%" if tgt_ch > 0 else "0.0%", 
            
            "Incidentes": inc_m, 
            "Var. MoM (Inc.)": mom_inc,
            "Var. YoY (Inc.)": yoy_inc,
            "Desv. Target (Inc.)": desv_mensal_inc,
            "Incid. Acum.": acc_inc,
            "Target Inc.": tgt_inc, 
            "Desvio Acum. Inc.": f"{((acc_inc - tgt_inc) / tgt_inc * 100):+.1f}%" if tgt_inc > 0 else "0.0%",
            
            "SLA Estourado": sla_m, 
            "Var. MoM (SLA)": mom_sla,
            "Var. YoY (SLA)": yoy_sla,
            "Desv. Target (SLA)": desv_mensal_sla,
            "SLA Acum.": acc_sla, 
            "Target SLA": tgt_sla, 
            "Desvio Acum. SLA": f"{((acc_sla - tgt_sla) / tgt_sla * 100):+.1f}%" if tgt_sla > 0 else "0.0%"
        })

    df_targets = pd.DataFrame(dados_mm)
    st.markdown("### 📋 Tabela de Targets Cumulativos M/M & Variações (Sem Zabbix)")
    mostrar_dataframe(df_targets)

    st.divider()

    # ---------------------------------------------------------
    # 2. RATIO CHAMADOS x USUÁRIOS
    # ---------------------------------------------------------
    st.markdown("### 👥 Ratio Chamados x Usuários")
    c_in1, c_in2 = st.columns([1, 2])
    
    with c_in1:
        qtd_usuarios = st.number_input("Total de Usuários:", min_value=1, value=500, step=10, key="gerencial_qtd_users")

    df_targets["Ratio Mensal"] = (df_targets["Chamados"] / qtd_usuarios).round(2)
    df_targets["Ratio Acumulado"] = (df_targets["Cham. Acum."] / qtd_usuarios).round(2)

    with c_in2:
        r_atual = df_targets["Ratio Mensal"].iloc[-1] if not df_targets.empty else 0
        r_acum = df_targets["Ratio Acumulado"].iloc[-1] if not df_targets.empty else 0
        with st.container(border=True):
            mc1, mc2 = st.columns(2)
            mc1.metric("Ratio Mês Atual", f"{r_atual:.2f} chamados/user")
            mc2.metric("Ratio Acumulado", f"{r_acum:.2f} chamados/user")

    st.divider()

    # ---------------------------------------------------------
    # 3. METAS E VOLUMETRIA (GERAL & POR SETOR)
    # ---------------------------------------------------------
    st.markdown("### 🏢 Metas e Volumetria (Geral & Por Setor)")
    st.markdown("#### 📈 Volumetria Geral Agrupada por Mês")
    
    c_tg1, _ = st.columns([1, 2])
    with c_tg1:
        target_geral_input = st.number_input("Target Geral Mensal (Total):", min_value=0, value=TARGET_MENSAL_CHAMADOS, step=50, key="gerencial_target_geral")

    fig_geral = go.Figure()
    fig_geral.add_trace(go.Bar(x=df_targets['Mês'], y=df_targets['Chamados'], name='Total de Chamados', marker_color='#2ca02c', text=df_targets['Chamados'], textposition='auto'))
    fig_geral.add_trace(go.Scatter(x=df_targets['Mês'], y=[target_geral_input] * len(df_targets), mode='lines', name=f'Target Geral ({target_geral_input})', line=dict(color='red', width=3, dash='dash')))
    fig_geral.update_layout(title=dict(text="Evolução Geral Mensal vs. Target", font=dict(size=16)), xaxis_title="Mês/Ano", yaxis_title="Quantidade Total", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=20, r=20, t=60, b=40), height=400)
    st.plotly_chart(fig_geral, use_container_width=True)

    st.divider()
    st.markdown("#### 🎯 Volumetria Mensal por Setor / Grupo Técnico")

    if col_grupo and col_grupo in df_ger.columns:
        setores_disponiveis = sorted([str(s) for s in df_ger[col_grupo].dropna().unique() if str(s).strip() != ''])
        c_filtro, c_target = st.columns([2, 1])
        
        with c_filtro:
            setores_selecionados = st.multiselect("Filtrar Grupos Técnicos / Setores:", options=setores_disponiveis, default=[], key="gerencial_multiselect_setores")
        with c_target:
            target_setor_input = st.number_input("Target Mensal por Setor:", min_value=0, value=50, step=5, key="gerencial_target_setor")

        if setores_selecionados:
            todos_meses_str = [m.strftime('%m/%Y') for m in meses_periodo]
            df_filtrado_setor = df_ger[df_ger[col_grupo].astype(str).isin(setores_selecionados)].copy()
            fig_setor = go.Figure()

            for setor in setores_selecionados:
                df_sub = df_filtrado_setor[df_filtrado_setor[col_grupo].astype(str) == setor]
                qtd_por_mes = df_sub.groupby('AnoMes').size()
                y_values = [int(qtd_por_mes.get(m, 0)) for m in meses_periodo]
                fig_setor.add_trace(go.Bar(x=todos_meses_str, y=y_values, name=setor, text=y_values, textposition='auto'))

            fig_setor.add_trace(go.Scatter(x=todos_meses_str, y=[target_setor_input] * len(todos_meses_str), mode='lines', name=f'Target Mensal ({target_setor_input})', line=dict(color='red', width=3, dash='dash')))
            fig_setor.update_layout(title=dict(text="Evolução Mensal vs. Target por Setor", font=dict(size=16)), xaxis_title="Mês/Ano", yaxis_title="Quantidade", barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=20, r=20, t=60, b=40), height=450)
            st.plotly_chart(fig_setor, use_container_width=True)

            dados_tabela = [
                {
                    'Mês': m.strftime('%m/%Y'), 
                    'Setor': s, 
                    'Qtd Chamados': (qtd := int(df_filtrado_setor[(df_filtrado_setor['AnoMes'] == m) & (df_filtrado_setor[col_grupo].astype(str) == s)].shape[0])),
                    'Target': target_setor_input, 
                    'Status': "🔴 Acima da Meta" if qtd > target_setor_input else "🟢 Dentro da Meta"
                }
                for m in meses_periodo for s in setores_selecionados
            ]
            with st.expander("📄 Ver Tabela Resumo Mensal dos Setores"):
                mostrar_dataframe(pd.DataFrame(dados_tabela))
        else:
            st.info("Selecione pelo menos um grupo técnico no filtro acima para exibir o gráfico.")
    else:
        st.info("Coluna de grupo técnico/setor não identificada no dataset.")

    st.divider()

    # ---------------------------------------------------------
    # 4. DETALHAMENTO POR TOP CATEGORIAS E LOCALIZAÇÃO
    # ---------------------------------------------------------
    st.markdown("### 📊 Detalhamento por Top Categorias e Localização")
    tab_cat, tab_loc = st.tabs(["🏷️ Top Categorias", "📍 Localizações"])

    tot_geral_base = len(df_ger)

    with tab_cat:
        if col_cat and col_cat in df_ger.columns:
            top_cat = df_ger[col_cat].value_counts().head(10).reset_index()
            top_cat.columns = ['Categoria', 'Quantidade Total']
            top_cat['% da Demanda'] = ((top_cat['Quantidade Total'] / tot_geral_base) * 100).round(1).astype(str) + '%' if tot_geral_base > 0 else '0.0%'
            mostrar_dataframe(top_cat)
        else:
            st.info("Coluna de categoria não identificada.")

    with tab_loc:
        if col_loc and col_loc in df_ger.columns:
            top_loc = df_ger[col_loc].value_counts().head(10).reset_index()
            top_loc.columns = ['Localização', 'Quantidade Total']
            top_loc['% da Demanda'] = ((top_loc['Quantidade Total'] / tot_geral_base) * 100).round(1).astype(str) + '%' if tot_geral_base > 0 else '0.0%'
            mostrar_dataframe(top_loc)
        else:
            st.info("Coluna de localização/entidade não identificada.")