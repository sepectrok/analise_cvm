"""Sidebar — Solis Investimentos Platform — Premium v2"""

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
            <div class="logo-title">Solis Analytics</div>
            <div class="logo-sub">Inteligência Competitiva · FIDCs</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-title">Filtros</div>', unsafe_allow_html=True)

        # Foco de Atuação
        focos_disponiveis = sorted(df["foco_atuacao"].dropna().unique().tolist())
        focos = st.multiselect(
            "Segmento",
            options=focos_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Administrador
        adm_disponiveis = sorted(df["administrador"].dropna().unique().tolist())
        administradores = st.multiselect(
            "Administrador",
            options=adm_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Gestor
        ges_disponiveis = sorted(df["gestor"].dropna().unique().tolist())
        gestores = st.multiselect(
            "Gestor",
            options=ges_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Range de Taxas
        st.markdown('<div class="sidebar-section-title" style="margin-top:16px;">Ranges de Taxa</div>', unsafe_allow_html=True)

        gestao_range = None
        if "taxa_gestao" in df.columns and not df["taxa_gestao"].dropna().empty:
            min_ges = float(df["taxa_gestao"].min())
            max_ges = float(df["taxa_gestao"].max())
            if max_ges > min_ges:
                gestao_range = st.slider("Gestão (% a.a.)", min_value=min_ges, max_value=max_ges, value=(min_ges, max_ges), step=0.01)

        perf_range = None
        if "taxa_performance" in df.columns and not df["taxa_performance"].dropna().empty:
            min_perf = float(df["taxa_performance"].min())
            max_perf = float(df["taxa_performance"].max())
            if max_perf > min_perf:
                perf_range = st.slider("Performance (% a.a.)", min_value=min_perf, max_value=max_perf, value=(min_perf, max_perf), step=0.1)

        # Dataset stats
        st.markdown("---")
        st.markdown(f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat">
                <span class="stat-value">{len(df)}</span>
                <span class="stat-label">FIDCs</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['administrador'].nunique()}</span>
                <span class="stat-label">Admins</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['gestor'].nunique()}</span>
                <span class="stat-label">Gestores</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['foco_atuacao'].nunique()}</span>
                <span class="stat-label">Segmentos</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.6rem; color:var(--text-dim); text-align:center; letter-spacing:0.5px;">
            Fonte: Regulamentos CVM / FNET
        </div>
        """, unsafe_allow_html=True)

    filters_dict = {
        "focos": focos,
        "administradores": administradores,
        "gestores": gestores,
    }

    if gestao_range is not None and "taxa_gestao" in df.columns:
        if gestao_range != (float(df["taxa_gestao"].min()), float(df["taxa_gestao"].max())):
            filters_dict["gestao_range"] = gestao_range

    if perf_range is not None and "taxa_performance" in df.columns:
        if perf_range != (float(df["taxa_performance"].min()), float(df["taxa_performance"].max())):
            filters_dict["perf_range"] = perf_range

    return filters_dict


def apply_sidebar_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply the sidebar filter selections to df."""
    f = df.copy()
    if filters.get("focos"):
        f = f[f["foco_atuacao"].isin(filters["focos"])]
    if filters.get("administradores"):
        f = f[f["administrador"].isin(filters["administradores"])]
    if filters.get("gestores"):
        f = f[f["gestor"].isin(filters["gestores"])]
    if "gestao_range" in filters:
        min_g, max_g = filters["gestao_range"]
        f = f[f["taxa_gestao"].notna() & (f["taxa_gestao"] >= min_g) & (f["taxa_gestao"] <= max_g)]
    if "perf_range" in filters:
        min_p, max_p = filters["perf_range"]
        f = f[f["taxa_performance"].notna() & (f["taxa_performance"] >= min_p) & (f["taxa_performance"] <= max_p)]
    return f
