"""Página 5 — Foco de Atuação"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Foco de Atuação | FIDC Analytics", page_icon="🎯", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import boxplot_by_group, PALETTE, _base_layout
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
    col_sel = st.selectbox(
        "Tipo de Taxa",
        taxa_cols_avail,
        format_func=lambda c: TAXA_LABELS.get(c, c),
        key="foco_taxa",
    )
    mean_col = f"{col_sel}_mean"

    if mean_col not in df_seg.columns:
        st.info("Sem dados suficientes para este tipo de taxa.")
        st.stop()

    taxa_label = TAXA_LABELS.get(col_sel, col_sel)

    # ── Gráfico comparativo Solis vs Mercado (apenas para gestao e performance) ──
    if col_sel in ["taxa_gestao", "taxa_performance"]:
        is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
        df_solis  = df[is_solis]
        df_mercado = df[~is_solis]

        df_plot = df_seg.dropna(subset=[mean_col]).sort_values(mean_col, ascending=True)
        focos = df_plot["foco_atuacao"].tolist()

        solis_means   = df_solis.groupby("foco_atuacao")[col_sel].mean().to_dict()
        mercado_means = df_mercado.groupby("foco_atuacao")[col_sel].mean().to_dict()
        mkt_mean      = df_mercado[col_sel].mean()
        solis_mean    = df_solis[col_sel].mean()

        n_cats  = len(focos)
        chart_h = max(700, n_cats * 55 + 120)

        fig = go.Figure()

        # ── Barras sem texto (sem sobreposição) ──
        fig.add_trace(go.Bar(
            y=focos,
            x=[mercado_means.get(f, np.nan) for f in focos],
            name="Mercado",
            orientation="h",
            marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Mercado: %{x:.3f}%<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=focos,
            x=[solis_means.get(f, np.nan) for f in focos],
            name="Solis Investimentos",
            orientation="h",
            marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Solis: %{x:.3f}%<extra></extra>",
        ))

        # ── Linha + badge: Média Mercado (topo) ──
        fig.add_vline(
            x=mkt_mean,
            line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2),
        )
        fig.add_annotation(
            x=mkt_mean, y=1.01, yref="paper",
            text=f"Méd. Mercado: <b>{mkt_mean:.3f}%</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=10, color="#FFFFFF"),
            bgcolor="rgba(217,119,6,0.8)", borderpad=5,
            bordercolor="rgba(0,0,0,0)",
        )

        # ── Linha + badge: Média Solis (20% abaixo para não sobrepor) ──
        if pd.notna(solis_mean):
            fig.add_vline(
                x=solis_mean,
                line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2),
            )
            fig.add_annotation(
                x=solis_mean, y=0.86, yref="paper",
                text=f"Méd. Solis: <b>{solis_mean:.3f}%</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(size=10, color="#FFFFFF"),
                bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                bordercolor="rgba(0,0,0,0)",
            )

        # ── Layout ──
        _layout = _base_layout("", chart_h)
        for _k in ("margin", "font", "legend"):
            _layout.pop(_k, None)
        fig.update_layout(
            **_layout,
            barmode="group",
            bargap=0.28,
            bargroupgap=0.06,
            margin=dict(l=240, r=40, t=20, b=60),
            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
            legend=dict(
                orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                font=dict(size=12), bgcolor="rgba(0,0,0,0)",
            ),
        )
        fig.update_xaxes(title_text="% a.a.", title_font=dict(size=12), tickfont=dict(size=11))
        fig.update_yaxes(tickfont=dict(size=11), automargin=True)

        # Título fora do gráfico (evita sobreposição com legenda)
        st.markdown(f"**{taxa_label} — Média por Segmento · Mercado vs Solis**")
        st.plotly_chart(fig, use_container_width=True)

    # ── Gráfico geral (outras taxas) ──────────────────────────────────────────
    else:
        df_plot  = df_seg.dropna(subset=[mean_col]).sort_values(mean_col, ascending=True)
        mkt_mean = df[col_sel].mean()

        n_cats  = len(df_plot)
        chart_h = max(500, n_cats * 38 + 80)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_plot[mean_col],
            y=df_plot["foco_atuacao"],
            orientation="h",
            marker=dict(
                color=df_plot[mean_col],
                colorscale=[[0, PALETTE["teal"]], [0.5, PALETTE["blue"]], [1, PALETTE["copper"]]],
                showscale=False,
            ),
            text=[f"{v:.3f}%" for v in df_plot[mean_col]],
            textposition="outside",
            textfont=dict(size=11, color=PALETTE["text"]),
            hovertemplate="<b>%{y}</b><br>Média: %{x:.3f}%<extra></extra>",
        ))
        fig.add_vline(
            x=mkt_mean,
            line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2),
        )
        fig.add_annotation(
            x=mkt_mean, y=1.01, yref="paper",
            text=f"Média Geral: <b>{mkt_mean:.3f}%</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=10, color="#FFFFFF"),
            bgcolor="rgba(217,119,6,0.8)", borderpad=5,
            bordercolor="rgba(0,0,0,0)",
        )

        _layout = _base_layout("", chart_h)
        for _k in ("margin", "font", "legend"):
            _layout.pop(_k, None)
        fig.update_layout(
            **_layout,
            bargap=0.35,
            margin=dict(l=240, r=80, t=20, b=50),
            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
        )
        fig.update_xaxes(title_text="% a.a.", title_font=dict(size=12), tickfont=dict(size=11))
        fig.update_yaxes(tickfont=dict(size=11), automargin=True)

        st.markdown(f"**{taxa_label} — Média por Segmento**")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_box = st.selectbox(
        "Tipo de Taxa",
        taxa_cols_avail,
        format_func=lambda c: TAXA_LABELS.get(c, c),
        key="foco_box",
    )
    st.plotly_chart(boxplot_by_group(df, col_box, "foco_atuacao", height=500), use_container_width=True)

with tab3:
    rows = []
    for _, seg_row in df_seg.iterrows():
        r = {"Segmento": seg_row["foco_atuacao"], "Nº Fundos": int(seg_row["n_fundos"])}
        for c in taxa_cols_avail:
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Média %)"]  = round(seg_row.get(f"{c}_mean",   np.nan), 4)
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Med. %)"]   = round(seg_row.get(f"{c}_median", np.nan), 4)
        rows.append(r)

    if rows:
        df_table = pd.DataFrame(rows).sort_values("Nº Fundos", ascending=False)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados para a tabela.")
