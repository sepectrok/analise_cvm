"""Página 8 — Tabela Analítica"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st


from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.tables import render_analytical_table, export_buttons
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS, CVNP_COLS, CVNP_LABELS

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("📋", "Tabela Analítica",
            "Base completa de FIDCs com filtros, busca e exportação")

# ── Quick stats ────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("FIDCs na visão", len(df))
c2.metric("Administradores", df["administrador"].nunique())
c3.metric("Segmentos", df["foco_atuacao"].nunique())

st.markdown("---")

# ── Additional column filters ──────────────────────────────────────────────────
with st.expander("🔧 Filtros Adicionais", expanded=False):
    fc1, fc2 = st.columns(2)
    with fc1:
        focos_extra = st.multiselect(
            "Foco de Atuação (inline)",
            options=sorted(df["foco_atuacao"].dropna().unique()),
            key="tbl_foco"
        )
    with fc2:
        apenas_com_adm = st.checkbox("Apenas com Administrador identificado", value=False)
        apenas_com_ges = st.checkbox("Apenas com Gestor identificado", value=False)

df_view = df.copy()
if focos_extra:
    df_view = df_view[df_view["foco_atuacao"].isin(focos_extra)]
if apenas_com_adm:
    df_view = df_view[df_view["administrador"].notna()]
if apenas_com_ges:
    df_view = df_view[df_view["gestor"].notna()]

# ── Main table ────────────────────────────────────────────────────────────────
render_analytical_table(df_view, key="main_tbl")

st.markdown("---")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Exportar Dados</div>', unsafe_allow_html=True)

# Build export-ready dataframe
export_cols = (
    ["cnpj_tratado", "nome_fundo", "foco_atuacao", "administrador", "gestor",
     "data_regulamento", "Valor_PL", "Valor_PL_Medio"] + TAXA_COLS +
    ["taxa_inadimplencia", "PDD", "DC", "Sub_JR", "Sub_JR_MZ", "CVNP"] + CVNP_COLS
)
export_cols = [c for c in export_cols if c in df_view.columns]
df_export = df_view[export_cols].copy()
df_export.rename(columns={
    "cnpj_tratado":      "CNPJ",
    "nome_fundo":        "Nome do Fundo",
    "foco_atuacao":      "Foco de Atuação",
    "administrador":     "Administrador",
    "gestor":            "Gestor",
    "data_regulamento":  "Data do Regulamento",
    "Valor_PL":          "PL Atual",
    "Valor_PL_Medio":    "PL Médio",
    "taxa_inadimplencia": "Inadimplência PDD/DC (%)",
    "PDD":               "PDD (R$)",
    "DC":                "DC (R$)",
    "Sub_JR":            "Subordinação Júnior (%)",
    "Sub_JR_MZ":         "Subordinação Júnior+Mezzanino (%)",
    "CVNP":              "Credito Vencido Nao Pago - CVNP (R$)",
    **{c: TAXA_LABELS.get(c, c) + " (% a.a.)" for c in TAXA_COLS},
    **{c: CVNP_LABELS.get(c, c) + " (R$)" for c in CVNP_COLS},
}, inplace=True)

export_buttons(df_export, label="fidc_analytics")
