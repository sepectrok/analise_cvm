"""Página 3 — Agrupamento por Administrador"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Administradores | FIDC Analytics", page_icon="🏢", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import bar_ranking, histogram_taxa
from components.tables import render_entity_ranking
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("🏢", "Agrupamento por Administrador",
            "Ranking, taxas médias e concentração por entidade administradora")

df_adm = df.dropna(subset=["administrador"])
if df_adm.empty:
    st.warning("Nenhum dado disponível para administradores com os filtros aplicados.")
    st.stop()

# ── Aggregate ─────────────────────────────────────────────────────────────────
taxa_cols_avail = [c for c in TAXA_COLS if c in df_adm.columns]
agg_dict = {c: "mean" for c in taxa_cols_avail}
agg_dict["cnpj_tratado"] = "count"

df_agg = (
    df_adm.groupby("administrador")
    .agg(agg_dict)
    .reset_index()
    .rename(columns={"cnpj_tratado": "n_fundos"})
    .sort_values("n_fundos", ascending=False)
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Administradores", df_agg["administrador"].nunique())
c2.metric("Total de FIDCs", int(df_agg["n_fundos"].sum()))
if "taxa_administracao" in df_agg.columns:
    wa = (df_agg["taxa_administracao"] * df_agg["n_fundos"]).sum() / df_agg["n_fundos"].sum()
    c3.metric("Taxa Adm. Ponderada (por nº fundos)", f"{wa:.3f}%")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(
    ["📋 Ranking", "📊 Distribuição"]
)

with tab1:
    min_fundos = st.slider("Nº mínimo de fundos", 1, 10, 2, key="adm_min")
    df_rank = df_agg[df_agg["n_fundos"] >= min_fundos].sort_values("taxa_administracao")
    render_entity_ranking(df_rank, "administrador", "n_fundos", key="adm_rank", taxa_col_to_show="taxa_administracao")

with tab2:
    if "taxa_administracao" in df.columns:
        st.plotly_chart(histogram_taxa(df, "taxa_administracao"), use_container_width=True)
    else:
        st.info("Dados de taxa de administração não disponíveis.")
