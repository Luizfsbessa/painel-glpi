import streamlit as st
import pandas as pd
from utils.ui_helpers import mostrar_dataframe

def renderizar(*args, **kwargs):
    # 1. Recuperação flexível de parâmetros (aceita tanto por posição quanto por nome)
    df_prob_in = None
    df_mud_in = None
    df_base = None

    # Verifica se os dois primeiros argumentos são DataFrames prontos (ex: df_problemas, df_mudancas)
    if len(args) >= 2 and isinstance(args[0], pd.DataFrame) and isinstance(args[1], pd.DataFrame):
        df_prob_in = args[0]
        df_mud_in = args[1]
    
    # Recupera parâmetros por nome
    df_periodo_sem_zabbix = kwargs.get('df_periodo_sem_zabbix')
    df_completo = kwargs.get('df_completo')
    cols = kwargs.get('cols', {})
    start_dt = kwargs.get('start_dt')
    end_dt = kwargs.get('end_dt')

    dt_inicio_str = start_dt.strftime('%d/%m/%Y') if hasattr(start_dt, 'strftime') else "Início"
    dt_fim_str = end_dt.strftime('%d/%m/%Y') if hasattr(end_dt, 'strftime') else "Fim"

    st.subheader(f"🔄 Gerenciamento de Problemas & Mudanças ({dt_inicio_str} a {dt_fim_str})")

    # 2. Resolução dos DataFrames de Problemas e Mudanças
    if df_prob_in is not None and df_mud_in is not None:
        df_problemas = df_prob_in.copy()
        df_mudancas = df_mud_in.copy()
    else:
        # Tenta extrair da base disponível
        df_base = df_completo if (df_completo is not None and not df_completo.empty) else df_periodo_sem_zabbix
        if df_base is None:
            st.warning("Nenhum dado fornecido para o módulo.")
            return

        col_tipo = cols.get('tipo') or next((c for c in df_base.columns if any(k in str(c).lower() for k in ['tipo', 'type', 'categoria'])), None)
        
        if col_tipo and col_tipo in df_base.columns:
            serie_tipo = df_base[col_tipo].astype(str).str.lower()
            df_problemas = df_base[serie_tipo.str.contains('problem|problema', regex=True, na=False)].copy()
            df_mudancas = df_base[serie_tipo.str.contains('mudan|gmud|change|altera', regex=True, na=False)].copy()
        else:
            df_problemas = pd.DataFrame()
            df_mudancas = pd.DataFrame()

    col_status = cols.get('status') or next((c for c in (df_problemas.columns if not df_problemas.empty else df_mudancas.columns) if any(k in str(c).lower() for k in ['status', 'estado'])), None)
    status_concluidos = ['Solucionado', 'Fechado', 'Closed', 'Resolved', 'Concluído', 'Aplicado']

    # 3. CRIAÇÃO DAS ABAS
    tab_problemas, tab_mudancas = st.tabs([
        "⚠️ Painel de Problemas", 
        "🔀 Painel de Mudanças"
    ])

    # --- ABA 1: PROBLEMAS ---
    with tab_problemas:
        tot_prob = len(df_problemas)
        
        if not df_problemas.empty and col_status and col_status in df_problemas.columns:
            conc_prob = len(df_problemas[df_problemas[col_status].astype(str).isin(status_concluidos)])
            and_prob = tot_prob - conc_prob
        else:
            conc_prob, and_prob = 0, tot_prob

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Problemas", tot_prob)
        c2.metric("Em Andamento / Atendimento", and_prob)
        c3.metric("Concluídos / Solucionados", conc_prob)

        st.divider()

        if not df_problemas.empty:
            mostrar_dataframe(df_problemas.loc[:, ~df_problemas.columns.duplicated()])
        else:
            st.info("Nenhum problema registrado.")

    # --- ABA 2: MUDANÇAS ---
    with tab_mudancas:
        tot_mud = len(df_mudancas)
        
        if not df_mudancas.empty and col_status and col_status in df_mudancas.columns:
            conc_mud = len(df_mudancas[df_mudancas[col_status].astype(str).isin(status_concluidos)])
            and_mud = tot_mud - conc_mud
        else:
            conc_mud, and_mud = 0, tot_mud

        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Mudanças", tot_mud)
        c2.metric("Em Andamento / Atendimento", and_mud)
        c3.metric("Concluídos / Solucionados", conc_mud)

        st.divider()

        if not df_mudancas.empty:
            mostrar_dataframe(df_mudancas.loc[:, ~df_mudancas.columns.duplicated()])
        else:
            st.info("Nenhuma mudança registrada.")

def exibir(*args, **kwargs):
    renderizar(*args, **kwargs)