"""Página 4 — Agrupamento por Gestor"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np


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

if "Valor_PL" in df_ges.columns:
    agg_dict["Valor_PL"] = "sum"

if "taxa_inadimplencia" in df_ges.columns:
    agg_dict["taxa_inadimplencia"] = "mean"

if "taxa_gestao" in df_ges.columns and "Valor_PL" in df_ges.columns:
    df_ges = df_ges.copy()
    df_ges["remun_esperada"] = (((1 + df_ges["taxa_gestao"]/100) ** (21/252)) - 1) * df_ges["Valor_PL"]
    agg_dict["remun_esperada"] = "sum"

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

tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Ranking", "📊 Distribuição", "💰 Remuneração Esperada", "📉 Inadimplência"]
)

with tab1:
    col_opt, col_min = st.columns([2, 1])
    with col_opt:
        rank_metric = st.radio("Ordenar ranking por:", ["Taxa de Gestão", "AuM (Patrimônio Líquido)"], horizontal=True)
    with col_min:
        min_f = st.slider("Nº mínimo de fundos", 1, 10, 2, key="ges_min")
        
    if rank_metric == "Taxa de Gestão":
        df_rank = df_agg[df_agg["n_fundos"] >= min_f].sort_values("taxa_gestao")
        if "taxa_gestao" in df_rank.columns:
            st.plotly_chart(bar_ranking(df_rank.rename(columns={"taxa_gestao": "_val", "gestor": "_name"}), 
                                        "_val", "_name", title="Ranking de Taxa de Gestão", 
                                        top_n=20, highlight_name="Solis", height=500), 
                            use_container_width=True)
        render_entity_ranking(df_rank, "gestor", "n_fundos", key="ges_rank", taxa_col_to_show="taxa_gestao")
    else:
        if "Valor_PL" in df_agg.columns:
            df_rank = df_agg[df_agg["n_fundos"] >= min_f].sort_values("Valor_PL")
            st.plotly_chart(bar_ranking(df_rank.rename(columns={"Valor_PL": "_val", "gestor": "_name"}), 
                                        "_val", "_name", title="Ranking de AuM", 
                                        top_n=20, highlight_name="Solis", height=500, is_percent=False, is_currency=True), 
                            use_container_width=True)
            st.dataframe(
                df_rank[["gestor", "n_fundos", "Valor_PL"]].sort_values("Valor_PL", ascending=False).rename(columns={
                    "gestor": "Gestor", "n_fundos": "Nº Fundos", "Valor_PL": "AuM (R$)"
                }),
                use_container_width=True, hide_index=True,
                column_config={"AuM (R$)": st.column_config.NumberColumn(format="R$ %.2f")}
            )

with tab2:
    col_dist1, col_dist2 = st.columns(2)
    with col_dist1:
        if "taxa_gestao" in df.columns:
            st.plotly_chart(histogram_taxa(df, "taxa_gestao"), use_container_width=True)
        else:
            st.info("Dados de taxa de gestão não disponíveis.")
    with col_dist2:
        if "Valor_PL" in df.columns:
            import plotly.graph_objects as go
            fig_aum = go.Figure(go.Histogram(
                x=df["Valor_PL"].dropna(), nbinsx=30,
                marker=dict(color="#3B82F6", opacity=0.7, line=dict(color="#08090F", width=0.8))
            ))
            fig_aum.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#08090F",
                font=dict(family="Inter", size=12, color="#94A3B8"),
                height=400, margin=dict(l=16, r=24, t=44, b=36),
                title=dict(text="Distribuição de AuM", font=dict(family="Space Grotesk, Inter", size=15, color="#F1F5F9")),
                xaxis=dict(title="AuM (R$)", gridcolor="rgba(148,163,184,0.06)", tickfont=dict(size=10)),
                yaxis=dict(title="Fundos", gridcolor="rgba(148,163,184,0.06)")
            )
            st.plotly_chart(fig_aum, use_container_width=True)

with tab3:
    st.markdown('<div class="section-label">Remuneração Esperada</div>', unsafe_allow_html=True)
    st.caption("`((1 + taxa_gestão/100)^(21/252) - 1) * PL_CVM`. Estima a receita mensal gerada pela taxa de gestão.")
    if "remun_esperada" in df_agg.columns:
        df_rank_remun = df_agg[df_agg["n_fundos"] >= min_f].sort_values("remun_esperada")
        st.plotly_chart(bar_ranking(df_rank_remun.rename(columns={"remun_esperada": "_val", "gestor": "_name"}), 
                                    "_val", "_name", title="Remuneração Esperada por Gestor (R$/Mês)", 
                                    top_n=20, highlight_name="Solis", height=500, is_percent=False, is_currency=True), 
                        use_container_width=True)
                        
        st.dataframe(
            df_rank_remun[["gestor", "n_fundos", "remun_esperada"]].sort_values("remun_esperada", ascending=False).rename(columns={
                "gestor": "Gestor", "n_fundos": "Nº Fundos", "remun_esperada": "Remuneração Mensal Estimada (R$)"
            }),
            use_container_width=True, hide_index=True,
            column_config={"Remuneração Mensal Estimada (R$)": st.column_config.NumberColumn(format="R$ %.2f")}
        )
    else:
        st.info("Dados de PL Médio ou Taxa de Gestão não disponíveis para o cálculo.")

with tab4:
    st.markdown('<div class="section-label">Inadimplência Média por Gestor (PDD/DC)</div>', unsafe_allow_html=True)
    if "taxa_inadimplencia" in df_agg.columns and df_agg["taxa_inadimplencia"].notna().any():
        df_inad = (
            df_agg[df_agg["taxa_inadimplencia"].notna() & (df_agg["n_fundos"] >= 1)]
            .sort_values("taxa_inadimplencia", ascending=True)
        )
        st.plotly_chart(
            bar_ranking(
                df_inad.rename(columns={"taxa_inadimplencia": "_val", "gestor": "_name"}),
                "_val", "_name",
                title="Ranking de Inadimplência por Gestor (PDD/DC %)",
                top_n=25, highlight_name="Solis", height=600,
            ),
            use_container_width=True,
        )
        st.dataframe(
            df_inad[["gestor", "n_fundos", "taxa_inadimplencia"]]
            .sort_values("taxa_inadimplencia", ascending=False)
            .rename(columns={"gestor": "Gestor", "n_fundos": "Nº Fundos", "taxa_inadimplencia": "Inadimplência Média (%)"}),
            use_container_width=True, hide_index=True,
            column_config={"Inadimplência Média (%)": st.column_config.NumberColumn(format="%.2f%%")},
        )
    else:
        st.info("Dados de inadimplência não disponíveis para os gestores filtrados.")
