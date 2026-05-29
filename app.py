"""
Solis Investimentos — Benchmarking Institucional
Main Entry Point
"""

import streamlit as st

st.set_page_config(
    page_title="Solis · Benchmarking Institucional",
    page_icon="logo_solis_v.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Principal": [
        st.Page("Visao_Geral.py", title="Visão Geral"),
        st.Page("pages/00_Guia_de_Uso.py", title="Guia de Uso"),
    ],
    "Análises de Mercado": [
        st.Page("pages/01_Analise_Taxas.py", title="Análise de Taxas"),
        st.Page("pages/03_Administradores.py", title="Administradores"),
        st.Page("pages/04_Gestores.py", title="Gestores"),
        st.Page("pages/05_Foco_Atuacao.py", title="Foco de Atuação"),
        st.Page("pages/06_Evolucao.py", title="Evolução histórica"),
        st.Page("pages/08_Tabela_Analitica.py", title="Tabela Analítica"),
    ]
}

pg = st.navigation(pages)
pg.run()
