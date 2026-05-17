"""Página 6 — Comparador de Fundos"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Comparador | FIDC Analytics", page_icon="⚖️", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import radar_fund, PALETTE, _base_layout
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.formatters import fmt_pct
import plotly.graph_objects as go

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("⚖️", "Comparador de Fundos", "Análise lado a lado de múltiplos FIDCs")

# ── Fund selection ─────────────────────────────────────────────────────────────
fund_options = (
    df.dropna(subset=["nome_fundo"])[["cnpj_tratado", "nome_curto"]]
    .drop_duplicates()
    .sort_values("nome_curto")
)
fund_map = fund_options.set_index("cnpj_tratado")["nome_curto"].to_dict()

selected_cnpjs = st.multiselect(
    "Selecione os fundos para comparar (máx. 8)",
    options=fund_options["cnpj_tratado"].tolist(),
    format_func=lambda c: fund_map.get(c, c),
    max_selections=8,
    placeholder="Escolha 2 ou mais fundos…",
)

if len(selected_cnpjs) < 2:
    st.info("Selecione ao menos 2 fundos para iniciar a comparação.")
    st.stop()

df_sel = df[df["cnpj_tratado"].isin(selected_cnpjs)].copy()
taxa_cols = [c for c in TAXA_COLS if c in df_sel.columns]
st.markdown("---")

# ── Radar comparativo ─────────────────────────────────────────────────────────
col_radar, col_score = st.columns([1.2, 0.8])

with col_radar:
    st.markdown('<div class="section-label">Radar Comparativo</div>', unsafe_allow_html=True)
    st.plotly_chart(radar_fund(df_sel, selected_cnpjs), use_container_width=True)

with col_score:
    st.markdown('<div class="section-label">Score Consolidado de Taxas</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:12px;">
    Score = soma ponderada das taxas. Menor score = estrutura de custos mais competitiva.
    </div>""", unsafe_allow_html=True)

    score_rows = []
    for cnpj in selected_cnpjs:
        row = df_sel[df_sel["cnpj_tratado"] == cnpj].iloc[0]
        total = sum([row[c] for c in taxa_cols if c in row.index and not np.isnan(row[c])])
        score_rows.append({"Fundo": row["nome_curto"], "Score Total (%)": round(total, 4)})

    df_score = pd.DataFrame(score_rows).sort_values("Score Total (%)")
    st.dataframe(df_score, use_container_width=True, hide_index=True,
                 column_config={"Score Total (%)": st.column_config.NumberColumn(format="%.4f%%")})

st.markdown("---")

# ── Side-by-side table ────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Comparativo Detalhado</div>', unsafe_allow_html=True)
compare_rows = []
for col in taxa_cols:
    row_data = {"Taxa": TAXA_LABELS.get(col, col)}
    for cnpj in selected_cnpjs:
        r = df_sel[df_sel["cnpj_tratado"] == cnpj]
        val = r[col].values[0] if not r.empty and col in r.columns else np.nan
        row_data[fund_map.get(cnpj, cnpj)[:30]] = round(val, 4) if not np.isnan(val) else None

    # Market average
    row_data["Média Mercado"] = round(df[col].mean(), 4) if col in df.columns else None
    compare_rows.append(row_data)

df_compare = pd.DataFrame(compare_rows)
col_cfg = {"Taxa": st.column_config.TextColumn(width="medium")}
for c in df_compare.columns[1:]:
    col_cfg[c] = st.column_config.NumberColumn(c, format="%.4f%%", width="small")

st.dataframe(df_compare, use_container_width=True, hide_index=True, column_config=col_cfg)

st.markdown("---")

# ── Bar chart ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Ranking de Taxas — Bar Chart</div>', unsafe_allow_html=True)
col_sel = st.selectbox("Tipo de Taxa", taxa_cols, format_func=lambda c: TAXA_LABELS.get(c, c), key="comp_bar")

fig = go.Figure()
df_bar = df_sel.dropna(subset=[col_sel]).sort_values(col_sel)
fig.add_trace(go.Bar(
    x=df_bar["nome_curto"].str[:45],
    y=df_bar[col_sel],
    marker=dict(
        color=df_bar[col_sel],
        colorscale=[[0, PALETTE["green"]], [0.5, PALETTE["blue"]], [1, PALETTE["copper"]]],
        showscale=False,
    ),
    text=[f"{v:.3f}%" for v in df_bar[col_sel]],
    textposition="outside",
    textfont=dict(size=10, color=PALETTE["text"]),
))
mkt_mean = df[col_sel].mean()
fig.add_hline(y=mkt_mean, line=dict(color=PALETTE["copper"], dash="dot", width=1.5),
              annotation=dict(text=f"Média mercado: {mkt_mean:.3f}%",
                              font=dict(size=10, color=PALETTE["copper"])))
fig.update_layout(**_base_layout(f"{TAXA_LABELS.get(col_sel,col_sel)} — Fundos Selecionados", 400))
fig.update_xaxes(tickangle=-20, tickfont=dict(size=9))
fig.update_yaxes(title_text="% a.a.")
st.plotly_chart(fig, use_container_width=True)
