import streamlit as st
import pandas as pd
import re
from utils.ui_helpers import mostrar_dataframe

def exibir(df_periodo, cols, start_dt, end_dt):
    st.subheader("🤖 Visão Exclusiva - Alertas Zabbix")

    df_zabbix = df_periodo[df_periodo['is_zabbix']].copy()
    tot_zbx = len(df_zabbix)

    if tot_zbx == 0:
        st.success("Nenhum alerta automático do Zabbix registrado no período selecionado.")
        return

    st.metric("Total de Alertas Disparados", tot_zbx)

    st.divider()
    st.markdown("### 🔍 Detalhamento dos Alertas Sanitizados")
    if cols['tit'] and cols['tit'] in df_zabbix.columns:
        df_zabbix['Alerta Sanitizado'] = df_zabbix[cols['tit']].astype(str).apply(lambda x: re.sub(r'^Problem:\s*\[\d+\]\s*', '', x, flags=re.IGNORECASE))
        ranking_zbx = df_zabbix['Alerta Sanitizado'].value_counts().reset_index()
        ranking_zbx.columns = ['Descrição do Alerta', 'Frequência']
        ranking_zbx['% do Total Zabbix'] = ((ranking_zbx['Frequência'] / tot_zbx) * 100).round(1).astype(str) + '%'
        mostrar_dataframe(ranking_zbx)