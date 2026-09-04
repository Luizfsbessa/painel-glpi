import streamlit as st
import pandas as pd
import os
import altair as alt

def renderizar(df_base, cols, start_dt, end_dt):
    if df_base is None or df_base.empty:
        st.warning("⚠️ Nenhuma base de dados disponível.")
        return

    df = df_base.copy()

    # --- BLINDAGEM MÁXIMA ANTI-ZABBIX ---
    for col in df.columns:
        if any(k in str(col).lower() for k in ['requisitante', 'solicitante', 'autor', 'requester', 'user', 'usuario', 'nome']):
            df = df[~df[col].astype(str).str.contains("zabbix", case=False, na=False)]
    
    for col in df.select_dtypes(include=['object']).columns:
        df = df[~df[col].astype(str).str.contains("zabbix", case=False, na=False)]

    col_data = cols.get('data') if cols else None
    if not col_data:
        col_data = next((c for c in df.columns if any(k in str(c).lower() for k in ['data', 'date', 'abertura', 'created'])), None)

    if col_data:
        df['dt_abertura'] = pd.to_datetime(df[col_data], errors='coerce')
        df = df.dropna(subset=['dt_abertura'])

    st.markdown("### 👤 Performance da Área & Desempenho por Técnico")

    # Filtro de período condicionado à barra lateral
    if col_data and start_dt and end_dt:
        start_ts = pd.Timestamp.combine(start_dt, pd.Timestamp("00:00:00").time())
        end_ts = pd.Timestamp.combine(end_dt, pd.Timestamp("23:59:59").time())
        df_filtrado = df[(df['dt_abertura'] >= start_ts) & (df['dt_abertura'] <= end_ts)].copy()
    else:
        df_filtrado = df.copy()

    tab_geral, tab_individual = st.tabs(["🌐 Visão Geral da Área", "👤 Visão Individual por Técnico"])

    col_sla = "Tempo para resolver excedido"
    col_tecnico = "Atribuído - Técnico"
    col_tipo = next((c for c in df.columns if 'tipo' in str(c).lower()), None)

    with tab_geral:
        total_chamados = len(df_filtrado)
        
        if col_tipo:
            df_incidentes = df_filtrado[df_filtrado[col_tipo].astype(str).str.contains("incidente", case=False, na=False)]
            df_requisicoes = df_filtrado[df_filtrado[col_tipo].astype(str).str.contains("requisi", case=False, na=False)]
            num_incidentes = len(df_incidentes)
            num_requisicoes = len(df_requisicoes)
            str_inc_req = f"{num_incidentes:,} / {num_requisicoes:,}".replace(",", ".")
        else:
            df_incidentes = pd.DataFrame()
            num_incidentes = 0
            str_inc_req = "N/A"

        if col_sla in df_filtrado.columns:
            if not df_incidentes.empty and col_sla in df_incidentes.columns:
                sla_estourado_incidentes = df_incidentes[df_incidentes[col_sla].astype(str).str.strip().str.lower().isin(['sim', 'yes', '1', 'true', 'estourado'])]
                total_estourados = len(sla_estourado_incidentes)
            else:
                sla_estourado = df_filtrado[df_filtrado[col_sla].astype(str).str.strip().str.lower().isin(['sim', 'yes', '1', 'true', 'estourado'])]
                total_estourados = len(sla_estourado)

            base_calculo_sla = num_incidentes if num_incidentes > 0 else total_chamados
            pct_sla = ((base_calculo_sla - total_estourados) / base_calculo_sla * 100) if base_calculo_sla > 0 else 100
            str_sla_geral = f"{pct_sla:.1f}% (Estourados: {total_estourados})"
        else:
            str_sla_geral = "N/A"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total de Chamados", f"{total_chamados:,}".replace(",", "."))
        with c2:
            st.metric("Incidentes vs Requisições", str_inc_req)
        with c3:
            st.metric("SLA Geral", str_sla_geral)

        st.markdown("---")

        if col_tecnico in df_filtrado.columns:
            df_tec_geral = df_filtrado.dropna(subset=[col_tecnico]).copy()
            df_tec_geral = df_tec_geral[df_tec_geral[col_tecnico].astype(str).str.strip() != ""]
            
            if not df_tec_geral.empty:
                ranking_tec = df_tec_geral[col_tecnico].value_counts().reset_index()
                ranking_tec.columns = ['Técnico', 'Total de Chamados']
                
                total_geral_equipe = ranking_tec['Total de Chamados'].sum()
                ranking_tec['% da Equipe'] = ranking_tec['Total de Chamados'].apply(
                    lambda x: f"{(x / total_geral_equipe * 100):.1f}%" if total_geral_equipe > 0 else "0.0%"
                )
                
                st.markdown("#### 🏆 Ranking de Volume por Técnico")
                st.dataframe(ranking_tec, use_container_width=True, hide_index=True)
        else:
            st.info(f"Coluna '{col_tecnico}' não encontrada para gerar o ranking.")

    with tab_individual:
        if col_tecnico in df_filtrado.columns:
            df_tec = df_filtrado.dropna(subset=[col_tecnico]).copy()
            df_tec = df_tec[df_tec[col_tecnico].astype(str).str.strip() != ""]

            if not df_tec.empty:
                lista_tecnicos = sorted(df_tec[col_tecnico].unique().tolist())
                
                st.markdown("Selecione o Técnico:")
                tec_selecionado = st.selectbox("", [""] + lista_tecnicos, label_visibility="collapsed")
                
                if tec_selecionado and tec_selecionado != "":
                    df_detalhe_tec = df_tec[df_tec[col_tecnico] == tec_selecionado]
                    total_atrib = len(df_detalhe_tec)
                    
                    col_status = next((c for c in df.columns if any(k in str(c).lower() for k in ['status', 'estado'])), None)
                    if col_status:
                        concluidos = len(df_detalhe_tec[df_detalhe_tec[col_status].astype(str).str.contains("solucionado|fechado|concluído", case=False, na=False)])
                    else:
                        concluidos = total_atrib
                    
                    participacao = (total_atrib / total_chamados * 100) if total_chamados > 0 else 0

                    # Cálculo do SLA Individual do Técnico de forma mais compacta para caber na tela
                    if col_tipo and col_sla in df_detalhe_tec.columns:
                        df_tec_incidentes = df_detalhe_tec[df_detalhe_tec[col_tipo].astype(str).str.contains("incidente", case=False, na=False)]
                        total_tec_incidentes = len(df_tec_incidentes)
                        if total_tec_incidentes > 0:
                            estourados_tec = len(df_tec_incidentes[df_tec_incidentes[col_sla].astype(str).str.strip().str.lower().isin(['sim', 'yes', '1', 'true', 'estourado'])])
                            base_sla_tec = total_tec_incidentes
                        else:
                            estourados_tec = len(df_detalhe_tec[df_detalhe_tec[col_sla].astype(str).str.strip().str.lower().isin(['sim', 'yes', '1', 'true', 'estourado'])])
                            base_sla_tec = total_atrib
                    elif col_sla in df_detalhe_tec.columns:
                        estourados_tec = len(df_detalhe_tec[df_detalhe_tec[col_sla].astype(str).str.strip().str.lower().isin(['sim', 'yes', '1', 'true', 'estourado'])])
                        base_sla_tec = total_atrib
                    else:
                        estourados_tec = 0
                        base_sla_tec = total_atrib

                    pct_sla_tec = ((base_sla_tec - estourados_tec) / base_sla_tec * 100) if base_sla_tec > 0 else 100
                    
                    # Formato mais enxuto para evitar cortes visuais no componente metric
                    str_sla_tec = f"{pct_sla_tec:.1f}% ({estourados_tec} est.)"

                    st.markdown(f"### Desempenho de: {tec_selecionado}")
                    
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Atribuídos", f"{total_atrib:,}".replace(",", "."))
                    with m2:
                        st.metric("Concluídos", f"{concluidos:,}".replace(",", "."))
                    with m3:
                        st.metric("Participação", f"{participacao:.1f}%")
                    with m4:
                        st.metric("SLA Individual", str_sla_tec)

                    st.markdown("---")
                    st.markdown("#### Detalhamento dos Chamados do Técnico")
                    
                    def achar_coluna(dataframe, cols_possiveis):
                        for p in cols_possiveis:
                            encontrada = next((c for c in dataframe.columns if p.lower() in str(c).lower()), None)
                            if encontrada:
                                return encontrada
                        return None

                    c_id = achar_coluna(df_detalhe_tec, ['id', 'chamado', 'ticket'])
                    c_tit = achar_coluna(df_detalhe_tec, ['titulo', 'summary', 'assunto'])
                    c_ent = achar_coluna(df_detalhe_tec, ['entidade', 'entity'])
                    c_cat = achar_coluna(df_detalhe_tec, ['categoria', 'category'])
                    c_tip = achar_coluna(df_detalhe_tec, ['tipo', 'type'])
                    c_pri = achar_coluna(df_detalhe_tec, ['prioridade', 'priority'])
                    c_req = achar_coluna(df_detalhe_tec, ['requerente', 'solicitante', 'autor'])
                    c_dat_ab = achar_coluna(df_detalhe_tec, ['data de abertura', 'abertura', 'created'])
                    c_dat_sol = achar_coluna(df_detalhe_tec, ['data da solução', 'solução', 'closed', 'solved'])
                    c_sta = achar_coluna(df_detalhe_tec, ['status', 'estado'])
                    c_sla = achar_coluna(df_detalhe_tec, ['sla_estourado', 'tempo para resolver excedido', 'excedido'])

                    colunas_desejadas = {
                        c_id: 'id',
                        c_tit: 'titulo',
                        c_ent: 'entidade',
                        c_cat: 'categoria',
                        c_tip: 'tipo',
                        c_pri: 'prioridade',
                        c_req: 'requerente',
                        c_dat_ab: 'data de abertura',
                        c_dat_sol: 'data da solução',
                        c_sta: 'status',
                        c_sla: 'sla_estourado'
                    }

                    colunas_presentes = [k for k in colunas_desejadas.keys() if k is not None]
                    df_exibicao = df_detalhe_tec[colunas_presentes].copy()
                    df_exibicao = df_exibicao.rename(columns=colunas_desejadas)

                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
                else:
                    st.info("👆 Selecione um técnico acima para visualizar os indicadores e o detalhamento dos chamados.")
            else:
                st.warning("⚠️ Nenhum registro com técnico atribuído encontrado no período.")
        else:
            st.error(f"⚠️ A coluna '{col_tecnico}' não foi encontrada na base de dados.")