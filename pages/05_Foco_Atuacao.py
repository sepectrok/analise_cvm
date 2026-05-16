"""Página 5 — Foco de Atuação"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Foco de Atuação | FIDC Analytics", page_icon="🎯", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import boxplot_by_group, bar_ranking, PALETTE, _base_layout
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.formatters import fmt_pct

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("🎯", "Foco de Atuação", "Taxa média por segmento e competitividade relativa")

taxa_cols_avail = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 3]

df_seg = (
    df.groupby("foco_atuacao")[taxa_cols_avail + ["cnpj_tratado"]]
    .agg({**{c: ["mean", "median", "count"] for c in taxa_cols_avail}, "cnpj_tratado": "count"})
    .reset_index()
)
# Flatten cols
df_seg.columns = ["foco_atuacao"] + [
    f"{c}_{s}" for c in taxa_cols_avail for s in ["mean", "median", "count"]
] + ["n_fundos"]

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 Taxas por Segmento", "📦 Boxplot", "📋 Tabela"])

with tab1:
    col_sel = st.selectbox("Tipo de Taxa",
                            taxa_cols_avail,
                            format_func=lambda c: TAXA_LABELS.get(c, c),
                            key="foco_taxa")
    mean_col = f"{col_sel}_mean"
    if mean_col in df_seg.columns:
        df_plot = df_seg.dropna(subset=[mean_col]).sort_values(mean_col, ascending=True)
        mkt_mean = df[col_sel].mean()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_plot[mean_col],
            y=df_plot["foco_atuacao"],
            orientation="h",
            marker=dict(
                color=df_plot[mean_col],
                colorscale=[[0, PALETTE["green"]], [0.5, PALETTE["blue"]], [1, PALETTE["copper"]]],
                showscale=False,
            ),
            text=[f"{v:.3f}% ({int(n)} fundos)" for v, n in
                  zip(df_plot[mean_col], df_plot["n_fundos"])],
            textposition="outside",
            textfont=dict(size=10, color=PALETTE["text"]),
        ))
        fig.add_vline(x=mkt_mean, line=dict(color=PALETTE["copper"], dash="dot", width=1.5),
                      annotation=dict(text=f"  Média: {mkt_mean:.3f}%",
                                      font=dict(size=10, color=PALETTE["copper"]), showarrow=False))
        fig.update_layout(**_base_layout(
            f"{TAXA_LABELS.get(col_sel,col_sel)} — Média por Segmento", 480))
        fig.update_xaxes(title_text="% a.a.")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_box = st.selectbox("Tipo de Taxa",
                            taxa_cols_avail,
                            format_func=lambda c: TAXA_LABELS.get(c, c),
                            key="foco_box")
    st.plotly_chart(boxplot_by_group(df, col_box, "foco_atuacao", height=500),
                    use_container_width=True)

with tab3:
    # Summary table
    rows = []
    for _, seg_row in df_seg.iterrows():
        r = {"Segmento": seg_row["foco_atuacao"], "Nº Fundos": int(seg_row["n_fundos"])}
        for c in taxa_cols_avail:
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Média %)"] = round(seg_row.get(f"{c}_mean", np.nan), 4)
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Med. %)"] = round(seg_row.get(f"{c}_median", np.nan), 4)
        rows.append(r)

    if rows:
        df_table = pd.DataFrame(rows).sort_values("Nº Fundos", ascending=False)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados para a tabela.")
