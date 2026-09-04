import streamlit as st
import pandas as pd
from utils.ui_helpers import mostrar_dataframe

def renderizar(df_periodo_sem_zabbix, cols, start_dt=None, end_dt=None, df_completo=None):
    # Se df_completo não foi enviado, tenta usar a variável global ou assume o recebido
    df_full = df_completo if df_completo is not None else df_periodo_sem_zabbix
    df_humana = df_periodo_sem_zabbix.copy()

    dt_inicio_str = start_dt.strftime('%d/%m/%Y') if start_dt else "Início"
    dt_fim_str = end_dt.strftime('%d/%m/%Y') if end_dt else "Fim"
    
    st.subheader(f"📈 Dashboard Executivo - Visão Geral ({dt_inicio_str} a {dt_fim_str})")

    if df_full.empty:
        st.info("Nenhum dado encontrado para o período selecionado.")
        return

    # Mapeamento dinâmico de colunas
    col_tipo = cols.get('tipo') or next((c for c in df_full.columns if 'tipo' in str(c).lower()), None)
    col_cat = cols.get('cat') or next((c for c in df_full.columns if 'cat' in str(c).lower()), None)
    col_prio = cols.get('prioridade') or next((c for c in df_full.columns if 'prio' in str(c).lower()), None)
    col_tec = cols.get('tecnico') or next((c for c in df_full.columns if 'tecn' in str(c).lower() or 'atribu' in str(c).lower()), None)
    col_req = cols.get('requerente') or next((c for c in df_full.columns if 'req' in str(c).lower() or 'usuario' in str(c).lower()), None)
    col_status = cols.get('status') or next((c for c in df_full.columns if 'status' in str(c).lower() or 'estado' in str(c).lower()), None)
    col_sla = cols.get('sla_estourado') or next((c for c in df_full.columns if 'sla' in str(c).lower() or 'estourado' in str(c).lower()), None)
    col_titulo = cols.get('titulo') or next((c for c in df_full.columns if any(p in str(c).lower() for p in ['tit', 'assunto', 'alerta', 'nome', 'desc'])), None)

    # Identificação do Zabbix no DataFrame Completo
    df_zabbix = pd.DataFrame()
    for col_check in [col_tec, col_req, 'Requerente', 'Técnico', 'Atribuído a']:
        if col_check and col_check in df_full.columns:
            matches = df_full[df_full[col_check].astype(str).str.contains('Zabbix', case=False, na=False)]
            if not matches.empty:
                df_zabbix = matches
                break

    tot_volumetria = len(df_full)
    tot_equipe = len(df_humana)
    tot_zabbix = len(df_zabbix)
    pct_zabbix = round((tot_zabbix / tot_volumetria) * 100, 1) if tot_volumetria > 0 else 0.0

    # Backlog
    if col_status and col_status in df_full.columns:
        df_backlog = df_full[~df_full[col_status].astype(str).isin(['Solucionado', 'Fechado', 'Closed', 'Resolved'])]
        tot_backlog = len(df_backlog)
    else:
        tot_backlog = 0

    # SLA Incidentes
    df_inc = df_humana[df_humana[col_tipo].astype(str).str.contains('Incidente', case=False, na=False)] if col_tipo and col_tipo in df_humana.columns else df_humana
    if col_sla and col_sla in df_inc.columns and len(df_inc) > 0:
        sla_cumprido = len(df_inc[df_inc[col_sla] == False])
        pct_sla = round((sla_cumprido / len(df_inc)) * 100, 1)
    else:
        pct_sla = 0.0

    # --- 1. CARDS DE KPI SUPERIORES ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de Volumetria", f"{tot_volumetria:,}".replace(",", "."))
    c2.metric("Atendimentos Equipe", f"{tot_equipe:,}".replace(",", "."))
    c3.metric("SLA de Incidentes", f"{pct_sla}%")
    c4.metric("Alertas Zabbix", f"{tot_zabbix:,}".replace(",", "."), delta=f"↑ {pct_zabbix}% do total", delta_color="off")
    c5.metric("Backlog / Em Aberto", f"{tot_backlog:,}".replace(",", "."))

    st.divider()

    # --- 2. SEÇÃO 1: TOP CATEGORIAS | INCIDENTES POR PRIORIDADE ---
    col_left1, col_right1 = st.columns(2)

    with col_left1:
        st.markdown("### 🏷️ Top 5 Categorias Mais Ofensivas")
        if col_cat and col_cat in df_humana.columns:
            top_cat = df_humana[col_cat].value_counts().head(5).reset_index()
            top_cat.columns = ['Categoria', 'Volume']
            top_cat['% da Demanda'] = ((top_cat['Volume'] / tot_equipe) * 100).round(1).astype(str) + '%'
            mostrar_dataframe(top_cat)

    with col_right1:
        st.markdown("### 🚨 Incidentes por Prioridade")
        if col_prio and col_prio in df_inc.columns:
            df_prio = df_inc.groupby(col_prio).apply(
                lambda x: pd.Series({
                    'Qtd Incidentes': len(x),
                    'SLA Estourado': len(x[x[col_sla] == True]) if col_sla and col_sla in x.columns else 0
                })
            ).reset_index()

            ordem_prio = {'Alta': 1, 'Baixa': 2, 'Média': 3, 'Muito alta': 4, 'Critica': 5, 'Crítica': 5}
            df_prio['ordem'] = df_prio[col_prio].map(lambda v: ordem_prio.get(str(v), 99))
            df_prio = df_prio.sort_values('ordem').drop(columns=['ordem'])
            df_prio.rename(columns={col_prio: 'Prioridade'}, inplace=True)
            mostrar_dataframe(df_prio)

    st.divider()

    # --- 3. SEÇÃO 2: TOP ALERTAS ZABBIX | RANKING DE ATENDIMENTO DA EQUIPE ---
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.markdown("### 🎯 Top Alertas Zabbix Recorrentes")
        
        if not df_zabbix.empty:
            # Tenta encontrar a coluna de título/assunto/descrição no df_zabbix
            col_alerta = None
            
            # 1. Tenta pela chave do dicionário
            if cols.get('titulo') and cols.get('titulo') in df_zabbix.columns:
                col_alerta = cols.get('titulo')
            else:
                # 2. Busca por nomes de colunas comuns
                candidatos = ['titulo', 'title', 'assunto', 'alerta', 'resumo', 'summary', 'nome', 'descricao', 'description']
                for c in df_zabbix.columns:
                    if any(cand in str(c).lower() for cand in candidatos):
                        col_alerta = c
                        break
            
            # Se ainda não achou, pega a primeira coluna de texto (object/string) que não seja id/tecnico
            if not col_alerta:
                col_alerta = df_zabbix.select_dtypes(include=['object']).columns[0]

            if col_alerta and col_alerta in df_zabbix.columns:
                # Agrupa e pega os Top 5
                top_zabbix = df_zabbix[col_alerta].dropna().astype(str).value_counts().head(5).reset_index()
                top_zabbix.columns = ['Alerta Zabbix (Sanitizado)', 'Ocorrências']
                mostrar_dataframe(top_zabbix)
            else:
                st.info("Coluna de título/alerta não identificada no Zabbix.")
        else:
            st.info("Sem dados de alertas Zabbix para o período.")

    with col_right2:
        st.markdown("### 🏆 Ranking de Atendimento da Equipe")
        if col_tec and col_tec in df_humana.columns:
            top_tec = df_humana[col_tec].value_counts().head(5).reset_index()
            top_tec.columns = ['Técnico', 'Chamados Atendidos']
            top_tec['% de Carga'] = ((top_tec['Chamados Atendidos'] / tot_equipe) * 100).round(1).astype(str) + '%'
            mostrar_dataframe(top_tec)