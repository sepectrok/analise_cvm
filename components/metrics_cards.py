"""Metrics Cards — Solis Investimentos Platform — Premium v2"""

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


def institutional_header(title: str, subtitle: str = "", logo_path: str = "logo_solis_v.png"):
    import os, base64
    logo_html = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" style="height:48px; width:auto; filter: brightness(1.1);" />'
    else:
        logo_html = '<span style="font-family: Space Grotesk; font-weight:700; font-size:1.2rem; color: var(--accent-primary);">SOLIS</span>'

    st.markdown(f"""
    <div class="inst-header">
        <div>{logo_html}</div>
        <div class="header-text">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", delta: str = "",
             delta_up: bool | None = None, card_class: str = "") -> str:
    delta_class = "up" if delta_up else ("down" if delta_up is False else "")
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card {card_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
        {delta_html}
    </div>
    """


def render_executive_kpis(df_solis: pd.DataFrame, df_mercado: pd.DataFrame):
    """Render the top KPI cards comparing Solis vs Mercado."""
    n_solis = len(df_solis)
    n_mercado = len(df_mercado)

    med_gestao_solis = df_solis["taxa_gestao"].mean() if "taxa_gestao" in df_solis.columns else np.nan
    med_gestao_mercado = df_mercado["taxa_gestao"].mean() if "taxa_gestao" in df_mercado.columns else np.nan

    med_perf_solis = df_solis["taxa_performance"].mean() if "taxa_performance" in df_solis.columns else np.nan
    med_perf_mercado = df_mercado["taxa_performance"].mean() if "taxa_performance" in df_mercado.columns else np.nan

    med_inad_solis   = df_solis["taxa_inadimplencia"].mean()   if "taxa_inadimplencia" in df_solis.columns   else np.nan
    med_inad_mercado = df_mercado["taxa_inadimplencia"].mean() if "taxa_inadimplencia" in df_mercado.columns else np.nan

    def calc_delta(val1, val2):
        if pd.isna(val1) or pd.isna(val2) or val2 == 0:
            return None
        return val1 < val2

    aum_solis = df_solis["Valor_PL"].sum() if "Valor_PL" in df_solis.columns else 0
    aum_mercado = df_mercado["Valor_PL"].sum() if "Valor_PL" in df_mercado.columns else 0

    def fmt_aum(val):
        if pd.isna(val): return "R$ 0.00"
        if val >= 1e9: return f"R$ {val/1e9:.2f} Bi"
        if val >= 1e6: return f"R$ {val/1e6:.2f} Mi"
        return f"R$ {val:,.2f}"

    cards = [
        kpi_card("Fundos Geridos", str(n_solis), "Solis Investimentos",
                 delta=f"vs {n_mercado} no mercado", delta_up=None, card_class="kpi-solis"),
        kpi_card("AuM (Patrimônio Líquido)", fmt_aum(aum_solis), "Solis Investimentos",
                 delta=f"Mercado (Fora Solis): {fmt_aum(aum_mercado)}",
                 delta_up=None, card_class="kpi-solis"),
        kpi_card("Taxa Média de Gestão", fmt_pct(med_gestao_solis), "% a.a. · Solis",
                 delta=f"Mercado (Fora Solis): {fmt_pct(med_gestao_mercado)}",
                 delta_up=calc_delta(med_gestao_solis, med_gestao_mercado), card_class="kpi-solis"),
        kpi_card("Taxa Média de Performance", fmt_pct(med_perf_solis), "% a.a. · Solis",
                 delta=f"Mercado (Fora Solis): {fmt_pct(med_perf_mercado)}",
                 delta_up=calc_delta(med_perf_solis, med_perf_mercado), card_class="kpi-solis"),
        kpi_card("Inadimplência Média (PDD/DC)", fmt_pct(med_inad_solis), "% · Solis",
                 delta=f"Mercado (Fora Solis): {fmt_pct(med_inad_mercado)}",
                 delta_up=calc_delta(med_inad_solis, med_inad_mercado), card_class="kpi-solis"),
    ]

    cols = st.columns(5)
    for i, card in enumerate(cards):
        with cols[i]:
            st.markdown(card, unsafe_allow_html=True)


def render_general_kpis(df: pd.DataFrame):
    """Render 6 KPI cards for general market overview."""
    n_fundos = len(df)
    n_adm    = df["administrador"].nunique()
    n_ges    = df["gestor"].nunique()
    n_focos  = df["foco_atuacao"].nunique()

    adm_col = df["taxa_administracao"] if "taxa_administracao" in df.columns else pd.Series(dtype=float)
    ges_col = df["taxa_gestao"]        if "taxa_gestao"        in df.columns else pd.Series(dtype=float)
    inad_col = df["taxa_inadimplencia"] if "taxa_inadimplencia" in df.columns else pd.Series(dtype=float)

    med_adm  = adm_col.mean()
    med_ges  = ges_col.mean()
    med_inad = inad_col.mean()

    aum_total = df["Valor_PL"].sum() if "Valor_PL" in df.columns else 0

    def fmt_aum(val):
        if pd.isna(val): return "R$ 0.00"
        if val >= 1e9: return f"R$ {val/1e9:.2f} Bi"
        if val >= 1e6: return f"R$ {val/1e6:.2f} Mi"
        return f"R$ {val:,.2f}"

    cards = [
        kpi_card("AuM Mercado (PL Total)", fmt_aum(aum_total), "Patrimônio Líquido", card_class="kpi-market"),
        kpi_card("FIDCs Analisados",    str(n_fundos),    f"{n_focos} segmentos", card_class="kpi-market"),
        kpi_card("Administradores",     str(n_adm),       "entidades únicas", card_class="kpi-market"),
        kpi_card("Gestores",            str(n_ges),       "entidades únicas", card_class="kpi-market"),
        kpi_card("Média Adm.",          fmt_pct(med_adm), f"mediana: {fmt_pct(adm_col.median())}", card_class="kpi-market"),
        kpi_card("Média Gestão",        fmt_pct(med_ges), f"mediana: {fmt_pct(ges_col.median())}", card_class="kpi-market"),
        kpi_card("Inadimplência Méd. (PDD/DC)", fmt_pct(med_inad), f"mediana: {fmt_pct(inad_col.median())}", card_class="kpi-market"),
    ]

    cols = st.columns(4)
    for i in range(4):
        with cols[i]:
            st.markdown(cards[i], unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    cols2 = st.columns(3)
    for i in range(4, 7):
        with cols2[i - 4]:
            st.markdown(cards[i], unsafe_allow_html=True)


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
