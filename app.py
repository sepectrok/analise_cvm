"""
Solis Investimentos — Benchmarking Institucional
Main Entry Point
"""

import streamlit as st

st.set_page_config(
    page_title="Solis · Benchmarking Institucional",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Principal": [
        st.Page("Visao_Geral.py", title="Visão Geral", icon="🏠"),
        st.Page("pages/00_Guia_de_Uso.py", title="Guia de Uso", icon="📖"),
    ],
    "Análises de Mercado": [
        st.Page("pages/01_Analise_Taxas.py", title="Análise de Taxas", icon="📈"),
        st.Page("pages/03_Administradores.py", title="Administradores", icon="🏢"),
        st.Page("pages/04_Gestores.py", title="Gestores", icon="👔"),
        st.Page("pages/05_Foco_Atuacao.py", title="Foco de Atuação", icon="🎯"),
        st.Page("pages/08_Tabela_Analitica.py", title="Tabela Analítica", icon="📋"),
    ]
}

pg = st.navigation(pages)
pg.run()
