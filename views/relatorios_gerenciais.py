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

    TARGETS_POR_GRUPO = {
        "bi": 11,
        "ti > bi": 11,
        "desenvolvimento": 194,
        "suporte": 724,
        "governança": 86,
        "governanca": 86,
        "infraestrutura de ti": 61,
        "segurança de ti": 22,
        "seguranca de ti": 22
    }

    col_tipo = cols.get('tipo') or next((c for c in df_ger.columns if 'tipo' in str(c).lower()), None)
    col_cat = cols.get('cat') or next((c for c in df_ger.columns if 'cat' in str(c).lower()), None)
    col_grupo = cols.get('grupo') or next((c for c in df_ger.columns if 'grup' in str(c).lower() or 'equipe' in str(c).lower()), None)
    col_loc = cols.get('loc') or next((c for c in df_ger.columns if 'loc' in str(c).lower() or 'entidade' in str(c).lower()), None)
    col_sla = cols.get('sla_estourado') or next((c for c in df_ger.columns if 'sla' in str(c).lower() or 'estourado' in str(c).lower()), None)
    col_abertura = next((c for c in df_ger.columns if any(p in str(c).lower() for p in ['abertura', 'criacao', 'data_abertura', 'created'])), 'dt_abertura')

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

    df_base_yoy = None
    if df_completo is not None and not df_completo.empty:
        df_base_yoy = df_completo.copy()
    elif 'df_bruto_global' in st.session_state and not st.session_state['df_bruto_global'].empty:
        df_base_yoy = st.session_state['df_bruto_global'].copy()
    
    if df_base_yoy is None or df_base_yoy.empty:
        df_base_yoy = df_ger.copy()

    if 'dt_abertura' in df_base_yoy.columns and 'AnoMes' not in df_base_yoy.columns:
        df_base_yoy['dt_abertura'] = pd.to_datetime(df_base_yoy['dt_abertura'], errors='coerce')
        df_base_yoy['AnoMes'] = df_base_yoy['dt_abertura'].dt.to_period('M')

    # ---------------------------------------------------------
    # 1. TABELA DE TARGETS CUMULATIVOS M/M SEGMENTADA POR BLOCOS
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

        if i > 1:
            m_anterior = meses_periodo[i - 2]
            df_ant = df_ger[df_ger['AnoMes'] == m_anterior]
        else:
            m_anterior = m - 1
            df_ant = df_base_yoy[df_base_yoy['AnoMes'] == m_anterior] if 'AnoMes' in df_base_yoy.columns else pd.DataFrame()

        ch_ant = len(df_ant)
        inc_ant = df_ant[df_ant[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)].shape[0] if (not df_ant.empty and col_tipo and col_tipo in df_ant.columns) else len(df_ant)
        sla_ant = df_ant[(df_ant[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)) & (df_ant[col_sla] == True)].shape[0] if (not df_ant.empty and col_tipo and col_tipo in df_ant.columns and col_sla and col_sla in df_ant.columns) else 0

        # Variações Chamados
        mom_ch = f"{((ch_m - ch_ant) / ch_ant * 100):+.1f}%" if ch_ant > 0 else "0.0%"
        yoy_ch = f"{((ch_m - ch_yoy) / ch_yoy * 100):+.1f}%" if ch_yoy > 0 else "N/A"
        desv_ch = f"{((ch_m - TARGET_MENSAL_CHAMADOS) / TARGET_MENSAL_CHAMADOS * 100):+.1f}%"
        desv_acum_ch = f"{((acc_ch - tgt_ch) / tgt_ch * 100):+.1f}%" if tgt_ch > 0 else "0.0%"

        # Variações Incidentes
        mom_inc = f"{((inc_m - inc_ant) / inc_ant * 100):+.1f}%" if inc_ant > 0 else "0.0%"
        yoy_inc = f"{((inc_m - inc_yoy) / inc_yoy * 100):+.1f}%" if inc_yoy > 0 else "N/A"
        desv_inc = f"{((inc_m - TARGET_MENSAL_INCIDENTES) / TARGET_MENSAL_INCIDENTES * 100):+.1f}%"
        desv_acum_inc = f"{((acc_inc - tgt_inc) / tgt_inc * 100):+.1f}%" if tgt_inc > 0 else "0.0%"

        # Variações SLA
        mom_sla = f"{((sla_m - sla_ant) / sla_ant * 100):+.1f}%" if sla_ant > 0 else "0.0%"
        yoy_sla = f"{((sla_m - sla_yoy) / sla_yoy * 100):+.1f}%" if sla_yoy > 0 else "N/A"
        desv_sla = f"{((sla_m - TARGET_MENSAL_SLA) / TARGET_MENSAL_SLA * 100):+.1f}%"
        desv_acum_sla = f"{((acc_sla - tgt_sla) / tgt_sla * 100):+.1f}%" if tgt_sla > 0 else "0.0%"

        dados_mm.append({
            ("Mês", ""): m.strftime('%m/%Y'),
            
            ("Chamados", "Qtd"): ch_m, 
            ("Chamados", "MoM"): mom_ch,
            ("Chamados", "YoY"): yoy_ch,
            ("Chamados", "Desvio"): desv_ch,
            ("Chamados", "Acumulado"): acc_ch, 
            ("Chamados", "Target"): tgt_ch,
            ("Chamados", "Desv. Acum."): desv_acum_ch,
            
            ("Incidentes", "Qtd"): inc_m, 
            ("Incidentes", "MoM"): mom_inc,
            ("Incidentes", "YoY"): yoy_inc,
            ("Incidentes", "Desvio"): desv_inc,
            ("Incidentes", "Acumulado"): acc_inc,
            ("Incidentes", "Target"): tgt_inc, 
            ("Incidentes", "Desv. Acum."): desv_acum_inc,
            
            ("SLA Estourado", "Qtd"): sla_m, 
            ("SLA Estourado", "MoM"): mom_sla,
            ("SLA Estourado", "YoY"): yoy_sla,
            ("SLA Estourado", "Desvio"): desv_sla,
            ("SLA Estourado", "Acumulado"): acc_sla, 
            ("SLA Estourado", "Target"): tgt_sla, 
            ("SLA Estourado", "Desv. Acum."): desv_acum_sla
        })

    df_targets = pd.DataFrame(dados_mm)
    df_targets.columns = pd.MultiIndex.from_tuples(df_targets.columns)

    def centralizar_tabela(s):
        return 'text-align: center; vertical-align: middle;'

    st.markdown("### 📋 Tabela Consolidada por Blocos (Chamados, Incidentes e SLA)")
    
    html_tabela = df_targets.to_html(index=False, classes="table-centralizada")
    
    codigo_html = f"""
    <style>
        .table-centralizada {{
            width: 100%;
            border-collapse: collapse;
            text-align: center;
            font-family: sans-serif;
            font-size: 13px;
        }}
        .table-centralizada th, .table-centralizada td {{
            text-align: center !important;
            vertical-align: middle !important;
            padding: 8px 6px;
            border: 1px solid #d6d6d6;
        }}
        .table-centralizada th {{
            background-color: #f0f2f6;
            font-weight: bold;
            color: #31333F;
        }}
        .table-centralizada tr:nth-child(even) {{
            background-color: #fafafa;
        }}
    </style>
    {html_tabela}
    """
    import streamlit.components.v1 as components
    components.html(codigo_html, height=380, scrolling=True)

    st.divider()

    # ---------------------------------------------------------
    # 2. RATIO CHAMADOS x USUÁRIOS
    # ---------------------------------------------------------
    st.markdown("### 👥 Ratio Chamados x Usuários")
    c_in1, c_in2 = st.columns([1, 2])
    
    with c_in1:
        qtd_usuarios = st.number_input("Total de Usuários:", min_value=1, value=500, step=10, key="gerencial_qtd_users")

    ratio_mensal = (df_targets[("Chamados", "Qtd")] / qtd_usuarios).round(2)
    ratio_acum = (df_targets[("Chamados", "Acumulado")] / qtd_usuarios).round(2)

    with c_in2:
        r_atual = ratio_mensal.iloc[-1] if not ratio_mensal.empty else 0
        r_acum = ratio_acum.iloc[-1] if not ratio_acum.empty else 0
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

    meses_str_geral = [m.strftime('%m/%Y') for m in meses_periodo]
    qtos_chamados_geral = df_targets[("Chamados", "Qtd")].tolist()

    fig_geral = go.Figure()
    fig_geral.add_trace(go.Bar(x=meses_str_geral, y=qtos_chamados_geral, name='Total de Chamados', marker_color='#2ca02c', text=qtos_chamados_geral, textposition='auto'))
    fig_geral.add_trace(go.Scatter(x=meses_str_geral, y=[target_geral_input] * len(meses_str_geral), mode='lines', name=f'Target Geral ({target_geral_input})', line=dict(color='red', width=3, dash='dash')))
    fig_geral.update_layout(title=dict(text="Evolução Geral Mensal vs. Target", font=dict(size=16)), xaxis_title="Mês/Ano", yaxis_title="Quantidade Total", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=20, r=20, t=60, b=40), height=400)
    st.plotly_chart(fig_geral, use_container_width=True)

    st.divider()
    st.markdown("#### 🎯 Volumetria Mensal por Setor / Grupo Técnico")

    if col_grupo and col_grupo in df_ger.columns:
        setores_disponiveis = sorted([str(s) for s in df_ger[col_grupo].dropna().unique() if str(s).strip() != ''])
        
        c_filtro, _ = st.columns([2, 1])
        with c_filtro:
            setores_selecionados = st.multiselect("Filtrar Grupos Técnicos / Setores:", options=setores_disponiveis, default=[], key="gerencial_multiselect_setores")

        if setores_selecionados:
            todos_meses_str = [m.strftime('%m/%Y') for m in meses_periodo]
            df_filtrado_setor = df_ger[df_ger[col_grupo].astype(str).isin(setores_selecionados)].copy()
            fig_setor = go.Figure()

            dados_tabela = []
            for setor in setores_selecionados:
                df_sub = df_filtrado_setor[df_filtrado_setor[col_grupo].astype(str) == setor]
                qtd_por_mes = df_sub.groupby('AnoMes').size()
                y_values = [int(qtd_por_mes.get(m, 0)) for m in meses_periodo]
                fig_setor.add_trace(go.Bar(x=todos_meses_str, y=y_values, name=setor, text=y_values, textposition='auto'))

                setor_key_clean = setor.strip().lower()
                target_especifico = TARGETS_POR_GRUPO.get(setor_key_clean, 50)

                for m in meses_periodo:
                    qtd_m = int(qtd_por_mes.get(m, 0))
                    dados_tabela.append({
                        'Mês': m.strftime('%m/%Y'), 
                        'Setor': setor, 
                        'Qtd Chamados': qtd_m,
                        'Target': target_especifico, 
                        'Status': "🔴 Acima da Meta" if qtd_m > target_especifico else "🟢 Dentro da Meta"
                    })

            for setor in setores_selecionados:
                setor_key_clean = setor.strip().lower()
                target_especifico = TARGETS_POR_GRUPO.get(setor_key_clean, 50)
                fig_setor.add_trace(go.Scatter(
                    x=todos_meses_str, 
                    y=[target_especifico] * len(todos_meses_str), 
                    mode='lines', 
                    name=f'Target ({setor}: {target_especifico})', 
                    line=dict(color='#ff7f0e', width=2, dash='dash')
                ))

            fig_setor.update_layout(title=dict(text="Evolução Mensal vs. Target Individual por Setor", font=dict(size=16)), xaxis_title="Mês/Ano", yaxis_title="Quantidade", barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=20, r=20, t=60, b=40), height=480)
            st.plotly_chart(fig_setor, use_container_width=True)

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