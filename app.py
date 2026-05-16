"""
FIDC Analytics Platform — Main Entry Point
Plataforma institucional de benchmarking de taxas de FIDCs
"""

import streamlit as st

st.set_page_config(
    page_title="Analise de FIDCs - Dados | Benchmarking Institucional",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Shared helpers (import after set_page_config) ───────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, render_executive_kpis, kpi_card
from components.charts import donut_foco, bar_ranking, multi_box_taxas, heatmap_corr
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.insights import generate_insights
from utils.pdf_export import gerar_pdf

# ─── CSS ──────────────────────────────────────────────────────────────────────
load_css()

# ─── Data ─────────────────────────────────────────────────────────────────────
with st.spinner("Carregando base de dados…"):
    df_full = build_df_fidc()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

# ─── Exportação PDF (sidebar) ───────────────────────────────────────────────
# with st.sidebar:
#     st.markdown("---")
#     st.markdown(
#         '<div class="section-label">Exportar Relatório</div>',
#         unsafe_allow_html=True,
#     )
#     import datetime as _dt
#     _pdf_bytes = gerar_pdf(df, filters)
#     st.download_button(
#         label="📄 Exportar PDF",
#         data=_pdf_bytes,
#         file_name=f"FIDC_Analise_Taxas_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
#         mime="application/pdf",
#         use_container_width=True,
#         help="Relatório com KPIs e estatísticas de todas as taxas",
#     )

# ─── Page Header ──────────────────────────────────────────────────────────────
page_header(
    "⬡",
    "Analise de FIDCs — Dados",
    f"Benchmarking institucional de taxas · {len(df)} fundos analisados"
)

# ─── KPI Row ──────────────────────────────────────────────────────────────────
render_executive_kpis(df)

st.markdown("---")

# ─── Row 2: Charts ────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    st.markdown('<div class="section-label">Distribuição por Segmento</div>', unsafe_allow_html=True)
    st.plotly_chart(donut_foco(df), use_container_width=True)

with col_right:
    st.markdown('<div class="section-label">Comparativo Geral de Taxas</div>', unsafe_allow_html=True)
    st.plotly_chart(multi_box_taxas(df, height=380), use_container_width=True)

st.markdown("---")

# ─── Row 3: Top Admins + Insights ─────────────────────────────────────────────
col_l, col_r = st.columns([1.1, 0.9])

with col_l:
    st.markdown('<div class="section-label">Ranking — Administradores por Nº de Fundos</div>',
                unsafe_allow_html=True)
    adm_count = (
        df.dropna(subset=["administrador"])
        .groupby("administrador")
        .size()
        .reset_index(name="n_fundos")
        .nlargest(10, "n_fundos")
    )
    st.plotly_chart(
        bar_ranking(adm_count.rename(columns={"n_fundos": "_val", "administrador": "_name"}),
                    "_val", "_name",
                    title="Top 10 Administradores",
                    top_n=10, height=380, is_percent=False),
        use_container_width=True,
    )

with col_r:
    st.markdown('<div class="section-label">Ranking — Gestores por Nº de Fundos</div>',
                unsafe_allow_html=True)
    ges_count = (
        df.dropna(subset=["gestor"])
        .groupby("gestor")
        .size()
        .reset_index(name="n_fundos")
    )
    st.plotly_chart(
        bar_ranking(ges_count.rename(columns={"n_fundos": "_val", "gestor": "_name"}),
                    "_val", "_name",
                    title="Top 10 Gestores",
                    top_n=10, height=380, is_percent=False),
        use_container_width=True,
    )

st.markdown("---")

# ─── Row 4: Ranking de Entidades por Taxa Média (Bar Chart) ───────────────────
st.markdown('<div class="section-label">Ranking Institucional por Taxa Média</div>', unsafe_allow_html=True)

entidade_opt = st.radio("Selecione a Visão:", ["Administradores (Taxa de Administração)", "Gestores (Taxa de Gestão)"], horizontal=True)

if "Administradores" in entidade_opt:
    ent_col = "administrador"
    tax_col = "taxa_administracao"
    title = "Ranking — Taxa de Administração Média por Administrador"
else:
    ent_col = "gestor"
    tax_col = "taxa_gestao"
    title = "Ranking — Taxa de Gestão Média por Gestor"

df_ent = df.dropna(subset=[ent_col, tax_col])
if not df_ent.empty:
    df_agg = (
        df_ent.groupby(ent_col)
        .agg({tax_col: "mean"})
        .reset_index()
    )
    
    col1, col2 = st.columns([1, 3])
    with col1:
        top_n = st.slider("Número de Entidades", 5, 50, 15, key="app_ent_topn")

    df_bar = df_agg.copy()
    df_bar["_name"] = df_bar[ent_col].str[:40]
    
    fig = bar_ranking(df_bar.rename(columns={tax_col: "_val"}),
                      "_val", "_name",
                      title=title,
                      top_n=top_n)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Nenhum dado encontrado para analisar {tax_col} de {ent_col}.")

st.markdown("---")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:32px 0 16px; color:var(--text-muted); font-size:0.72rem;'>
    Analise de FIDC's · Dados extraídos de regulamentos via CVM/FNET · Uso interno
</div>
""", unsafe_allow_html=True)
