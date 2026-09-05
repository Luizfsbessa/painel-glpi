import streamlit as st

def aplicar_estilos_customizados():
    """Injeta estilos CSS customizados para alinhar componentes e formatar tabelas."""
    st.markdown("""
        <style>
            /* Restaura o cabeçalho no topo e remove a linha divisória inferior dele */
            section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
                border-bottom: none !important;
                padding-bottom: 0px !important;
                min-height: 40px !important;
            }
            
            /* Remove o padding superior excessivo da sidebar para colar no topo */
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
                padding-top: 0rem !important;
            }
            
            /* Remove todas as linhas divisórias (hr) geradas na sidebar */
            section[data-testid="stSidebar"] hr {
                display: none !important;
            }
            
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stDateInput"]),
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stSelectbox"]) {
                min-height: 85px !important;
                align-items: flex-end !important;
            }
            div[data-testid="stDateInput"], div[data-testid="stSelectbox"] {
                min-height: 75px !important;
            }
            div[data-testid="stDataFrame"] th {
                text-align: center !important;
                font-weight: 800 !important;
                white-space: normal !important;
                word-wrap: break-word !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stPopover"] {
                z-index: 999999 !important;
            }
        </style>
    """, unsafe_allow_html=True)

def mostrar_dataframe(df, use_container_width=True, hide_index=True, height=None, column_config=None):
    """Padroniza a exibição de DataFrames no Streamlit com alinhamento centralizado."""
    if df is None or df.empty:
        st.dataframe(df, use_container_width=use_container_width, hide_index=hide_index)
        return
    cfg = {col: st.column_config.Column(alignment="center") for col in df.columns}
    if column_config:
        cfg.update(column_config)
    kwargs = {"use_container_width": use_container_width, "hide_index": hide_index, "column_config": cfg}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)