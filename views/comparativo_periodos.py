from datetime import time
import pandas as pd
import streamlit as st
import os
import altair as alt

def exibir(*args, **kwargs):
    caminho_excel = "relatorio glpi.xlsx"
    if os.path.exists(caminho_excel):
        try:
            df_base_comp = pd.read_excel(caminho_excel, sheet_name="Chamados")
        except Exception:
            df_base_comp = kwargs.get("df") or (args[0] if args else None)
    else:
        df_base_comp = kwargs.get("df") or (args[0] if args else None)
    
    if df_base_comp is None or df_base_comp.empty:
        st.warning("⚠️ Nenhuma base de dados disponível para o comparativo.")
        return

    df_base_comp = df_base_comp.copy()

    # --- BLINDAGEM MÁXIMA ANTI-ZABBIX ---
    for col in df_base_comp.columns:
        if any(k in str(col).lower() for k in ['requisitante', 'solicitante', 'autor', 'requester', 'user', 'usuario', 'nome']):
            df_base_comp = df_base_comp[~df_base_comp[col].astype(str).str.contains("zabbix", case=False, na=False)]
    
    for col in df_base_comp.select_dtypes(include=['object']).columns:
        df_base_comp = df_base_comp[~df_base_comp[col].astype(str).str.contains("zabbix", case=False, na=False)]

    col_data = next((c for c in df_base_comp.columns if any(k in str(c).lower() for k in ['data', 'date', 'abertura', 'created'])), None)
    if not col_data:
        st.error("Coluna de data não encontrada na base de dados.")
        return

    df_base_comp['dt_abertura'] = pd.to_datetime(df_base_comp[col_data], errors='coerce')
    df_base_comp = df_base_comp.dropna(subset=['dt_abertura'])

    dt_validas_comp = df_base_comp['dt_abertura'].dropna()
    
    if not dt_validas_comp.empty:
        min_date = dt_validas_comp.dt.date.min()
        max_date = dt_validas_comp.dt.date.max()
    else:
        st.error("Nenhuma data válida encontrada na base.")
        return

    st.markdown("#### 📅 Seleção dos Períodos para Comparação")

    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.info("📌 **Período A (Base / Anterior)**")
        data_ini_a = st.date_input("Início Período A:", value=min_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_a_ini")
        data_fim_a = st.date_input("Fim Período A:", value=min_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_a_fim")

    with c_p2:
        st.success("📌 **Período B (Recente / Mais Atual)**")
        data_ini_b = st.date_input("Início Período B:", value=min_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_b_ini")
        data_fim_b = st.date_input("Fim Período B:", value=max_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY", key="comp_p_b_fim")

    if not data_ini_a or not data_fim_a or not data_ini_b or not data_fim_b:
        st.info("ℹ️ Preencha todas as datas de início e fim para ambos os períodos para gerar o comparativo.")
        return

    start_a = pd.Timestamp.combine(data_ini_a, time(0, 0, 0))
    end_a = pd.Timestamp.combine(data_fim_a, time(23, 59, 59))
    start_b = pd.Timestamp.combine(data_ini_b, time(0, 0, 0))
    end_b = pd.Timestamp.combine(data_fim_b, time(23, 59, 59))

    df_per_a = df_base_comp[(df_base_comp['dt_abertura'] >= start_a) & (df_base_comp['dt_abertura'] <= end_a)].copy()
    df_per_b = df_base_comp[(df_base_comp['dt_abertura'] >= start_b) & (df_base_comp['dt_abertura'] <= end_b)].copy()

    # Criação garantida do objeto de período para uso geral
    df_per_a['periodo_obj'] = df_per_a['dt_abertura'].dt.to_period('M')
    df_per_b['periodo_obj'] = df_per_b['dt_abertura'].dt.to_period('M')

    # --- 1. VISÃO GERAL CONSOLIDADA ---
    st.markdown("### 📊 Visão Geral Consolidada da Comparação")
    
    dias_a = (end_a - start_a).days + 1
    dias_b = (end_b - start_b).days + 1
    
    total_a = len(df_per_a)
    total_b = len(df_per_b)
    
    media_a = total_a / dias_a if dias_a > 0 else 0
    media_b = total_b / dias_b if dias_b > 0 else 0
    
    diff_vol = total_b - total_a
    pct_vol = (diff_vol / total_a * 100) if total_a > 0 else 0
    
    diff_media = media_b - media_a

    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.metric(f"Volumetria Período A ({data_ini_a.strftime('%d/%m/%Y')} a {data_fim_a.strftime('%d/%m/%Y')})", f"{total_a:,}".replace(",", "."), delta=f"{dias_a} dias")
    with col_v2:
        st.metric(f"Volumetria Período B ({data_ini_b.strftime('%d/%m/%Y')} a {data_fim_b.strftime('%d/%m/%Y')})", f"{total_b:,}".replace(",", "."), delta=f"{pct_vol:+.1f}% vs Período A")
    with col_v3:
        st.metric("Média Diária (A vs B)", f"{media_a:.1f} / {media_b:.1f}", delta=f"{diff_media:+.1f} chamados/dia")

    st.markdown("---")

    # --- 2. COMPARATIVO DE VOLUMETRIA TOTAL MÊS A MÊS (LADO A LADO) ---
    st.markdown("### 📈 Comparativo de Volumetria Total Mês a Mês")
    
    df_per_a['mes_num'] = df_per_a['dt_abertura'].dt.month
    df_per_b['mes_num'] = df_per_b['dt_abertura'].dt.month
    
    df_per_a['ano'] = df_per_a['dt_abertura'].dt.year
    df_per_b['ano'] = df_per_b['dt_abertura'].dt.year
    
    vol_a = df_per_a.groupby(['mes_num', 'ano']).size().reset_index(name='Volumetria')
    vol_a['Período'] = 'Período A (' + vol_a['ano'].astype(str) + ')'
    
    vol_b = df_per_b.groupby(['mes_num', 'ano']).size().reset_index(name='Volumetria')
    vol_b['Período'] = 'Período B (' + vol_b['ano'].astype(str) + ')'
    
    df_mes_comp = pd.concat([vol_a, vol_b])
    
    meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    df_mes_comp['Mês'] = df_mes_comp['mes_num'].map(meses_dict)
    
    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    chart = alt.Chart(df_mes_comp).mark_bar().encode(
        x=alt.X('Mês:N', sort=ordem_meses, title='Mês', axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset('Período:N'),
        y=alt.Y('Volumetria:Q', title='Volumetria'),
        color=alt.Color(
            'Período:N', 
            scale=alt.Scale(range=['#1f77b4', '#aec7e8', '#ff7f0e', '#2ca02c']),
            legend=alt.Legend(orient='bottom', title='Período')
        )
    ).properties(
        height=400
    )
    
    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # --- 3. HISTÓRICO POR TOP 10 CATEGORIAS (MESES LADO A LADO) ---
    col_cat = next((c for c in df_base_comp.columns if any(k in str(c).lower() for k in ['categoria', 'category'])), None)

    if col_cat:
        st.markdown("### 📋 Histórico por Top 10 Categorias")
        
        # --- APLICAÇÃO SEGURA DA LÓGICA DE ENCURTAMENTO DE CATEGORIA ---
        for df_target in [df_per_a, df_per_b]:
            if col_cat in df_target.columns:
                df_target[col_cat] = df_target[col_cat].fillna("").astype(str).apply(
                    lambda x: x.split(' > ')[-1].strip() if ' > ' in x else x
                )

        top_10_cats = df_per_b[col_cat].value_counts().head(10).index.tolist()
        
        df_a_top = df_per_a[df_per_a[col_cat].isin(top_10_cats)]
        df_b_top = df_per_b[df_per_b[col_cat].isin(top_10_cats)]
        
        nomes_meses = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        
        df_tabela = pd.DataFrame({'Categoria': top_10_cats})
        df_tabela['ordem'] = df_tabela['Categoria'].map(lambda c: df_b_top[df_b_top[col_cat] == c].shape[0])
        df_tabela = df_tabela.sort_values('ordem', ascending=False).drop(columns=['ordem'])
        
        meses_a_set = set(df_per_a['periodo_obj'].unique())
        meses_b_set = set(df_per_b['periodo_obj'].unique())
        
        meses_numericos = sorted(list(set([m.month for m in meses_a_set] + [m.month for m in meses_b_set])))
        anos_envolvidos = sorted(list(set([m.year for m in meses_a_set] + [m.year for m in meses_b_set])))
        
        colunas_meses_geradas = []
        
        for m in meses_numericos:
            for ano in anos_envolvidos:
                p_mes = pd.Period(f"{ano}-{m:02d}", freq='M')
                
                if p_mes in meses_a_set or p_mes in meses_b_set:
                    nome_col = f"{nomes_meses.get(m, '')}/{str(ano)[2:]}"
                    
                    soma_mes = []
                    for cat in df_tabela['Categoria']:
                        val_a = df_a_top[(df_a_top[col_cat] == cat) & (df_a_top['periodo_obj'] == p_mes)].shape[0]
                        val_b = df_b_top[(df_b_top[col_cat] == cat) & (df_b_top['periodo_obj'] == p_mes)].shape[0]
                        soma_mes.append(val_a + val_b)
                    
                    df_tabela[nome_col] = soma_mes
                    colunas_meses_geradas.append(nome_col)

        totais_a = df_a_top[col_cat].value_counts()
        totais_b = df_b_top[col_cat].value_counts()
        
        df_tabela['Período A'] = df_tabela['Categoria'].map(lambda c: totais_a.get(c, 0))
        df_tabela['Período B'] = df_tabela['Categoria'].map(lambda c: totais_b.get(c, 0))
        
        df_tabela['↑ Y/Y %'] = df_tabela.apply(
            lambda r: f"{((r['Período B'] - r['Período A']) / r['Período A'] * 100):+.2f}%" if r['Período A'] > 0 else "+100%", axis=1
        )
        
        total_geral_b = len(df_per_b) if len(df_per_b) > 0 else 1
        df_tabela['% Backlog'] = (df_tabela['Período B'] / total_geral_b * 100).apply(lambda x: f"{x:.2f}%")

        colunas_finais = ['Categoria'] + colunas_meses_geradas + ['Período A', 'Período B', '↑ Y/Y %', '% Backlog']
        df_tabela = df_tabela[[c for c in colunas_finais if c in df_tabela.columns]]

        st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    else:
        st.info("Coluna de categoria não identificada na base de dados.")