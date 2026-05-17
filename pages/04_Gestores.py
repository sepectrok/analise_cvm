"""Página 4 — Agrupamento por Gestor"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Gestores | FIDC Analytics", page_icon="👔", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, kpi_card, insight_card
from components.charts import bar_ranking, heatmap_entity_taxa, histogram_taxa
from components.tables import render_entity_ranking
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.formatters import fmt_pct

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("👔", "Agrupamento por Gestor",
            "Concentração, clusterização e benchmark de taxas de gestão")

df_ges = df.dropna(subset=["gestor"])
if df_ges.empty:
    st.warning("Nenhum dado disponível para gestores com os filtros aplicados.")
    st.stop()

taxa_cols_avail = [c for c in TAXA_COLS if c in df_ges.columns]
agg_dict = {c: "mean" for c in taxa_cols_avail}
agg_dict["cnpj_tratado"] = "count"

df_agg = (
    df_ges.groupby("gestor")
    .agg(agg_dict)
    .reset_index()
    .rename(columns={"cnpj_tratado": "n_fundos"})
    .sort_values("n_fundos", ascending=False)
)

if not df_agg.empty and "taxa_gestao" in df_agg.columns:
    max_idx = df_agg["taxa_gestao"].idxmax()
    if pd.notna(max_idx):
        df_agg = df_agg.drop(max_idx)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Gestores", df_agg["gestor"].nunique())
c2.metric("Total FIDCs", int(df_agg["n_fundos"].sum()))
if "taxa_gestao" in df_agg.columns:
    wa = (df_agg["taxa_gestao"].fillna(0) * df_agg["n_fundos"]).sum() / df_agg["n_fundos"].sum()
    c3.metric("Taxa Gestão Pond.", f"{wa:.3f}%")
    top_ges = df_agg.dropna(subset=["taxa_gestao"]).nlargest(1, "taxa_gestao").iloc[0]
    c4.metric("Maior Taxa Gestão", fmt_pct(top_ges["taxa_gestao"]),
              delta=f"↑ {top_ges['gestor'][:25]}", delta_color="inverse")

st.markdown("---")

tab1, tab2 = st.tabs(
    ["📋 Ranking", "📊 Distribuição"]
)

with tab1:
    min_f = st.slider("Nº mínimo de fundos", 1, 10, 2, key="ges_min")
    df_rank = df_agg[df_agg["n_fundos"] >= min_f].sort_values("taxa_gestao")
    if "taxa_gestao" in df_rank.columns:
        st.plotly_chart(bar_ranking(df_rank.rename(columns={"taxa_gestao": "_val", "gestor": "_name"}), 
                                    "_val", "_name", title="Ranking de Taxa de Gestão", 
                                    top_n=20, highlight_name="Solis", height=500), 
                        use_container_width=True)
    render_entity_ranking(df_rank, "gestor", "n_fundos", key="ges_rank", taxa_col_to_show="taxa_gestao")

with tab2:
    if "taxa_gestao" in df.columns:
        st.plotly_chart(histogram_taxa(df, "taxa_gestao"), use_container_width=True)
    else:
        st.info("Dados de taxa de gestão não disponíveis.")
