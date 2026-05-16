"""Página 1 — Análise de Taxas"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Análise de Taxas | FIDC Analytics", page_icon="📈", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, stats_table
from components.charts import histogram_taxa, boxplot_by_group, violin_taxa, scatter_two_taxas, multi_box_taxas
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS, get_available_taxas

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("📈", "Análise de Taxas",
            "Distribuições estatísticas e comparativos entre tipos de taxa")

available = get_available_taxas(df)
if not available:
    st.warning("Nenhuma taxa disponível com os filtros aplicados.")
    st.stop()

# Seletor de taxa
col_sel, _ = st.columns([1, 3])
with col_sel:
    taxa_sel = st.selectbox(
        "Tipo de Taxa",
        options=available,
        format_func=lambda c: TAXA_LABELS.get(c, c),
    )

st.markdown("---")

# ── Tab layout ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Histograma", "📦 Boxplot por Segmento", "🎻 Violin", "🔀 Scatter", "📋 Estatísticas"]
)

with tab1:
    st.plotly_chart(histogram_taxa(df, taxa_sel, height=420), use_container_width=True)

with tab2:
    st.plotly_chart(boxplot_by_group(df, taxa_sel, "foco_atuacao", height=460), use_container_width=True)

with tab3:
    st.plotly_chart(multi_box_taxas(df, height=400), use_container_width=True)

with tab4:
    other_taxas = [c for c in available if c != taxa_sel]
    if other_taxas:
        col_y = st.selectbox("Eixo Y", options=other_taxas,
                              format_func=lambda c: TAXA_LABELS.get(c, c))
        st.plotly_chart(scatter_two_taxas(df, taxa_sel, col_y, height=440),
                        use_container_width=True)
    else:
        st.info("Selecione ao menos 2 tipos de taxa para visualizar scatter.")

with tab5:
    st.markdown(f"**{TAXA_LABELS.get(taxa_sel, taxa_sel)}** — Estatísticas Descritivas")
    stats_table(df[taxa_sel], TAXA_LABELS.get(taxa_sel, taxa_sel))

    # All taxas stats
    st.markdown("---")
    st.markdown("**Resumo de Todas as Taxas**")
    rows = []
    for col in TAXA_COLS:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                rows.append({
                    "Taxa": TAXA_LABELS.get(col, col),
                    "N Fundos": len(s),
                    "Média (%)": round(s.mean(), 4),
                    "Mediana (%)": round(s.median(), 4),
                    "Desvio (%)": round(s.std(), 4),
                    "Mín (%)": round(s.min(), 4),
                    "Máx (%)": round(s.max(), 4),
                })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
