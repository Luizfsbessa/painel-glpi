import streamlit as st
import pandas as pd

def formatar_categoria_resumida(serie):
    if serie is None or serie.empty:
        return serie
    return serie.astype(str).apply(lambda x: x.split('>')[-1].strip() if '>' in str(x) and x != 'None' else x)

def buscar_coluna(df, nomes_possiveis):
    if df is None or df.empty:
        return None
    for nome in nomes_possiveis:
        if nome in df.columns:
            return nome
    return None

@st.cache_data(ttl=300)
def carregar_e_tratar_dados(file_source):
    """Carrega arquivos CSV/XLSX do GLPI e faz a padronização e higienização dos dados."""
    dict_dfs = {"Chamados": pd.DataFrame(), "Problemas": pd.DataFrame(), "Mudanças": pd.DataFrame(), "Técnicos": pd.DataFrame()}
    try:
        is_path = isinstance(file_source, str)
        file_name = file_source if is_path else file_source.name

        if file_name.endswith('.csv'):
            try:
                df = pd.read_csv(file_source, sep=';', encoding='utf-8')
            except Exception:
                df = pd.read_csv(file_source, sep=',', encoding='utf-8')
            dict_dfs["Chamados"] = df
        else:
            xls = pd.ExcelFile(file_source, engine='openpyxl')
            for sheet in xls.sheet_names:
                dict_dfs[sheet] = pd.read_excel(xls, sheet_name=sheet)
        
        df_tecnicos = dict_dfs.get("Técnicos", pd.DataFrame())
        for key in ["Chamados", "Problemas", "Mudanças"]:
            df_curr = dict_dfs[key]
            if not df_curr.empty and not df_tecnicos.empty:
                if 'Atribuído - Técnico' in df_curr.columns and 'Atribuído - Técnico' in df_tecnicos.columns:
                    df_tec_clean = df_tecnicos[['Atribuído - Técnico', 'Atribuído - Grupo técnico']].drop_duplicates().rename(columns={'Atribuído - Grupo técnico': 'Grupo_Cadastrado'})
                    df_merged = pd.merge(df_curr, df_tec_clean, on='Atribuído - Técnico', how='left')
                    if 'Atribuído - Grupo técnico' in df_merged.columns:
                        df_merged['Atribuído - Grupo técnico'] = df_merged['Atribuído - Grupo técnico'].fillna(df_merged['Grupo_Cadastrado'])
                    else:
                        df_merged['Atribuído - Grupo técnico'] = df_merged['Grupo_Cadastrado']
                    df_merged.drop(columns=['Grupo_Cadastrado'], inplace=True, errors='ignore')
                    dict_dfs[key] = df_merged

        df_raw = dict_dfs.get("Chamados", pd.DataFrame())
        if not df_raw.empty:
            df_raw.columns = df_raw.columns.str.strip()

            for df_tmp in [df_raw, dict_dfs.get("Problemas", pd.DataFrame()), dict_dfs.get("Mudanças", pd.DataFrame())]:
                if df_tmp is not None and not df_tmp.empty:
                    c_cat = buscar_coluna(df_tmp, ['Categoria', 'categoria'])
                    if c_cat:
                        df_tmp[c_cat] = formatar_categoria_resumida(df_tmp[c_cat])

                    for col_entidade in df_tmp.columns:
                        if any(termo in col_entidade.lower() for termo in ['entidade', 'localização', 'localizacao']):
                            df_tmp[col_entidade] = df_tmp[col_entidade].astype(str).str.replace(r'^\s*Entidade raiz\s*>\s*', '', regex=True).str.strip()

            col_ab = buscar_coluna(df_raw, ['Data de abertura', 'Data Abertura', 'data', 'date'])
            col_sol = buscar_coluna(df_raw, ['Data da solução', 'Data Solução', 'solvedate'])
            col_sla = buscar_coluna(df_raw, ['Tempo para resolver excedido', 'excedido'])

            df_raw['dt_abertura'] = pd.to_datetime(df_raw[col_ab], dayfirst=True, errors='coerce') if col_ab else pd.NaT
            df_raw['dt_solucao'] = pd.to_datetime(df_raw[col_sol], dayfirst=True, errors='coerce') if col_sol else pd.NaT
            df_raw['sla_estourado'] = (df_raw[col_sla].astype(str).str.strip().str.lower() == 'sim') if col_sla else False

            zabbix_cols = [c for c in df_raw.columns if 'requerente' in c.lower()] or df_raw.select_dtypes(include='object').columns.tolist()
            mask_zabbix = pd.Series(False, index=df_raw.index)
            for c in zabbix_cols:
                mask_zabbix |= df_raw[c].astype(str).str.contains('zabbix', case=False, na=False)
            df_raw['is_zabbix'] = mask_zabbix
            dict_dfs["Chamados"] = df_raw

        return dict_dfs
    except Exception as e:
        st.error(f"Erro na leitura do arquivo: {e}")
        return dict_dfs