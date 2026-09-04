import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, date
from utils.ui_helpers import mostrar_dataframe

def renderizar(*args, **kwargs):
    df_base = None
    for arg in args:
        if isinstance(arg, pd.DataFrame):
            df_base = arg
            break
    if df_base is None:
        df_base = kwargs.get('df_completo') or kwargs.get('df_periodo_sem_zabbix') or kwargs.get('df_raw')

    if df_base is None or df_base.empty:
        st.warning("⚠️ Nenhum dado disponível para o comparativo.")
        return

    st.subheader("🔄 Comparativo Temporal de Desempenho (YoY / PoP)")

    if 'is_zabbix' in df_base.columns:
        df_base_comp = df_base[~df_base['is_zabbix']].copy()
    else:
        df_base_comp = df_base.copy()

    if df_base_comp.empty:
        st.warning("⚠️ Nenhum dado disponível após filtragem.")
        return

    col_data = next((c for c in df_base_comp.columns if any(k in str(c).lower() for k in ['data', 'date', 'abertura', 'created'])), None)
    if not col_data:
        st.error("Coluna de data não encontrada na base de dados.")
        return

    df_base_comp['dt_abertura'] = pd.to_datetime(df_base_comp[col_data], errors='coerce')
    df_base_comp = df_base_comp.dropna(subset=['dt_abertura'])

    dt_validas_comp = df_base_comp['dt_abertura'].dropna()
    min_date = date(2020, 1, 1)
    max_date = date(2026, 12, 31)

    st.markdown("#### 📅 Seleção dos Períodos para Comparação")

    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.info("📌 **Período A (Base / Anterior)**")
        data_ini_a = st.date_input("Início Período A:", value=None, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_a_ini")
        data_fim_a = st.date_input("Fim Período A:", value=None, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_a_fim")

    with c_p2:
        st.success("📌 **Período B (Recent / Mais Atual)**")
        data_ini_b = st.date_input("Início Período B:", value=None, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_b_ini")
        data_fim_b = st.date_input("Fim Período B:", value=None, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_b_fim")

    if not data_ini_a or not data_fim_a or not data_ini_b or not data_fim_b:
        st.info("ℹ️ Preencha todas as datas de início e fim para ambos os períodos para gerar o comparativo.")
        return

    start_a = pd.Timestamp.combine(data_ini_a, time(0, 0, 0))
    end_a = pd.Timestamp.combine(data_fim_a, time(23, 59, 59))
    start_b = pd.Timestamp.combine(data_ini_b, time(0, 0, 0))
    end_b = pd.Timestamp.combine(data_fim_b, time(23, 59, 59))

    df_per_a = df_base_comp[(df_base_comp['dt_abertura'] >= start_a) & (df_base_comp['dt_abertura'] <= end_a)].copy()
    df_per_b = df_base_comp[(df_base_comp['dt_abertura'] >= start_b) & (df_base_comp['dt_abertura'] <= end_b)].copy()

    if df_per_a.empty and df_per_b.empty:
        st.warning("⚠️ Nenhum chamado encontrado para os períodos selecionados.")
        return

    st.divider()
    st.markdown("### 📊 Visão Geral Consolidada da Comparação")
    
    tot_a, tot_b = len(df_per_a), len(df_per_b)
    dias_a = max((data_fim_a - data_ini_a).days + 1, 1)
    dias_b = max((data_fim_b - data_ini_b).days + 1, 1)
    media_a = tot_a / dias_a
    media_b = tot_b / dias_b
    var_vol = ((tot_b - tot_a) / tot_a * 100) if tot_a > 0 else 0.0

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(f"Volumetria Período A ({data_ini_a.strftime('%d/%m/%Y')} a {data_fim_a.strftime('%d/%m/%Y')})", f"{tot_a:,}".replace(",", "."), delta=f"{dias_a} dias")
    with col_m2:
        st.metric(f"Volumetria Período B ({data_ini_b.strftime('%d/%m/%Y')} a {data_fim_b.strftime('%d/%m/%Y')})", f"{tot_b:,}".replace(",", "."), delta=f"{var_vol:+.1f}% vs Período A", delta_color="normal" if var_vol <= 0 else "inverse")
    with col_m3:
        st.metric("Média Diária (A vs B)", f"{media_a:.1f} / {media_b:.1f}", delta=f"{media_b - media_a:+.1f} chamados/dia")

    st.divider()
    st.markdown("### 📈 Comparativo de Volumetria Total Mês a Mês")

    df_per_a['MesAno'] = df_per_a['dt_abertura'].dt.to_period('M')
    df_per_b['MesAno'] = df_per_b['dt_abertura'].dt.to_period('M')

    g_a = df_per_a.groupby('MesAno').size()
    g_b = df_per_b.groupby('MesAno').size()

    fig_comp = go.Figure()
    if not g_a.empty:
        fig_comp.add_trace(go.Bar(
            x=[str(p) for p in g_a.index], y=g_a.values,
            name=f"Período A ({data_ini_a.strftime('%d/%m/%Y')} a {data_fim_a.strftime('%d/%m/%Y')})",
            marker_color='#2b5c8f', text=g_a.values, textposition='auto'
        ))
    if not g_b.empty:
        fig_comp.add_trace(go.Bar(
            x=[str(p) for p in g_b.index], y=g_b.values,
            name=f"Período B ({data_ini_b.strftime('%d/%m/%Y')} a {data_fim_b.strftime('%d/%m/%Y')})",
            marker_color='#2e7d32', text=g_b.values, textposition='auto'
        ))

    fig_comp.update_layout(
        barmode='group',
        title=dict(text="Volumetria Comparativa Mensal", font=dict(size=16)),
        xaxis_title="Período", yaxis_title="Quantidade de Chamados",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=40), height=420
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    st.divider()
    st.markdown("### 📋 Histórico por Top 10 Categorias")

    col_cat = next((c for c in df_base_comp.columns if any(k in str(c).lower() for k in ['categoria', 'category'])), None)
    if col_cat:
        top_cats_b = df_per_b[col_cat].dropna().value_counts().head(10).index.tolist()

        label_a = f"{data_ini_a.strftime('%b/%y').upper()}" if data_ini_a.month == data_fim_a.month else f"{data_ini_a.strftime('%d/%m')} - {data_fim_a.strftime('%d/%m')}"
        label_b = f"{data_ini_b.strftime('%b/%y').upper()}" if data_ini_b.month == data_fim_b.month else f"{data_ini_b.strftime('%d/%m')} - {data_fim_b.strftime('%d/%m')}"

        linhas_comp = []
        tot_geral_b = len(df_per_b)
        tot_geral_base = len(df_base_comp)

        for cat in top_cats_b:
            q_a = len(df_per_a[df_per_a[col_cat] == cat])
            q_b = len(df_per_b[df_per_b[col_cat] == cat])
            dif = q_b - q_a
            pct_var = (dif / q_a * 100) if q_a > 0 else (100.0 if q_b > 0 else 0.0)
            
            pct_backlog = (q_b / tot_geral_b * 100) if tot_geral_b > 0 else 0.0
            pct_bl_total = (q_b / tot_geral_base * 100) if tot_geral_base > 0 else 0.0

            linhas_comp.append({
                "Categoria": str(cat),
                label_a: q_a,
                label_b: q_b,
                "↑ Y/Y %": f"{pct_var:+.2f}%" if q_a > 0 else ("+100.00%" if q_b > 0 else "0.00%"),
                "% Backlog": f"{pct_backlog:.2f}%",
                "%BL 2026": f"{pct_bl_total:.2f}%"
            })

        df_tabela_comp = pd.DataFrame(linhas_comp)
        mostrar_dataframe(df_tabela_comp, height=450)
    else:
        st.info("Coluna de categoria não identificada para gerar o comparativo.")

def exibir(*args, **kwargs):
    renderizar(*args, **kwargs)