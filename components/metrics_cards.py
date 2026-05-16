"""Metrics Cards — FIDC Analytics Platform"""

import numpy as np
import pandas as pd
import streamlit as st
from utils.data_loader import TAXA_COLS, TAXA_LABELS
from utils.formatters import fmt_pct, fmt_num


def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-header">
        <span class="icon">{icon}</span>
        <div>
            <h1>{title}</h1>
            {"" if not subtitle else f'<p>{subtitle}</p>'}
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", delta: str = "",
             delta_up: bool | None = None) -> str:
    delta_class = "up" if delta_up else ("down" if delta_up is False else "")
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
        {delta_html}
    </div>
    """


def render_executive_kpis(df: pd.DataFrame):
    """Render the 6 top KPI cards for Visão Executiva."""
    n_fundos = len(df)
    n_adm    = df["administrador"].nunique()
    n_ges    = df["gestor"].nunique()
    n_focos  = df["foco_atuacao"].nunique()

    adm_col = df["taxa_administracao"] if "taxa_administracao" in df.columns else pd.Series(dtype=float)
    ges_col = df["taxa_gestao"]        if "taxa_gestao"        in df.columns else pd.Series(dtype=float)

    med_adm  = adm_col.mean()
    med_ges  = ges_col.mean()
    max_taxa = max(
        [df[c].max() for c in TAXA_COLS if c in df.columns and df[c].notna().any()],
        default=np.nan
    )

    cards = [
        kpi_card("FIDCs Analisados",          str(n_fundos),         f"{n_focos} segmentos"),
        kpi_card("Administradores",            str(n_adm),            "entidades únicas"),
        kpi_card("Gestores",                   str(n_ges),            "entidades únicas"),
        kpi_card("Média Taxa de Adm.",         fmt_pct(med_adm),      "% a.a.  ·  mediana: " + fmt_pct(adm_col.median())),
        kpi_card("Média Taxa de Gestão",       fmt_pct(med_ges),      "% a.a.  ·  mediana: " + fmt_pct(ges_col.median())),
        kpi_card("Maior Taxa de Performance",      fmt_pct(max_taxa),     "% a.a."),
    ]

    cols = st.columns(3)
    for i, card in enumerate(cards):
        with cols[i % 3]:
            st.markdown(card, unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


def insight_card(icon: str, title: str, text: str, card_type: str = "info") -> str:
    return f"""
    <div class="insight-card {card_type}">
        <span class="ic-icon">{icon}</span>
        <div>
            <div class="ic-title">{title}</div>
            <div class="ic-text">{text}</div>
        </div>
    </div>
    """


def stats_table(series: pd.Series, label: str = ""):
    """Display a clean stats table for a taxa series."""
    s = series.dropna()
    if s.empty:
        st.info("Sem dados suficientes.")
        return

    data = {
        "Estatística": ["Qtd. de Fundos", "Média", "Mediana", "Desvio Padrão",
                        "Mínimo", "P25", "P75", "Máximo"],
        "Valor": [
            f"{len(s):,}",
            fmt_pct(s.mean()),
            fmt_pct(s.median()),
            fmt_pct(s.std()),
            fmt_pct(s.min()),
            fmt_pct(s.quantile(0.25)),
            fmt_pct(s.quantile(0.75)),
            fmt_pct(s.max()),
        ],
    }
    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Estatística": st.column_config.TextColumn(width="medium"),
            "Valor":       st.column_config.TextColumn(width="small"),
        },
    )
