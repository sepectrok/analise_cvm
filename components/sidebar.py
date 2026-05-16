"""Sidebar — FIDC Analytics Platform"""

import streamlit as st
import pandas as pd
import os


def load_css():
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles", "main.css")
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_sidebar(df: pd.DataFrame) -> dict:
    """Render the sidebar with filters. Returns a dict of active filter values."""
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
            <div class="logo-title">⬡ FIDC Analytics</div>
            <div class="logo-sub">Benchmarking Institucional de Taxas</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">Filtros de Análise</div>', unsafe_allow_html=True)

        # Foco de Atuação
        focos_disponiveis = sorted(df["foco_atuacao"].dropna().unique().tolist())
        focos = st.multiselect(
            "Foco de Atuação",
            options=focos_disponiveis,
            default=[],
            placeholder="Todos os segmentos",
            help="Filtre por segmento de atuação do FIDC",
        )

        # Administrador
        adm_disponiveis = sorted(df["administrador"].dropna().unique().tolist())
        administradores = st.multiselect(
            "Administrador",
            options=adm_disponiveis,
            default=[],
            placeholder="Todos os administradores",
        )

        # Gestor
        ges_disponiveis = sorted(df["gestor"].dropna().unique().tolist())
        gestores = st.multiselect(
            "Gestor",
            options=ges_disponiveis,
            default=[],
            placeholder="Todos os gestores",
        )

        # Taxa de Adm range removed

        # Dataset info
        st.markdown("---")
        st.markdown(f"""
        <div style="font-size:0.72rem; color:var(--text-muted); line-height:1.8;">
            📂 <b style="color:var(--text-secondary);">{len(df)}</b> FIDCs carregados<br>
            🏢 <b style="color:var(--text-secondary);">{df['administrador'].nunique()}</b> administradores<br>
            👔 <b style="color:var(--text-secondary);">{df['gestor'].nunique()}</b> gestores<br>
            🎯 <b style="color:var(--text-secondary);">{df['foco_atuacao'].nunique()}</b> segmentos
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.67rem; color:var(--text-muted); text-align:center;">
            Fonte: Regulamentos CVM / FNET<br>
            Extração via LLM (GPT-4o-mini)
        </div>
        """, unsafe_allow_html=True)

    return {
        "focos": focos,
        "administradores": administradores,
        "gestores": gestores,
    }


def apply_sidebar_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply the sidebar filter selections to df."""
    f = df.copy()
    if filters.get("focos"):
        f = f[f["foco_atuacao"].isin(filters["focos"])]
    if filters.get("administradores"):
        f = f[f["administrador"].isin(filters["administradores"])]
    if filters.get("gestores"):
        f = f[f["gestor"].isin(filters["gestores"])]
    return f
