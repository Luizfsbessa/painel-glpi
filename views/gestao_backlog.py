import streamlit as st
import pandas as pd
from datetime import datetime
from utils.ui_helpers import mostrar_dataframe

def renderizar(df_periodo_sem_zabbix, cols, start_dt=None, end_dt=None, df_completo=None):
    df_full = df_completo if df_completo is not None else df_periodo_sem_zabbix
    df_humana = df_periodo_sem_zabbix.copy()

    dt_inicio_str = start_dt.strftime('%d/%m/%Y') if start_dt else "Início"
    dt_fim_str = end_dt.strftime('%d/%m/%Y') if end_dt else "Fim"

    st.subheader(f"⏳ Gestão de Backlog & Chamados Pendentes ({dt_inicio_str} a {dt_fim_str})")

    # Mapeamento dinâmico de colunas
    col_status = cols.get('status') or next((c for c in df_full.columns if 'status' in str(c).lower() or 'estado' in str(c).lower()), None)
    col_tec = cols.get('tecnico') or next((c for c in df_full.columns if 'tecn' in str(c).lower() or 'atribu' in str(c).lower()), None)
    col_req = cols.get('requerente') or next((c for c in df_full.columns if 'req' in str(c).lower() or 'usuario' in str(c).lower()), None)
    col_abertura = next((c for c in df_full.columns if any(p in str(c).lower() for p in ['abertura', 'criacao', 'created', 'dt_abertura'])), None)

    status_fechados = ['Solucionado', 'Fechado', 'Closed', 'Resolved']

    # --- 1. FILTRAGEM DE BACKLOG ---
    if col_status and col_status in df_full.columns:
        df_backlog_total = df_full[~df_full[col_status].astype(str).isin(status_fechados)].copy()
    else:
        df_backlog_total = df_full.copy()

    df_backlog_humano = df_periodo_sem_zabbix[~df_periodo_sem_zabbix[col_status].astype(str).isin(status_fechados)].copy() if (col_status and col_status in df_periodo_sem_zabbix.columns) else df_periodo_sem_zabbix.copy()
    
    # Identifica Zabbix no Backlog Total
    mask_zabbix = pd.Series(False, index=df_backlog_total.index)
    for col_check in [col_tec, col_req, 'Requerente', 'Técnico', 'Atribuído a']:
        if col_check and col_check in df_backlog_total.columns:
            mask_zabbix = mask_zabbix | df_backlog_total[col_check].astype(str).str.contains('Zabbix', case=False, na=False)

    df_backlog_zabbix = df_backlog_total[mask_zabbix].copy()

    # Cálculo do dias_em_aberto
    for df_temp in [df_backlog_total, df_backlog_humano, df_backlog_zabbix]:
        if not df_temp.empty:
            if 'dias_em_aberto' not in df_temp.columns:
                if col_abertura and col_abertura in df_temp.columns:
                    df_temp[col_abertura] = pd.to_datetime(df_temp[col_abertura], errors='coerce')
                    data_ref = datetime.now()
                    df_temp['dias_em_aberto'] = (data_ref - df_temp[col_abertura]).dt.days.fillna(0).astype(int)
                else:
                    df_temp['dias_em_aberto'] = 0

    df_criticos_humano = df_backlog_humano[df_backlog_humano['dias_em_aberto'] > 5] if 'dias_em_aberto' in df_backlog_humano.columns else pd.DataFrame()

    # Totais dos KPIs
    tot_backlog = len(df_backlog_total)
    tot_pend_humano = len(df_backlog_humano)
    tot_pend_zabbix = len(df_backlog_zabbix)
    tot_criticos = len(df_criticos_humano)
    pct_criticos = round((tot_criticos / tot_pend_humano) * 100, 1) if tot_pend_humano > 0 else 0.0

    # --- 2. CARDS DE KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Backlog Total", f"{tot_backlog:,}".replace(",", "."))
    c2.metric("Pendente (Atendimento Humano)", f"{tot_pend_humano:,}".replace(",", "."))
    c3.metric("Pendente (Zabbix)", f"{tot_pend_zabbix:,}".replace(",", "."))
    c4.metric("Críticos (> 5 dias em aberto)", f"{tot_criticos:,}".replace(",", "."), delta=f"↑ {pct_criticos}% do humano", delta_color="inverse")

    st.divider()

    # --- 3. TABELAS NAVEGÁVEIS EM ABAS (TABS) ---
    tab_humano, tab_zabbix = st.tabs([
        "👤 Backlog Operacional (Atendimento Humano)", 
        "🤖 Backlog Infraestrutura (Zabbix)"
    ])

    def formatar_tabela_backlog(df_src):
        if df_src.empty:
            return pd.DataFrame()
        
        df_base = df_src.loc[:, ~df_src.columns.duplicated()].copy()
        
        mapa = {}
        ja_mapeados = set()

        for c in df_base.columns:
            cl = str(c).lower()
            
            if any(k in cl for k in ['id', 'chamado', 'numero']) and 'ID' not in ja_mapeados:
                mapa[c] = 'ID'
                ja_mapeados.add('ID')
            elif any(k in cl for k in ['dt_abertura', 'data_abertura', 'criacao', 'created']) and 'dt_abertura' not in ja_mapeados:
                mapa[c] = 'dt_abertura'
                ja_mapeados.add('dt_abertura')
            elif 'dias_em_aberto' in cl and 'dias_em_aberto' not in ja_mapeados:
                mapa[c] = 'dias_em_aberto'
                ja_mapeados.add('dias_em_aberto')
            elif 'tipo' in cl and 'Tipo' not in ja_mapeados:
                mapa[c] = 'Tipo'
                ja_mapeados.add('Tipo')
            elif 'prio' in cl and 'Prioridade' not in ja_mapeados:
                mapa[c] = 'Prioridade'
                ja_mapeados.add('Prioridade')
            elif any(k in cl for k in ['titulo', 'assunto', 'alerta', 'desc']) and 'Título' not in ja_mapeados:
                mapa[c] = 'Título'
                ja_mapeados.add('Título')
            elif any(k in cl for k in ['tecn', 'atribu']) and 'Atribuído - Técnico' not in ja_mapeados:
                mapa[c] = 'Atribuído - Técnico'
                ja_mapeados.add('Atribuído - Técnico')
            elif 'status' in cl and 'Status' not in ja_mapeados:
                mapa[c] = 'Status'
                ja_mapeados.add('Status')

        df_renomeado = df_base.rename(columns=mapa)
        df_renomeado = df_renomeado.loc[:, ~df_renomeado.columns.duplicated()]
        
        cols_desejadas = ['ID', 'dt_abertura', 'dias_em_aberto', 'Tipo', 'Prioridade', 'Título', 'Atribuído - Técnico', 'Status']
        cols_finais = [c for c in cols_desejadas if c in df_renomeado.columns]
        
        df_out = df_renomeado[cols_finais].copy()
        df_out = df_out.loc[:, ~df_out.columns.duplicated()]
        
        if 'dias_em_aberto' in df_out.columns:
            df_out = df_out.sort_values(by='dias_em_aberto', ascending=False)
            
        return df_out

    def renderizar_tabela_com_link(df_fmt):
        if df_fmt.empty:
            st.info("Nenhum registro encontrado.")
            return

        df_exibicao = df_fmt.copy()
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

    # ABA 1: Backlog Humano
    with tab_humano:
        df_humano_fmt = formatar_tabela_backlog(df_backlog_humano)
        if not df_humano_fmt.empty:
            renderizar_tabela_com_link(df_humano_fmt)
        else:
            st.info("Nenhum chamado pendente no atendimento humano.")

    # ABA 2: Backlog Zabbix
    with tab_zabbix:
        df_zabbix_fmt = formatar_tabela_backlog(df_backlog_zabbix)
        if not df_zabbix_fmt.empty:
            renderizar_tabela_com_link(df_zabbix_fmt)
        else:
            st.info("Nenhum alerta pendente no Zabbix.")

# Alias de compatibilidade com o app.py
def exibir(*args, **kwargs):
    df_periodo_sem_zabbix = kwargs.get('df_periodo_sem_zabbix') or (args[0] if len(args) > 0 else None)
    cols = kwargs.get('cols') or (args[2] if len(args) > 2 else {})
    start_dt = kwargs.get('start_dt') or (args[3] if len(args) > 3 else None)
    end_dt = kwargs.get('end_dt') or (args[4] if len(args) > 4 else None)
    df_completo = kwargs.get('df_completo')
    
    renderizar(df_periodo_sem_zabbix, cols, start_dt=start_dt, end_dt=end_dt, df_completo=df_completo)