import streamlit as st
import pandas as pd
from utils.ui_helpers import mostrar_dataframe

def renderizar_conteudo_analitico(df, cols, key_prefix=""):
    if df.empty:
        st.info("Nenhum registro encontrado para os filtros selecionados.")
        return

    # 1. SELETOR DE GRUPO TÉCNICO NO TOPO
    st.markdown("### 🎯 Filtro por Grupo Técnico")
    if cols.get('grupo') and cols['grupo'] in df.columns:
        grupos = sorted([str(g) for g in df[cols['grupo']].dropna().unique() if str(g).strip() != ''])
        grupo_sel = st.selectbox(
            "Selecione um Grupo Técnico:",
            ["Todos os Grupos"] + grupos,
            key=f"sel_grupo_{key_prefix}"
        )
        
        df_f = df if grupo_sel == "Todos os Grupos" else df[df[cols['grupo']] == grupo_sel]
    else:
        grupo_sel = "Todos os Grupos"
        df_f = df

    tot_f = len(df_f)

    if df_f.empty:
        st.warning("Nenhum registro encontrado para este Grupo Técnico.")
        return

    st.divider()

    # 2. Resumo de Indicadores
    st.markdown("### 📊 Resumo de Indicadores")
    c_m, c_p, c_g = st.columns([1, 1.2, 1.8])

    with c_m:
        with st.container(border=True):
            st.metric("Total de Incidentes", f"{tot_f:,}".replace(",", "."))

    with c_p:
        st.markdown("**Prioridades Atendidas**")
        if cols.get('prio') and cols['prio'] in df_f.columns:
            df_prio = df_f[cols['prio']].value_counts().reset_index()
            df_prio.columns = ['Prioridade', 'Qtd']
            mostrar_dataframe(df_prio)

    with c_g:
        st.markdown("**Visão por Grupo Técnico**")
        if cols.get('grupo') and cols['grupo'] in df_f.columns:
            df_grupo = df_f[cols['grupo']].value_counts().reset_index()
            df_grupo.columns = ['Grupo Técnico', 'Qtd']
            mostrar_dataframe(df_grupo)

    st.divider()

    # 3. Análise de Criticidade
    st.markdown("### ⚠️ Análise de Criticidade")
    if cols.get('prio') and cols['prio'] in df_f.columns:
        df_crit = df_f[cols['prio']].value_counts().reset_index()
        df_crit.columns = ['Nível de Criticidade', 'Chamados Atendidos']
        df_crit['Proporção (%)'] = ((df_crit['Chamados Atendidos'] / tot_f) * 100).round(1).astype(str) + '%'
        mostrar_dataframe(df_crit)

    st.divider()

    # 4. Top 10 Categorias de Incidentes
    st.markdown("### 🏷️ Top 10 Categorias de Incidentes")
    if cols.get('cat') and cols['cat'] in df_f.columns:
        top_cat = df_f[cols['cat']].value_counts().head(10).reset_index()
        top_cat.columns = ['Categoria', 'Volume']
        top_cat['% do Total'] = ((top_cat['Volume'] / tot_f) * 100).round(1).astype(str) + '%'
        mostrar_dataframe(top_cat)

    st.divider()

    # 5. Top 10 Requerentes (Forçando uso estrito de df_f)
    st.markdown(f"### 👥 Top 10 Requerentes com Mais Incidentes")
    if cols.get('req') and cols['req'] in df_f.columns:
        top_req = df_f[cols['req']].value_counts().head(10).reset_index()
        top_req.columns = ['Requerente', 'Volume']
        top_req['% do Total'] = ((top_req['Volume'] / tot_f) * 100).round(1).astype(str) + '%'
        mostrar_dataframe(top_req)

    st.divider()

    # 6. Detalhamento dos Chamados
    st.markdown("### 📄 Detalhamento dos Chamados")
    mostrar_dataframe(df_f, height=400)


def renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt):
    if cols.get('tipo') and cols['tipo'] in df_periodo_sem_zabbix.columns:
        df_inc = df_periodo_sem_zabbix[
            df_periodo_sem_zabbix[cols['tipo']].astype(str).str.contains('Incidente', case=False, na=False)
        ].copy()
    else:
        df_inc = df_periodo_sem_zabbix.copy()

    tot = len(df_inc)
    if 'sla_estourado' in df_inc.columns and tot > 0:
        estourados = len(df_inc[df_inc['sla_estourado'] == True])
        dentro_sla = tot - estourados
        conformidade = (dentro_sla / tot) * 100
    else:
        dentro_sla = tot
        estourados = 0
        conformidade = 100.0

    st.title("🚨 Relatório de Incidentes & Cumprimento de SLA")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Incidentes", f"{tot:,}".replace(",", "."))
    k2.metric("Dentro do SLA", f"{dentro_sla:,}".replace(",", "."))
    k3.metric("SLA Estourado", f"{estourados:,}".replace(",", "."))
    k4.metric("Taxa de Conformidade SLA", f"{conformidade:.1f}%")

    st.divider()

    tab_todos, tab_estourados = st.tabs(["📋 Todos os Incidentes", "🚨 Incidentes com SLA Estourado"])

    with tab_todos:
        renderizar_conteudo_analitico(df_inc, cols, key_prefix="todos")

    with tab_estourados:
        df_est = df_inc[df_inc['sla_estourado'] == True] if 'sla_estourado' in df_inc.columns else pd.DataFrame()
        renderizar_conteudo_analitico(df_est, cols, key_prefix="estourados")

def renderizar_incidentes_sla(*args, **kwargs):
    return renderizar(*args, **kwargs)

def exibir(*args, **kwargs):
    return renderizar(*args, **kwargs)