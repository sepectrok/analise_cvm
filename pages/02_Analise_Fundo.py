"""Página 2 — Análise por Fundo"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Análise por Fundo | FIDC Analytics", page_icon="🔍", layout="wide")

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, kpi_card, insight_card
from components.charts import radar_fund
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.formatters import fmt_pct, fmt_delta_pp
from utils.insights import rank_percentile

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("🔍", "Análise por Fundo", "Deep dive em um FIDC específico vs. mercado")

if df.empty:
    st.warning("Nenhum fundo disponível com os filtros aplicados.")
    st.stop()

# ── Seleção do fundo ───────────────────────────────────────────────────────────
fund_options = df.dropna(subset=["nome_fundo"])[["cnpj_tratado", "nome_curto"]].drop_duplicates()
fund_options = fund_options.sort_values("nome_curto")

selected = st.selectbox(
    "Selecione o Fundo",
    options=fund_options["cnpj_tratado"].tolist(),
    format_func=lambda c: fund_options.set_index("cnpj_tratado").loc[c, "nome_curto"],
)

row = df[df["cnpj_tratado"] == selected]
if row.empty:
    st.warning("Fundo não encontrado.")
    st.stop()
row = row.iloc[0]

st.markdown("---")

# ── Info header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:16px 20px; background:var(--bg-card); border:1px solid var(--border);
            border-radius:var(--radius); margin-bottom:24px;">
  <div style="font-size:1.05rem; font-weight:600; color:var(--text-primary); font-family:'Space Grotesk',sans-serif;">
    {row['nome_fundo']}
  </div>
  <div style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">
    CNPJ: {row['cnpj_tratado']} &nbsp;·&nbsp;
    Segmento: <b style="color:var(--text-secondary)">{row['foco_atuacao']}</b> &nbsp;·&nbsp;
    Administrador: <b style="color:var(--text-secondary)">{row.get('administrador','—')}</b> &nbsp;·&nbsp;
    Gestor: <b style="color:var(--text-secondary)">{row.get('gestor','—')}</b>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards: taxa do fundo vs. média ────────────────────────────────────────
available_cols = [c for c in TAXA_COLS if c in df.columns and not np.isnan(row.get(c, np.nan))]
mkt_means = {c: df[c].mean() for c in available_cols if c in df.columns}

def fmt_percentile_label(p):
    if p is None or np.isnan(p):
        return ""
    return f"{p:.0f}º percentil"

if available_cols:
    cards_html = ""
    for col in available_cols:
        val = row[col]
        mkt = mkt_means.get(col, np.nan)
        delta_str, is_up = fmt_delta_pp(val, mkt)
        pct_rank = rank_percentile(df, col, selected)
        sub = f"Mercado: {fmt_pct(mkt)} · {fmt_percentile_label(pct_rank)}" if pct_rank else f"Mercado: {fmt_pct(mkt)}"
        cards_html += kpi_card(
            TAXA_LABELS.get(col, col),
            fmt_pct(val),
            sub=f"Média de mercado: {fmt_pct(mkt)}",
            delta=delta_str,
            delta_up=is_up,
        )

    # Render in grid of 3
    cols_all = available_cols
    for chunk_start in range(0, len(cols_all), 3):
        chunk = cols_all[chunk_start:chunk_start+3]
        cols = st.columns(len(chunk))
        for i, col in enumerate(chunk):
            val = row[col]
            mkt = mkt_means.get(col, np.nan)
            delta_str, is_up = fmt_delta_pp(val, mkt)
            pct_rank = rank_percentile(df, col, selected)
            with cols[i]:
                st.markdown(kpi_card(
                    TAXA_LABELS.get(col, col),
                    fmt_pct(val),
                    sub=f"Média mercado: {fmt_pct(mkt)}",
                    delta=delta_str,
                    delta_up=is_up,
                ), unsafe_allow_html=True)
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

st.markdown("---")

# ── Radar chart ───────────────────────────────────────────────────────────────
col_radar, col_peers = st.columns([1, 1])

with col_radar:
    st.markdown('<div class="section-label">Radar de Taxas</div>', unsafe_allow_html=True)
    st.plotly_chart(radar_fund(df, [selected]), use_container_width=True)

with col_peers:
    st.markdown('<div class="section-label">Peers do Mesmo Segmento</div>', unsafe_allow_html=True)
    peers = df[df["foco_atuacao"] == row["foco_atuacao"]].dropna(subset=["taxa_administracao"])
    if len(peers) > 1:
        peers_disp = peers[["nome_curto"] + [c for c in TAXA_COLS if c in peers.columns]].copy()
        peers_disp = peers_disp.rename(columns={
            "nome_curto": "Fundo",
            **{c: TAXA_LABELS.get(c, c).replace("Taxa de ", "") for c in TAXA_COLS}
        })
        # Highlight selected fund
        st.dataframe(peers_disp, use_container_width=True, hide_index=True, height=380)
    else:
        st.info("Sem peers no mesmo segmento com dados suficientes.")

# ── Market position insight ───────────────────────────────────────────────────
if "taxa_administracao" in df.columns and not np.isnan(row.get("taxa_administracao", np.nan)):
    val = row["taxa_administracao"]
    mkt = df["taxa_administracao"].mean()
    diff = (val / mkt - 1) * 100
    icon = "🔴" if diff > 20 else ("🟢" if diff < -10 else "🟡")
    tipo = "warning" if diff > 20 else ("success" if diff < -10 else "info")
    st.markdown(insight_card(
        icon,
        "Posicionamento de Mercado",
        f"Taxa de administração de <b>{fmt_pct(val)}</b> — "
        f"<b>{'acima' if diff > 0 else 'abaixo'}</b> da média do mercado em <b>{abs(diff):.0f}%</b>.",
        tipo,
    ), unsafe_allow_html=True)
