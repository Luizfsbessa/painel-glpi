import streamlit as st
import pandas as pd
import re
from utils.ui_helpers import mostrar_dataframe

def converter_duracao_para_segundos(texto):
    """Converte strings bagunçadas de duração do GLPI em segundos totais."""
    if pd.isna(texto) or not str(texto).strip():
        return 0
    
    t = str(texto).lower()
    horas = sum([int(x) for x in re.findall(r'(\d+)\s*(?:hora|horas|h)', t)])
    minutos = sum([int(x) for x in re.findall(r'(\d+)\s*(?:minuto|minutos|min|m)', t)])
    segundos = sum([int(x) for x in re.findall(r'(\d+)\s*(?:segundo|segundos|seg|s)', t)])
    
    return (horas * 3600) + (minutos * 60) + segundos

def formatar_segundos_para_humano(total_segundos):
    """Formata segundos totais em uma string limpa (ex: 2h 15m)."""
    if pd.isna(total_segundos) or total_segundos == 0:
        return "0m"
    
    h = int(total_segundos // 3600)
    m = int((total_segundos % 3600) // 60)
    
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"

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

    # 5. Top 10 Requerentes
    st.markdown(f"### 👥 Top 10 Requerentes com Mais Incidentes")
    if cols.get('req') and cols['req'] in df_f.columns:
        top_req = df_f[cols['req']].value_counts().head(10).reset_index()
        top_req.columns = ['Requerente', 'Volume']
        top_req['% do Total'] = ((top_req['Volume'] / tot_f) * 100).round(1).astype(str) + '%'
        mostrar_dataframe(top_req)

    st.divider()

    # 6. Detalhamento dos Chamados (Cabeçalhos com iniciais maiúsculas padronizadas)
    st.markdown("### 📄 Detalhamento dos Chamados")
    
    df_exibicao = df_f.copy()

    col_duracao_possivel = [c for c in df_exibicao.columns if 'tarefa' in c.lower() or 'dura' in c.lower()]
    if col_duracao_possivel:
        col_dur = col_duracao_possivel[0]
        df_exibicao['tarefas_duracao_segundos'] = df_exibicao[col_dur].apply(converter_duracao_para_segundos)
        df_exibicao['Tempo Total de Tarefas'] = df_exibicao['tarefas_duracao_segundos'].apply(formatar_segundos_para_humano)

    def achar_coluna(posstermps):
        for pt in posstermps:
            for c in df_exibicao.columns:
                if c.lower().strip() == pt.lower().strip():
                    return c
        return None

    col_id = cols.get('id') or achar_coluna(['id', 'chamado', 'id do chamado'])
    
    mapeamento_desejado = [
        ('ID', col_id),
        ('Título', achar_coluna(['titulo', 'título', 'assunto'])),
        ('Entidade', achar_coluna(['entidade'])),
        ('Categoria', achar_coluna(['categoria'])),
        ('Prioridade', achar_coluna(['prioridade', 'criticidade'])),
        ('Requerente', achar_coluna(['requerente', 'autor'])),
        ('Data de Abertura', achar_coluna(['data de abertura', 'data abertura', 'abertura'])),
        ('Data da Solução', achar_coluna(['data da solução', 'data solucao', 'solução', 'solucao'])),
        ('Status', achar_coluna(['status', 'estado'])),
        ('Atribuído - Grupo Técnico', achar_coluna(['atribuído - grupo técnico', 'grupo técnico', 'grupo', 'atribuido - grupo tecnico'])),
        ('Localização', achar_coluna(['localização', 'localizacao', 'local'])),
        ('Tempo Total de Tarefas', achar_coluna(['Tempo Total de Tarefas'])),
        ('Sla_Estourado', achar_coluna(['sla_estourado', 'estourado', 'sla estourado']))
    ]

    renomear_dict = {}
    colunas_presentes = []
    
    for nome_bonito, coluna_real in mapeamento_desejado:
        if coluna_real and coluna_real in df_exibicao.columns:
            renomear_dict[coluna_real] = nome_bonito
            colunas_presentes.append(coluna_real)

    df_exibicao = df_exibicao[colunas_presentes].rename(columns=renomear_dict)

    if 'ID' in df_exibicao.columns:
        df_exibicao['ID'] = df_exibicao['ID'].astype(str).str.replace(r'\.0$', '', regex=True)
        url_base = "https://glpi.dominio.local/ssi/front/ticket.form.php?id="
        df_exibicao['ID'] = url_base + df_exibicao['ID']
        
        mostrar_dataframe(
            df_exibicao, 
            height=400,
            column_config={
                'ID': st.column_config.LinkColumn(
                    "ID",
                    help="Clique para abrir o chamado diretamente no GLPI em uma nova aba",
                    display_text=r"id=(.*)"
                )
            }
        )
    else:
        mostrar_dataframe(df_exibicao, height=400)


def renderizar(df_periodo_sem_zabbix, cols, start_dt, end_dt):
    if cols.get('tipo') and cols['tipo'] in df_periodo_sem_zabbix.columns:
        df_inc = df_periodo_sem_zabbix[
            df_periodo_sem_zabbix[cols['tipo']].astype(str).str.contains('Incidente', case=False, na=False)
        ].copy()
    else:
        df_inc = df_periodo_sem_zabbix.copy()

    # 1. SELETOR GLOBAL DE GRUPO TÉCNICO NO TOPO (LOGO ABAIXO DO TÍTULO)
    st.title("🚨 Relatório de Incidentes & Cumprimento de SLA")
    
    if cols.get('grupo') and cols['grupo'] in df_inc.columns:
        grupos = sorted([str(g) for g in df_inc[cols['grupo']].dropna().unique() if str(g).strip() != ''])
        grupo_geral_sel = st.selectbox(
            "Selecione um Grupo Técnico (Filtro Geral):",
            ["Todos os Grupos"] + grupos,
            key="sel_grupo_geral_incidentes"
        )
        df_inc_filtrado = df_inc if grupo_geral_sel == "Todos os Grupos" else df_inc[df_inc[cols['grupo']] == grupo_geral_sel]
    else:
        grupo_geral_sel = "Todos os Grupos"
        df_inc_filtrado = df_inc

    tot = len(df_inc_filtrado)
    if 'sla_estourado' in df_inc_filtrado.columns and tot > 0:
        estourados = len(df_inc_filtrado[df_inc_filtrado['sla_estourado'] == True])
        dentro_sla = tot - estourados
        conformidade = (dentro_sla / tot) * 100
    else:
        dentro_sla = tot
        estourados = 0
        conformidade = 100.0

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