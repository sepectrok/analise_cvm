"""Página 9 — Principais Insights"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.colors as pc

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, kpi_card
from components.charts import PALETTE, _base_layout
from utils.data_loader import (
    build_principais_gestoras,
    build_prest_servico,
    PRESTADOR_TIPOS,
    TAXA_COLS, TAXA_LABELS,
    CVNP_COLS, CVNP_LABELS,
    AGING_COLS, AGING_LABELS,
    weighted_mean, weighted_mean_by_group,
)
from utils.formatters import fmt_pct

load_css()

# ── Carregar dados ────────────────────────────────────────────────────────────
# Carrega todo o histórico; o filtro de data é controlado pela sidebar
df_principais = build_principais_gestoras()
filters = render_sidebar(df_principais, show_date_filter=True)
# df: com todos os filtros (inclusive data) — usado em KPIs, gráficos e ranking
df = apply_sidebar_filters(df_principais, filters)
# df_historico: todos os filtros EXCETO data — exclusivo para evolução temporal
_filters_sem_data = {**filters, "data_base": None}
df_historico = apply_sidebar_filters(df_principais, _filters_sem_data)

page_header(
    "",
    "Principais Gestoras",
    "Benchmark das Principais Gestoras — SOLIS · ANGÁ · POLIGONO · ARTESANAL · JIVE · VALORA · CATALISE · ORRAM · GUARDIAN · M8",
)

# ── Lista de gestoras disponíveis no df filtrado ───────────────────────────────
GESTORAS_ORDEM = ["SOLIS", "ANGÁ", "JIVE", "VALORA", "ARTESANAL",
                  "POLÍGONO", "CATALISE", "ORRAM", "GUARDIAN", "M8"]

gestoras_disponiveis = [
    g for g in GESTORAS_ORDEM
    if g in df["Nome_Gestora"].dropna().unique()
]
# Adiciona gestoras não previstas na ordem (segurança)
for g in sorted(df["Nome_Gestora"].dropna().unique()):
    if g not in gestoras_disponiveis:
        gestoras_disponiveis.append(g)

# ══════════════════════════════════════════════════════════════════════════════
# SELEÇÃO GLOBAL DA GESTORA (visível em todas as abas)
# ══════════════════════════════════════════════════════════════════════════════
if not gestoras_disponiveis:
    st.info("Nenhuma gestora disponível com os filtros aplicados.")
    st.stop()

gestora_sel = st.selectbox(
    "Gestora",
    options=gestoras_disponiveis,
    key="gestora_sel_global",
)

df_gest  = df[df["Nome_Gestora"] == gestora_sel]
df_resto = df[df["Nome_Gestora"] != gestora_sel]
#df_grupo = df  # todas as principais (para médias de referência)
df_grupo = df_resto.copy()
# ══════════════════════════════════════════════════════════════════════════════
# ABAS PRINCIPAIS
# ══════════════════════════════════════════════════════════════════════════════
tab_visao, tab_ranking, tab_evolucao, tab_prest_servico, tab_tabela_analitica = st.tabs(["Visao Geral", "Ranking Gestoras","Evolucao","Prestadores de Servicos","Tabela Analitica"])


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISAO GERAL
# ╚══════════════════════════════════════════════════════════════════════════════
with tab_visao:

    # ─── Helpers ─────────────────────────────────────────────────────────────
    def fmt_aum(val):
        if pd.isna(val) or val == 0:
            return "R$ 0"
        if val >= 1e9: return f"R$ {val/1e9:.2f} Bi"
        if val >= 1e6: return f"R$ {val/1e6:.2f} Mi"
        return f"R$ {val:,.0f}"

    def _inad_dc(df_):
        if df_.empty or "DC" not in df_.columns: return np.nan
        d = df_["DC"].sum()
        return float(min(df_["PDD"].sum() / d * 100, 100.0)) if d > 0 else np.nan

    def _sub_jr(df_):
        if not {"SB", "MZ", "SR"}.issubset(df_.columns): return np.nan
        denom = df_["SB"].sum() + df_["MZ"].sum() + df_["SR"].sum()
        return float(df_["SB"].sum() / denom * 100) if denom > 0 else np.nan

    def _sub_jrmz(df_):
        if not {"SB", "MZ", "SR"}.issubset(df_.columns): return np.nan
        denom = df_["SB"].sum() + df_["MZ"].sum() + df_["SR"].sum()
        return float((df_["SB"].sum() + df_["MZ"].sum()) / denom * 100) if denom > 0 else np.nan

    def _delta_str(v, ref, pct=True, reverse=False):
        """Delta texto: v vs ref. reverse=True → menor é melhor."""
        if pd.isna(v) or pd.isna(ref): return ""
        diff = v - ref
        sinal = "+" if diff >= 0 else ""
        fmt = fmt_pct if pct else fmt_aum
        dir_up = diff > 0 if not reverse else diff < 0
        return f"{sinal}{fmt_pct(diff)} vs média grupo"

    # ─── Calcular métricas ───────────────────────────────────────────────────
    # Gestora — médias ponderadas pelo PL_CVM
    g_pl       = df_gest["Valor_PL"].sum()   if "Valor_PL" in df_gest.columns else 0
    g_n        = len(df_gest)
    g_gest     = weighted_mean(df_gest, "taxa_gestao")        if "taxa_gestao"        in df_gest.columns else np.nan
    g_adm      = weighted_mean(df_gest, "taxa_administracao") if "taxa_administracao" in df_gest.columns else np.nan
    g_perf     = weighted_mean(df_gest, "taxa_performance")   if "taxa_performance"   in df_gest.columns else np.nan
    g_inad     = _inad_dc(df_gest)
    g_sub_jr   = _sub_jr(df_gest)
    g_sub_jrmz = _sub_jrmz(df_gest)
    g_cvnp     = df_gest["CVNP"].sum()  if "CVNP"  in df_gest.columns else 0
    g_aging    = df_gest["Aging"].sum() if "Aging" in df_gest.columns else 0

    # Médias do grupo externo a gestora selecionada (todas as principais) — ponderadas pelo PL_CVM
    r_pl       = df_grupo["Valor_PL"].sum()   if "Valor_PL" in df_grupo.columns else 0
    r_n        = len(df_grupo)
    r_gest     = weighted_mean(df_grupo, "taxa_gestao")        if "taxa_gestao"        in df_grupo.columns else np.nan
    r_adm      = weighted_mean(df_grupo, "taxa_administracao") if "taxa_administracao" in df_grupo.columns else np.nan
    r_perf     = weighted_mean(df_grupo, "taxa_performance")   if "taxa_performance"   in df_grupo.columns else np.nan
    r_inad     = _inad_dc(df_grupo)
    r_sub_jr   = _sub_jr(df_grupo)
    r_sub_jrmz = _sub_jrmz(df_grupo)

    # ─── KPIs — Gestora ──────────────────────────────────────────────────────
    st.markdown(
        f'<div class="section-label">{gestora_sel} — Indicadores Chave</div>',
        unsafe_allow_html=True,
    )

    def _delta_badge(v, ref, reverse=False):
        if pd.isna(v) or pd.isna(ref): return ""
        diff = v - ref
        sinal = "+" if diff >= 0 else ""
        melhor = diff < 0 if reverse else diff > 0
        cor = "#4ade80" if melhor else "#f87171"
        return f"<span style='color:{cor};font-size:0.72rem'>{sinal}{diff:+.2f}% vs grupo</span>"

    row1 = [
        kpi_card("PL Total",
                 fmt_aum(g_pl),
                 f"{g_n} fundos",
                 delta=f"Ex {gestora_sel}: {fmt_aum(r_pl)} · {r_n} fundos",
                 card_class="kpi-solis"),
        kpi_card("Taxa de Gestao Media",
                 fmt_pct(g_gest),
                 "% a.a.",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_gest)}",
                 delta_up=None,
                 card_class="kpi-solis"),
        kpi_card("Taxa de Administracao Media",
                 fmt_pct(g_adm),
                 "% a.a.",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_adm)}",
                 card_class="kpi-solis"),
        kpi_card("Taxa de Performance Media",
                 fmt_pct(g_perf),
                 "% a.a.",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_perf)}",
                 card_class="kpi-solis"),
    ]
    row2 = [
        kpi_card("Inadimplencia (PDD/DC)",
                 fmt_pct(g_inad),
                 "% Soma PDD / Soma DC",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_inad)}",
                 delta_up=None,
                 card_class="kpi-solis"),
        kpi_card("Subordinacao Jr.",
                 fmt_pct(g_sub_jr),
                 "% Soma Jr / Soma PL",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_sub_jr)}",
                 card_class="kpi-solis"),
        kpi_card("Subordinacao Jr + Mez",
                 fmt_pct(g_sub_jrmz),
                 "% Soma (Jr + Mez) / Soma PL",
                 delta=f"Ex {gestora_sel}: {fmt_pct(r_sub_jrmz)}",
                 card_class="kpi-solis"),
        kpi_card("CVNP Total / Aging Total",
                 fmt_aum(g_cvnp),
                 f"Aging: {fmt_aum(g_aging)}",
                 card_class="kpi-solis"),
    ]

    c1, c2, c3, c4 = st.columns(4)
    for col, card in zip([c1, c2, c3, c4], row1):
        with col:
            st.markdown(card, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    for col, card in zip([c5, c6, c7, c8], row2):
        with col:
            st.markdown(card, unsafe_allow_html=True)

    # ─── Comparativo visual — Medias do Grupo ────────────────────────────────
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-label">Media das Principais Gestoras (Referencia do Grupo)</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Valores calculados sobre todos os fundos das 10 principais gestoras. "
    )

    n_gest = df_grupo["Nome_Gestora"].nunique()
    media_pl_por_gestora = df_grupo.groupby("Nome_Gestora")["Valor_PL"].sum().mean() if "Valor_PL" in df_grupo.columns else 0
    media_n_por_gestora  = df_grupo.groupby("Nome_Gestora").size().mean()

    row_ref = [
        kpi_card("PL Medio por Gestora",
                 fmt_aum(media_pl_por_gestora),
                 f"{n_gest} gestoras no grupo",
                 card_class="kpi-market"),
        kpi_card("Taxa de Gestao — Media",
                 fmt_pct(r_gest),
                 "% a.a. · Grupo",
                 card_class="kpi-market"),
        kpi_card("Inadimplencia — Media (PDD/DC)",
                 fmt_pct(r_inad),
                 "Grupo",
                 card_class="kpi-market"),
        kpi_card("Subordinacao Jr. — Media",
                 fmt_pct(r_sub_jr),
                 "Grupo",
                 card_class="kpi-market"),
    ]

    cr1, cr2, cr3, cr4 = st.columns(4)
    for col, card in zip([cr1, cr2, cr3, cr4], row_ref):
        with col:
            st.markdown(card, unsafe_allow_html=True)

    st.markdown("---")

    # ─── Graficos por Foco de Atuacao ────────────────────────────────────────
    st.markdown(
        f'<div class="section-label">{gestora_sel} vs Demais Gestoras — por Foco de Atuacao</div>',
        unsafe_allow_html=True,
    )

    VARIAVEIS = {
        "Taxas":        "taxas",
        "Inadimplencia (PDD/DC)": "inad_dc",
        "Inadimplencia (PDD/PL)": "inad_pl",
        "Subordinacao Jr.":       "sub_jr",
        "Subordinacao Jr + Mez":  "sub_jrmz",
        "CVNP":                   "cvnp",
        "Aging":                  "aging",
    }

    var_label = st.selectbox(
        "Variavel para comparar com o grupo",
        options=list(VARIAVEIS.keys()),
        key="visao_var_sel",
    )
    var_key = VARIAVEIS[var_label]

    # ── helper de paleta degradê ──────────────────────────────────────────────
    def _make_grad(n, alpha=0.90):
        hex_list = pc.sample_colorscale(
            [[0, PALETTE["blue"]], [0.5, PALETTE["orange"]], [1, PALETTE["amber"]]],
            [i / max(n - 1, 1) for i in range(n)],
        )
        out = []
        for h in hex_list:
            if h.startswith("#"):
                r_, g_, b_ = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
            else:
                parts = h.replace("rgb(", "").replace(")", "").split(",")
                r_, g_, b_ = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
            out.append(f"rgba({r_},{g_},{b_},{alpha})")
        return out

    # ── Função genérica de barras horizontais duplas (gestora vs resto) ───────
    def _bar_chart_foco(y_vals, x_gest, x_resto, label_gest, label_resto,
                        x_title, mean_gest=None, mean_resto=None, chart_key=""):
        n_cats  = len(y_vals)
        chart_h = max(500, n_cats * 52 + 120)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=y_vals,
            x=x_resto,
            name=label_resto,
            orientation="h",
            marker=dict(color="rgba(137,155,183,0.7)", line=dict(color="#899BB7", width=1)),
            hovertemplate=f"<b>%{{y}}</b><br>{label_resto}: %{{x:.2f}}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=y_vals,
            x=x_gest,
            name=label_gest,
            orientation="h",
            marker=dict(color="rgba(255,195,106,0.85)", line=dict(color="#F89B66", width=1.5)),
            hovertemplate=f"<b>%{{y}}</b><br>{label_gest}: %{{x:.2f}}<extra></extra>",
        ))
        if mean_resto is not None and pd.notna(mean_resto):
            fig.add_vline(x=mean_resto, line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2))
            fig.add_annotation(
                x=mean_resto, y=1.01, yref="paper",
                text=f"Med. Grupo: <b>{mean_resto:.2f}</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(size=10, color="#FFFFFF"),
                bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
            )
        if mean_gest is not None and pd.notna(mean_gest):
            fig.add_vline(x=mean_gest, line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2))
            fig.add_annotation(
                x=mean_gest, y=0.86, yref="paper",
                text=f"Med. {label_gest}: <b>{mean_gest:.2f}</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(size=10, color="#FFFFFF"),
                bgcolor="rgba(59,130,246,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
            )
        _layout = _base_layout("", chart_h)
        for _k in ("margin", "font", "legend"):
            _layout.pop(_k, None)
        fig.update_layout(
            **_layout,
            barmode="group", bargap=0.28, bargroupgap=0.06,
            margin=dict(l=240, r=40, t=20, b=60),
            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        )
        fig.update_xaxes(title_text=x_title, title_font=dict(size=12), tickfont=dict(size=11))
        fig.update_yaxes(tickfont=dict(size=11), automargin=True)
        return fig

    # ── TAXAS ─────────────────────────────────────────────────────────────────
    if var_key == "taxas":
        taxa_cols_avail = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 3]
        if not taxa_cols_avail:
            st.info("Nenhuma taxa disponivel com os filtros aplicados.")
        else:
            col_sel = st.selectbox(
                "Tipo de Taxa",
                taxa_cols_avail,
                format_func=lambda c: TAXA_LABELS.get(c, c),
                key="visao_taxa_tipo",
            )
            taxa_label = TAXA_LABELS.get(col_sel, col_sel)

            # Médias ponderadas pelo PL_CVM por foco de atuação
            gest_means  = weighted_mean_by_group(df_gest,  "foco_atuacao", col_sel).to_dict()
            resto_means = weighted_mean_by_group(df_resto, "foco_atuacao", col_sel).to_dict()
            all_focos   = sorted(set(list(gest_means.keys()) + list(resto_means.keys())))
            focos_sorted = sorted(
                all_focos,
                key=lambda f: resto_means.get(f, np.nan) if pd.notna(resto_means.get(f, np.nan)) else -999,
            )

            x_gest  = [gest_means.get(f, np.nan)  for f in focos_sorted]
            x_resto = [resto_means.get(f, np.nan) for f in focos_sorted]

            mgest  = weighted_mean(df_gest,  col_sel)
            mresto = weighted_mean(df_resto, col_sel)

            st.markdown(f"**{taxa_label} | por Segmento | {gestora_sel} vs Demais Gestoras**")
            fig = _bar_chart_foco(
                focos_sorted, x_gest, x_resto,
                gestora_sel, "Demais Gestoras",
                "% a.a.", mgest, mresto, chart_key="taxa",
            )
            st.plotly_chart(fig, use_container_width=True, key="foco_taxa_gest")

    # ── INADIMPLENCIA PDD/DC ──────────────────────────────────────────────────
    elif var_key == "inad_dc":
        if "PDD" not in df.columns or "DC" not in df.columns:
            st.info("Dados de inadimplencia nao disponiveis.")
        else:
            def _inad_dc_foco(df_):
                if df_.empty: return {}
                agg = df_.groupby("foco_atuacao")[["PDD", "DC"]].sum()
                vals = np.where(agg["DC"] > 0, (agg["PDD"] / agg["DC"] * 100).clip(upper=100), np.nan)
                return dict(zip(agg.index, vals))

            gest_inad  = _inad_dc_foco(df_gest)
            resto_inad = _inad_dc_foco(df_resto)
            all_focos  = sorted(set(list(gest_inad.keys()) + list(resto_inad.keys())))
            focos_s    = sorted(all_focos, key=lambda f: resto_inad.get(f, -999) if pd.notna(resto_inad.get(f, np.nan)) else -999)

            x_gest  = [gest_inad.get(f, np.nan)  for f in focos_s]
            x_resto = [resto_inad.get(f, np.nan) for f in focos_s]

            mgest  = _inad_dc(df_gest)
            mresto = _inad_dc(df_resto)

            st.markdown(f"**Inadimplencia (PDD/DC) | por Segmento | {gestora_sel} vs Demais Gestoras**")
            fig = _bar_chart_foco(
                focos_s, x_gest, x_resto,
                gestora_sel, "Demais Gestoras",
                "% (PDD/DC)", mgest, mresto, chart_key="inad_dc",
            )
            st.plotly_chart(fig, use_container_width=True, key="foco_inad_dc_gest")

    # ── INADIMPLENCIA PDD/PL ──────────────────────────────────────────────────
    elif var_key == "inad_pl":
        if "PDD" not in df.columns or "PL_CVM" not in df.columns:
            st.info("Dados de inadimplencia PDD/PL nao disponiveis.")
        else:
            def _inad_pl_foco(df_):
                if df_.empty: return {}
                agg = df_.groupby("foco_atuacao")[["PDD", "PL_CVM"]].sum()
                vals = np.where(agg["PL_CVM"] > 0, (agg["PDD"] / agg["PL_CVM"] * 100).clip(upper=100), np.nan)
                return dict(zip(agg.index, vals))

            gest_inad  = _inad_pl_foco(df_gest)
            resto_inad = _inad_pl_foco(df_resto)
            all_focos  = sorted(set(list(gest_inad.keys()) + list(resto_inad.keys())))
            focos_s    = sorted(all_focos, key=lambda f: resto_inad.get(f, -999) if pd.notna(resto_inad.get(f, np.nan)) else -999)

            x_gest  = [gest_inad.get(f, np.nan)  for f in focos_s]
            x_resto = [resto_inad.get(f, np.nan) for f in focos_s]

            def _inad_pl_total(df_):
                if df_.empty or "PL_CVM" not in df_.columns: return np.nan
                d = df_["PL_CVM"].sum()
                return float(min(df_["PDD"].sum() / d * 100, 100.0)) if d > 0 else np.nan

            st.markdown(f"**Inadimplencia (PDD/PL) | por Segmento | {gestora_sel} vs Demais Gestoras**")
            fig = _bar_chart_foco(
                focos_s, x_gest, x_resto,
                gestora_sel, "Demais Gestoras",
                "% (PDD/PL)", _inad_pl_total(df_gest), _inad_pl_total(df_resto),
                chart_key="inad_pl",
            )
            st.plotly_chart(fig, use_container_width=True, key="foco_inad_pl_gest")

    # ── SUBORDINACAO JR ───────────────────────────────────────────────────────
    elif var_key == "sub_jr":
        if not {"SB", "MZ", "SR"}.issubset(df.columns):
            st.info("Dados de subordinacao nao disponiveis.")
        else:
            def _sub_jr_foco(df_):
                if df_.empty: return {}
                agg   = df_.groupby("foco_atuacao")[["SB", "MZ", "SR"]].sum()
                denom = agg["SB"] + agg["MZ"] + agg["SR"]
                vals  = np.where(denom > 0, agg["SB"] / denom * 100, np.nan)
                return dict(zip(agg.index, vals))

            gest_sub  = _sub_jr_foco(df_gest)
            resto_sub = _sub_jr_foco(df_resto)
            all_focos = sorted(set(list(gest_sub.keys()) + list(resto_sub.keys())))
            focos_s   = sorted(all_focos, key=lambda f: resto_sub.get(f, -999) if pd.notna(resto_sub.get(f, np.nan)) else -999)

            x_gest  = [gest_sub.get(f, np.nan)  for f in focos_s]
            x_resto = [resto_sub.get(f, np.nan) for f in focos_s]

            st.markdown(f"**Subordinacao Jr. | por Segmento | {gestora_sel} vs Demais Gestoras**")
            fig = _bar_chart_foco(
                focos_s, x_gest, x_resto,
                gestora_sel, "Demais Gestoras",
                "% (Sub Jr)", _sub_jr(df_gest), _sub_jr(df_resto),
                chart_key="sub_jr",
            )
            st.plotly_chart(fig, use_container_width=True, key="foco_sub_jr_gest")

    # ── SUBORDINACAO JR + MEZ ─────────────────────────────────────────────────
    elif var_key == "sub_jrmz":
        if not {"SB", "MZ", "SR"}.issubset(df.columns):
            st.info("Dados de subordinacao nao disponiveis.")
        else:
            def _sub_jrmz_foco(df_):
                if df_.empty: return {}
                agg   = df_.groupby("foco_atuacao")[["SB", "MZ", "SR"]].sum()
                denom = agg["SB"] + agg["MZ"] + agg["SR"]
                vals  = np.where(denom > 0, (agg["SB"] + agg["MZ"]) / denom * 100, np.nan)
                return dict(zip(agg.index, vals))

            gest_sub  = _sub_jrmz_foco(df_gest)
            resto_sub = _sub_jrmz_foco(df_resto)
            all_focos = sorted(set(list(gest_sub.keys()) + list(resto_sub.keys())))
            focos_s   = sorted(all_focos, key=lambda f: resto_sub.get(f, -999) if pd.notna(resto_sub.get(f, np.nan)) else -999)

            x_gest  = [gest_sub.get(f, np.nan)  for f in focos_s]
            x_resto = [resto_sub.get(f, np.nan) for f in focos_s]

            st.markdown(f"**Subordinacao Jr + Mez | por Segmento | {gestora_sel} vs Demais Gestoras**")
            fig = _bar_chart_foco(
                focos_s, x_gest, x_resto,
                gestora_sel, "Demais Gestoras",
                "% (Sub Jr+Mez)", _sub_jrmz(df_gest), _sub_jrmz(df_resto),
                chart_key="sub_jrmz",
            )
            st.plotly_chart(fig, use_container_width=True, key="foco_sub_jrmz_gest")

    # ── CVNP ──────────────────────────────────────────────────────────────────
    elif var_key == "cvnp":
        cvnp_presentes = [c for c in CVNP_COLS if c in df.columns]
        if not cvnp_presentes or "CVNP" not in df.columns:
            st.info("Dados de CVNP nao disponiveis.")
        else:
            def _agg_cvnp_foco(df_g):
                if df_g.empty: return pd.DataFrame()
                grp = (
                    df_g.groupby("foco_atuacao")[["CVNP"] + cvnp_presentes]
                    .sum().reset_index()
                )
                grp = grp[grp["CVNP"] > 0].copy()
                for c in cvnp_presentes:
                    grp[f"{c}_pct"] = (grp[c] / grp["CVNP"] * 100).fillna(0)
                return grp.sort_values("CVNP", ascending=False)

            agg_gest  = _agg_cvnp_foco(df_gest)
            agg_resto = _agg_cvnp_foco(df_resto)

            segs_ref   = agg_resto["foco_atuacao"].tolist() if not agg_resto.empty else []
            segs_gest  = agg_gest["foco_atuacao"].tolist()  if not agg_gest.empty  else []
            for s in segs_gest:
                if s not in segs_ref:
                    segs_ref.append(s)

            if not segs_ref:
                st.info("Nenhum dado de CVNP disponivel.")
            else:
                _cores = _make_grad(len(cvnp_presentes), alpha=0.90)
                _col_idx = {c: i for i, c in enumerate(cvnp_presentes)}

                grupos_ativos = [
                    ("Demais Gestoras", agg_resto),
                    (gestora_sel,       agg_gest),
                ]
                y_l1, y_l2 = [], []
                for seg in segs_ref:
                    for gname, _ in grupos_ativos:
                        y_l1.append(seg)
                        y_l2.append(gname)

                def _pv(agg_g, seg, col):
                    if agg_g is None or agg_g.empty: return 0.0
                    row = agg_g[agg_g["foco_atuacao"] == seg]
                    return float(row[f"{col}_pct"].iloc[0]) if not row.empty else 0.0

                fig_cvnp = go.Figure()
                for col in cvnp_presentes:
                    label  = CVNP_LABELS.get(col, col)
                    cidx   = _col_idx[col]
                    cor    = _cores[cidx] if cidx < len(_cores) else _cores[-1]
                    first_group = grupos_ativos[0][0]
                    for gname, agg_g in grupos_ativos:
                        x_vals  = [_pv(agg_g, seg, col) for seg in segs_ref]
                        y_trace = [[seg for seg in segs_ref], [gname] * len(segs_ref)]
                        txt     = [f"{v:.0f}%" if v >= 8.0 else "" for v in x_vals]
                        txt_col = "#FFFFFF" if cidx >= 2 else "#1e1e2e"
                        fig_cvnp.add_trace(go.Bar(
                            name=label, y=y_trace, x=x_vals, orientation="h",
                            text=txt, textposition="inside", insidetextanchor="middle",
                            textfont=dict(size=8, color=txt_col, family="Inter"),
                            marker=dict(color=cor, line=dict(width=0.4, color="rgba(255,255,255,0.08)")),
                            legendgroup=label, showlegend=(gname == first_group),
                            hovertemplate=(f"<b>{label}</b><br><b>%{{y[0]}}</b> — {gname}<br>%{{x:.1f}}% do CVNP<extra></extra>"),
                        ))

                n_segs  = len(segs_ref)
                chart_h = max(500, n_segs * 2 * 26 + 180)
                fig_cvnp.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PALETTE["bg"],
                    font=dict(family="Inter, -apple-system, sans-serif", size=12, color=PALETTE["text"]),
                    height=chart_h, barmode="stack", bargap=0.14, bargroupgap=0.06,
                    margin=dict(l=20, r=20, t=90, b=30),
                    legend=dict(
                        title=dict(text="Faixa de atraso", font=dict(size=10, color=PALETTE["text"])),
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(148,163,184,0.18)", borderwidth=1,
                        font=dict(size=11, color=PALETTE["text_hi"]),
                        orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=0.5,
                        itemwidth=90, tracegroupgap=0,
                    ),
                    xaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%", range=[0, 105],
                               title=dict(text="% do CVNP Total", font=dict(size=10, color=PALETTE["text"])),
                               tickfont=dict(size=9, color=PALETTE["text"])),
                    yaxis=dict(gridcolor="rgba(148,163,184,0.06)", tickfont=dict(size=10, color=PALETTE["text_hi"]), automargin=True),
                )
                st.markdown(f"**CVNP por Segmento | {gestora_sel} vs Demais Gestoras**")
                st.plotly_chart(fig_cvnp, use_container_width=True, key=f"foco_cvnp_gest_{len(segs_ref)}")

    # ── AGING ─────────────────────────────────────────────────────────────────
    elif var_key == "aging":
        aging_presentes = [c for c in AGING_COLS if c in df.columns]
        if not aging_presentes or "Aging" not in df.columns:
            st.info("Dados de Aging nao disponiveis.")
        else:
            def _agg_aging_foco(df_g):
                if df_g.empty: return pd.DataFrame()
                grp = (
                    df_g.groupby("foco_atuacao")[["Aging"] + aging_presentes]
                    .sum().reset_index()
                )
                grp = grp[grp["Aging"] > 0].copy()
                for c in aging_presentes:
                    grp[f"{c}_pct"] = (grp[c] / grp["Aging"] * 100).fillna(0)
                return grp.sort_values("Aging", ascending=False)

            agg_gest  = _agg_aging_foco(df_gest)
            agg_resto = _agg_aging_foco(df_resto)

            segs_ref  = agg_resto["foco_atuacao"].tolist() if not agg_resto.empty else []
            segs_gest = agg_gest["foco_atuacao"].tolist()  if not agg_gest.empty  else []
            for s in segs_gest:
                if s not in segs_ref:
                    segs_ref.append(s)

            if not segs_ref:
                st.info("Nenhum dado de Aging disponivel.")
            else:
                _cores_ag = _make_grad(len(aging_presentes), alpha=0.90)
                _col_idx_ag = {c: i for i, c in enumerate(aging_presentes)}

                grupos_ativos_ag = [
                    ("Demais Gestoras", agg_resto),
                    (gestora_sel,       agg_gest),
                ]
                y_l1, y_l2 = [], []
                for seg in segs_ref:
                    for gname, _ in grupos_ativos_ag:
                        y_l1.append(seg)
                        y_l2.append(gname)

                def _pv_ag(agg_g, seg, col):
                    if agg_g is None or agg_g.empty: return 0.0
                    row = agg_g[agg_g["foco_atuacao"] == seg]
                    return float(row[f"{col}_pct"].iloc[0]) if not row.empty else 0.0

                fig_ag = go.Figure()
                first_group = grupos_ativos_ag[0][0]
                for col in aging_presentes:
                    label = AGING_LABELS.get(col, col)
                    cidx  = _col_idx_ag[col]
                    cor   = _cores_ag[cidx] if cidx < len(_cores_ag) else _cores_ag[-1]
                    for gname, agg_g in grupos_ativos_ag:
                        x_vals  = [_pv_ag(agg_g, seg, col) for seg in segs_ref]
                        y_trace = [[seg for seg in segs_ref], [gname] * len(segs_ref)]
                        txt     = [f"{v:.0f}%" if v >= 8.0 else "" for v in x_vals]
                        txt_col = "#FFFFFF" if cidx >= 2 else "#1e1e2e"
                        fig_ag.add_trace(go.Bar(
                            name=label, y=y_trace, x=x_vals, orientation="h",
                            text=txt, textposition="inside", insidetextanchor="middle",
                            textfont=dict(size=8, color=txt_col, family="Inter"),
                            marker=dict(color=cor, line=dict(width=0.4, color="rgba(255,255,255,0.08)")),
                            legendgroup=label, showlegend=(gname == first_group),
                            hovertemplate=(f"<b>{label}</b><br><b>%{{y[0]}}</b> — {gname}<br>%{{x:.1f}}% do Aging<extra></extra>"),
                        ))

                n_segs_ag = len(segs_ref)
                chart_h_ag = max(500, n_segs_ag * 2 * 26 + 180)
                fig_ag.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PALETTE["bg"],
                    font=dict(family="Inter, -apple-system, sans-serif", size=12, color=PALETTE["text"]),
                    height=chart_h_ag, barmode="stack", bargap=0.14, bargroupgap=0.06,
                    margin=dict(l=20, r=20, t=90, b=30),
                    legend=dict(
                        title=dict(text="Faixa de prazo", font=dict(size=10, color=PALETTE["text"])),
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(148,163,184,0.18)", borderwidth=1,
                        font=dict(size=11, color=PALETTE["text_hi"]),
                        orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=0.5,
                        itemwidth=90, tracegroupgap=0,
                    ),
                    xaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%", range=[0, 105],
                               title=dict(text="% do Aging Total", font=dict(size=10, color=PALETTE["text"])),
                               tickfont=dict(size=9, color=PALETTE["text"])),
                    yaxis=dict(gridcolor="rgba(148,163,184,0.06)", tickfont=dict(size=10, color=PALETTE["text_hi"]), automargin=True),
                )
                st.markdown(f"**Aging por Segmento | {gestora_sel} vs Demais Gestoras**")
                st.plotly_chart(fig_ag, use_container_width=True, key=f"foco_aging_gest_{len(segs_ref)}")

# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RANKING GESTORAS
# ╚══════════════════════════════════════════════════════════════════════════════
with tab_ranking:

    st.markdown(
        '<div class="section-label">Ranking das Principais Gestoras por Indicador</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Comparativo posicional entre as principais gestoras. "
    )

    if df.empty or "Nome_Gestora" not in df.columns:
        st.info("Nenhum dado disponivel com os filtros aplicados.")
    else:
        subtab_taxa, subtab_inad, subtab_sub, subtab_cvnp, subtab_aging, subtab_remun = st.tabs([
            "Taxas", "Inadimplencia", "Subordinacao", "CVNP", "Aging", "Remuneracao Esperada"
        ])

        # ── Helper: tabela de ranking com highlight ───────────────────────────
        def _render_ranking(df_rank, col_valor, label_col, fmt_func,
                            ascendente=True, titulo=""):
            """Renderiza tabela de ranking ordenada."""
            df_rank = df_rank.sort_values(col_valor, ascending=ascendente, na_position="last").reset_index(drop=True)
            df_rank.index = df_rank.index + 1  # posicao começa em 1
            df_rank.index.name = "Pos."

            if titulo:
                st.markdown(f"**{titulo}**")

            # Formatar para exibição
            df_display = df_rank.copy()
            df_display[col_valor] = df_display[col_valor].apply(lambda x: fmt_func(x) if pd.notna(x) else "—")

            st.dataframe(
                df_display,
                use_container_width=True,
                column_config={
                    col_valor: st.column_config.TextColumn(label=label_col, width="medium"),
                    "N Fundos": st.column_config.NumberColumn(width="small"),
                },
            )

        # ── Agregar por gestora ───────────────────────────────────────────────
        gestoras_vals = df["Nome_Gestora"].dropna().unique()

        def _build_base_ranking():
            rows = []
            for g in gestoras_vals:
                dg = df[df["Nome_Gestora"] == g]
                rows.append({
                    "Gestora":  g,
                    "N Fundos": len(dg),
                    "PL Total": dg["Valor_PL"].sum() if "Valor_PL" in dg.columns else 0,
                })
            return pd.DataFrame(rows)

        df_base = _build_base_ranking()

        # ── SUB-TAB: TAXAS ───────────────────────────────────────────────────
        with subtab_taxa:
            taxa_opts = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 3]
            if not taxa_opts:
                st.info("Nenhuma taxa disponivel.")
            else:
                taxa_rank_sel = st.selectbox(
                    "Tipo de Taxa",
                    taxa_opts,
                    format_func=lambda c: TAXA_LABELS.get(c, c),
                    key="ranking_taxa_sel",
                )
                taxa_rank_label = TAXA_LABELS.get(taxa_rank_sel, taxa_rank_sel)

                rows_t = []
                for g in gestoras_vals:
                    dg = df[df["Nome_Gestora"] == g]
                    # Média ponderada pelo PL_CVM
                    val = weighted_mean(dg, taxa_rank_sel) if taxa_rank_sel in dg.columns else np.nan
                    med = dg[taxa_rank_sel].median() if taxa_rank_sel in dg.columns else np.nan
                    n_c = dg[taxa_rank_sel].notna().sum() if taxa_rank_sel in dg.columns else 0
                    rows_t.append({
                        "Gestora":       g,
                        "N Fundos":      len(dg),
                        "Fundos c/ Taxa": int(n_c),
                        "Media Pond. PL (% a.a.)": val,
                        "Mediana (% a.a.)": med,
                    })

                df_rank_t = pd.DataFrame(rows_t)
                df_rank_t = df_rank_t.sort_values("Media Pond. PL (% a.a.)", ascending=True, na_position="last").reset_index(drop=True)
                df_rank_t.index = df_rank_t.index + 1
                df_rank_t.index.name = "Pos."

                st.markdown(f"**Ranking por {taxa_rank_label} — Média Ponderada por PL (ordem crescente)**")

                # Grafico de barras horizontais do ranking
                df_plot_t = df_rank_t.dropna(subset=["Media Pond. PL (% a.a.)"]).sort_values("Media Pond. PL (% a.a.)")
                n_bars = len(df_plot_t)
                cores_rank = _make_grad(max(n_bars, 2), alpha=0.85)

                fig_rank_t = go.Figure(go.Bar(
                    y=df_plot_t["Gestora"],
                    x=df_plot_t["Media Pond. PL (% a.a.)"],
                    orientation="h",
                    marker=dict(
                        color=cores_rank[:n_bars],
                        line=dict(color="rgba(255,255,255,0.1)", width=0.5),
                    ),
                    text=[fmt_pct(v) for v in df_plot_t["Media Pond. PL (% a.a.)"]],
                    textposition="outside",
                    textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>Media Pond. PL: %{x:.3f}% a.a.<extra></extra>",
                ))
                # Média ponderada pelo PL_CVM de todo o grupo como referência
                mkt_media_t = weighted_mean(df, taxa_rank_sel) if taxa_rank_sel in df.columns else np.nan
                if pd.notna(mkt_media_t):
                    fig_rank_t.add_vline(x=mkt_media_t, line=dict(color="rgba(217,119,6,0.9)", dash="dot", width=2))
                    fig_rank_t.add_annotation(
                        x=mkt_media_t, y=1.01, yref="paper",
                        text=f"Media Grupo: <b>{mkt_media_t:.3f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
                    )
                _lt = _base_layout("", max(400, n_bars * 42 + 80))
                for _k in ("margin", "font", "legend"):
                    _lt.pop(_k, None)
                fig_rank_t.update_layout(
                    **_lt,
                    bargap=0.32,
                    margin=dict(l=120, r=80, t=30, b=50),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                )
                fig_rank_t.update_xaxes(title_text="% a.a.", tickfont=dict(size=11))
                fig_rank_t.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_rank_t, use_container_width=True, key="rank_taxa_bar")

                # Tabela detalhada
                st.dataframe(
                    df_rank_t,
                    use_container_width=True,
                    column_config={
                        "Media Pond. PL (% a.a.)": st.column_config.NumberColumn(format="%.3f%%"),
                        "Mediana (% a.a.)":         st.column_config.NumberColumn(format="%.3f%%"),
                        "N Fundos":                 st.column_config.NumberColumn(width="small"),
                        "Fundos c/ Taxa":            st.column_config.NumberColumn(width="small"),
                    },
                )

        # ── SUB-TAB: INADIMPLENCIA ───────────────────────────────────────────
        with subtab_inad:
            subtab_inad_dc, subtab_inad_pl = st.tabs(["PDD / DC", "PDD / PL"])

            with subtab_inad_dc:
                rows_i = []
                for g in gestoras_vals:
                    dg  = df[df["Nome_Gestora"] == g]
                    val = _inad_dc(dg)
                    rows_i.append({"Gestora": g, "N Fundos": len(dg), "Inadimplencia PDD/DC (%)": val})
                df_rank_i = pd.DataFrame(rows_i).sort_values("Inadimplencia PDD/DC (%)", ascending=True, na_position="last").reset_index(drop=True)
                df_rank_i.index = df_rank_i.index + 1
                df_rank_i.index.name = "Pos."

                st.markdown("**Ranking por Inadimplencia (PDD/DC)**")

                df_plot_i = pd.DataFrame(rows_i).dropna(subset=["Inadimplencia PDD/DC (%)"]).sort_values("Inadimplencia PDD/DC (%)")
                n_bi = len(df_plot_i)
                cores_i = _make_grad(max(n_bi, 2), alpha=0.85)
                fig_rank_i = go.Figure(go.Bar(
                    y=df_plot_i["Gestora"], x=df_plot_i["Inadimplencia PDD/DC (%)"],
                    orientation="h",
                    marker=dict(color=cores_i[:n_bi], line=dict(color="rgba(255,255,255,0.1)", width=0.5)),
                    text=[fmt_pct(v) for v in df_plot_i["Inadimplencia PDD/DC (%)"]],
                    textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>Inadimplencia: %{x:.2f}%<extra></extra>",
                ))
                media_inad_grupo = _inad_dc(df)
                if pd.notna(media_inad_grupo):
                    fig_rank_i.add_vline(x=media_inad_grupo, line=dict(color="rgba(217,119,6,0.9)", dash="dot", width=2))
                    fig_rank_i.add_annotation(
                        x=media_inad_grupo, y=1.01, yref="paper",
                        text=f"Media Grupo: <b>{media_inad_grupo:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
                    )
                _li = _base_layout("", max(400, n_bi * 42 + 80))
                for _k in ("margin", "font", "legend"): _li.pop(_k, None)
                fig_rank_i.update_layout(**_li, bargap=0.32, margin=dict(l=120, r=80, t=30, b=50),
                                         font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
                fig_rank_i.update_xaxes(title_text="% (PDD/DC)", tickfont=dict(size=11), ticksuffix="%")
                fig_rank_i.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_rank_i, use_container_width=True, key="rank_inad_dc_bar")

                st.dataframe(df_rank_i, use_container_width=True,
                             column_config={"Inadimplencia PDD/DC (%)": st.column_config.NumberColumn(format="%.2f%%"),
                                            "N Fundos": st.column_config.NumberColumn(width="small")})

            with subtab_inad_pl:
                def _inad_pl_total(df_):
                    if df_.empty or "PL_CVM" not in df_.columns: return np.nan
                    d = df_["PL_CVM"].sum()
                    return float(min(df_["PDD"].sum() / d * 100, 100.0)) if d > 0 else np.nan

                rows_ipl = []
                for g in gestoras_vals:
                    dg  = df[df["Nome_Gestora"] == g]
                    val = _inad_pl_total(dg)
                    rows_ipl.append({"Gestora": g, "N Fundos": len(dg), "Inadimplencia PDD/PL (%)": val})
                df_rank_ipl = pd.DataFrame(rows_ipl).sort_values("Inadimplencia PDD/PL (%)", ascending=True, na_position="last").reset_index(drop=True)
                df_rank_ipl.index = df_rank_ipl.index + 1
                df_rank_ipl.index.name = "Pos."

                st.markdown("**Ranking por Inadimplencia (PDD/PL) — Ponderada por Patrimonio (ordem crescente)**")

                df_plot_ipl = pd.DataFrame(rows_ipl).dropna(subset=["Inadimplencia PDD/PL (%)"]).sort_values("Inadimplencia PDD/PL (%)")
                n_bipl = len(df_plot_ipl)
                cores_ipl = _make_grad(max(n_bipl, 2), alpha=0.85)
                fig_rank_ipl = go.Figure(go.Bar(
                    y=df_plot_ipl["Gestora"], x=df_plot_ipl["Inadimplencia PDD/PL (%)"],
                    orientation="h",
                    marker=dict(color=cores_ipl[:n_bipl], line=dict(color="rgba(255,255,255,0.1)", width=0.5)),
                    text=[fmt_pct(v) for v in df_plot_ipl["Inadimplencia PDD/PL (%)"]],
                    textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>Inadimplencia: %{x:.2f}%<extra></extra>",
                ))
                media_inad_pl_grupo = _inad_pl_total(df)
                if pd.notna(media_inad_pl_grupo):
                    fig_rank_ipl.add_vline(x=media_inad_pl_grupo, line=dict(color="rgba(217,119,6,0.9)", dash="dot", width=2))
                    fig_rank_ipl.add_annotation(
                        x=media_inad_pl_grupo, y=1.01, yref="paper",
                        text=f"Media Grupo: <b>{media_inad_pl_grupo:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
                    )
                _lipl = _base_layout("", max(400, n_bipl * 42 + 80))
                for _k in ("margin", "font", "legend"): _lipl.pop(_k, None)
                fig_rank_ipl.update_layout(**_lipl, bargap=0.32, margin=dict(l=120, r=80, t=30, b=50),
                                           font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
                fig_rank_ipl.update_xaxes(title_text="% (PDD/PL)", tickfont=dict(size=11), ticksuffix="%")
                fig_rank_ipl.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_rank_ipl, use_container_width=True, key="rank_inad_pl_bar")

                st.dataframe(df_rank_ipl, use_container_width=True,
                             column_config={"Inadimplencia PDD/PL (%)": st.column_config.NumberColumn(format="%.2f%%"),
                                            "N Fundos": st.column_config.NumberColumn(width="small")})

        # ── SUB-TAB: SUBORDINACAO ────────────────────────────────────────────
        with subtab_sub:
            subtab_sub_jr, subtab_sub_jrmz = st.tabs(["Subordinacao Jr.", "Subordinacao Jr + Mez"])

            for sub_tab, sub_func, col_name, chart_key_s, ylabel_s in [
                (subtab_sub_jr,   _sub_jr,   "Subordinacao Jr. (%)",   "rank_sub_jr",   "% (Sub Jr)"),
                (subtab_sub_jrmz, _sub_jrmz, "Subordinacao Jr+Mez (%)", "rank_sub_jrmz", "% (Sub Jr+Mez)"),
            ]:
                with sub_tab:
                    rows_s = []
                    for g in gestoras_vals:
                        dg  = df[df["Nome_Gestora"] == g]
                        val = sub_func(dg)
                        rows_s.append({"Gestora": g, "N Fundos": len(dg), col_name: val})
                    df_rank_s = pd.DataFrame(rows_s).sort_values(col_name, ascending=False, na_position="last").reset_index(drop=True)
                    df_rank_s.index = df_rank_s.index + 1
                    df_rank_s.index.name = "Pos."

                    st.markdown(f"**Ranking por {col_name.replace('(%)', '').strip()}**")

                    df_plot_s = pd.DataFrame(rows_s).dropna(subset=[col_name]).sort_values(col_name)
                    n_bs = len(df_plot_s)
                    cores_s = _make_grad(max(n_bs, 2), alpha=0.85)
                    fig_rank_s = go.Figure(go.Bar(
                        y=df_plot_s["Gestora"], x=df_plot_s[col_name],
                        orientation="h",
                        marker=dict(color=cores_s[:n_bs], line=dict(color="rgba(255,255,255,0.1)", width=0.5)),
                        text=[fmt_pct(v) for v in df_plot_s[col_name]],
                        textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                        hovertemplate=f"<b>%{{y}}</b><br>{col_name}: %{{x:.2f}}%<extra></extra>",
                    ))
                    media_sub_grupo = sub_func(df)
                    if pd.notna(media_sub_grupo):
                        fig_rank_s.add_vline(x=media_sub_grupo, line=dict(color="rgba(217,119,6,0.9)", dash="dot", width=2))
                        fig_rank_s.add_annotation(
                            x=media_sub_grupo, y=1.01, yref="paper",
                            text=f"Media Grupo: <b>{media_sub_grupo:.2f}%</b>",
                            showarrow=False, xanchor="left", xshift=8,
                            font=dict(size=10, color="#FFFFFF"),
                            bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)",
                        )
                    _ls = _base_layout("", max(400, n_bs * 42 + 80))
                    for _k in ("margin", "font", "legend"): _ls.pop(_k, None)
                    fig_rank_s.update_layout(**_ls, bargap=0.32, margin=dict(l=120, r=80, t=30, b=50),
                                            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
                    fig_rank_s.update_xaxes(title_text=ylabel_s, tickfont=dict(size=11), ticksuffix="%")
                    fig_rank_s.update_yaxes(tickfont=dict(size=12), automargin=True)
                    st.plotly_chart(fig_rank_s, use_container_width=True, key=f"{chart_key_s}_bar")

                    st.dataframe(df_rank_s, use_container_width=True,
                                 column_config={col_name: st.column_config.NumberColumn(format="%.2f%%"),
                                                "N Fundos": st.column_config.NumberColumn(width="small")})

        # ── SUB-TAB: CVNP ───────────────────────────────────────────────────
        with subtab_cvnp:
            if "CVNP" not in df.columns:
                st.info("Dados de CVNP nao disponiveis.")
            else:
                rows_c = []
                for g in gestoras_vals:
                    dg = df[df["Nome_Gestora"] == g]
                    total = dg["CVNP"].sum() if "CVNP" in dg.columns else 0
                    medio = dg["CVNP"].mean() if "CVNP" in dg.columns else np.nan
                    rows_c.append({
                        "Gestora": g,
                        "N Fundos": len(dg),
                        "CVNP Total (R$)": total,
                        "CVNP Medio/Fundo (R$)": medio,
                    })
                df_rank_c = pd.DataFrame(rows_c).sort_values("CVNP Total (R$)", ascending=True, na_position="last").reset_index(drop=True)
                df_rank_c.index = df_rank_c.index + 1
                df_rank_c.index.name = "Pos."

                st.markdown("**Ranking por CVNP Total — Credito Vencido nao Pago (ordem crescente = menor exposicao)**")

                df_plot_c = pd.DataFrame(rows_c).sort_values("CVNP Total (R$)")
                n_bc = len(df_plot_c)
                cores_c = _make_grad(max(n_bc, 2), alpha=0.85)
                fig_rank_c = go.Figure(go.Bar(
                    y=df_plot_c["Gestora"], x=df_plot_c["CVNP Total (R$)"],
                    orientation="h",
                    marker=dict(color=cores_c[:n_bc], line=dict(color="rgba(255,255,255,0.1)", width=0.5)),
                    text=[fmt_aum(v) for v in df_plot_c["CVNP Total (R$)"]],
                    textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>CVNP: R$ %{x:,.0f}<extra></extra>",
                ))
                _lc = _base_layout("", max(400, n_bc * 42 + 80))
                for _k in ("margin", "font", "legend"): _lc.pop(_k, None)
                fig_rank_c.update_layout(**_lc, bargap=0.32, margin=dict(l=120, r=80, t=30, b=50),
                                         font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
                fig_rank_c.update_xaxes(title_text="R$", tickfont=dict(size=11), tickformat=",.0f")
                fig_rank_c.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_rank_c, use_container_width=True, key="rank_cvnp_bar")

                st.dataframe(df_rank_c, use_container_width=True,
                             column_config={
                                 "CVNP Total (R$)":        st.column_config.NumberColumn(format="R$ %,.0f"),
                                 "CVNP Medio/Fundo (R$)":  st.column_config.NumberColumn(format="R$ %,.0f"),
                                 "N Fundos": st.column_config.NumberColumn(width="small"),
                             })

        # ── SUB-TAB: AGING ──────────────────────────────────────────────────
        with subtab_aging:
            if "Aging" not in df.columns:
                st.info("Dados de Aging nao disponiveis.")
            else:
                rows_ag = []
                for g in gestoras_vals:
                    dg = df[df["Nome_Gestora"] == g]
                    total = dg["Aging"].sum() if "Aging" in dg.columns else 0
                    medio = dg["Aging"].mean() if "Aging" in dg.columns else np.nan
                    rows_ag.append({
                        "Gestora": g,
                        "N Fundos": len(dg),
                        "Aging Total (R$)": total,
                        "Aging Medio/Fundo (R$)": medio,
                    })
                df_rank_ag = pd.DataFrame(rows_ag).sort_values("Aging Total (R$)", ascending=True, na_position="last").reset_index(drop=True)
                df_rank_ag.index = df_rank_ag.index + 1
                df_rank_ag.index.name = "Pos."

                st.markdown("**Ranking por Aging Total.**")

                df_plot_ag = pd.DataFrame(rows_ag).sort_values("Aging Total (R$)")
                n_bag = len(df_plot_ag)
                cores_ag = _make_grad(max(n_bag, 2), alpha=0.85)
                fig_rank_ag = go.Figure(go.Bar(
                    y=df_plot_ag["Gestora"], x=df_plot_ag["Aging Total (R$)"],
                    orientation="h",
                    marker=dict(color=cores_ag[:n_bag], line=dict(color="rgba(255,255,255,0.1)", width=0.5)),
                    text=[fmt_aum(v) for v in df_plot_ag["Aging Total (R$)"]],
                    textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>Aging: R$ %{x:,.0f}<extra></extra>",
                ))
                _lag = _base_layout("", max(400, n_bag * 42 + 80))
                for _k in ("margin", "font", "legend"): _lag.pop(_k, None)
                fig_rank_ag.update_layout(**_lag, bargap=0.32, margin=dict(l=120, r=80, t=30, b=50),
                                          font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
                fig_rank_ag.update_xaxes(title_text="R$", tickfont=dict(size=11), tickformat=",.0f")
                fig_rank_ag.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_rank_ag, use_container_width=True, key="rank_aging_bar")
                st.dataframe(df_rank_ag, use_container_width=True,
                             column_config={
                                 "Aging Total (R$)":        st.column_config.NumberColumn(format="R$ %,.0f"),
                                 "Aging Medio/Fundo (R$)":  st.column_config.NumberColumn(format="R$ %,.0f"),
                                 "N Fundos": st.column_config.NumberColumn(width="small"),
                             })

        # ── SUB-TAB: REMUNERAÇÃO ESPERADA ────────────────────────────────────
        with subtab_remun:
            st.markdown(
                '<div class="section-label">Remuneração Esperada Mensal por Gestora</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "`((1 + taxa_gestão/100)^(21/252) − 1) × PL` — "
                "Estimativa da receita mensal gerada pela taxa de gestão. "
                "Usa a taxa com imputação de média quando a taxa real não está disponível."
            )

            if "taxa_gestao" not in df.columns or "Valor_PL" not in df.columns:
                st.info("Dados de taxa de gestão ou PL não disponíveis.")
            else:
                # Calcular remuneração esperada por fundo
                df_remun_calc = df.copy()
                df_remun_calc["remun_esperada"] = (
                    ((1 + df_remun_calc["taxa_gestao"] / 100) ** (21 / 252)) - 1
                ) * df_remun_calc["Valor_PL"]

                # Agregar por gestora
                rows_remun = []
                for g in gestoras_vals:
                    dg = df_remun_calc[df_remun_calc["Nome_Gestora"] == g]
                    total_remun = dg["remun_esperada"].sum() if not dg.empty else 0.0
                    rows_remun.append({
                        "Gestora":                         g,
                        "N Fundos":                        len(dg),
                        "PL Total (R$)":                   dg["Valor_PL"].sum() if "Valor_PL" in dg.columns else 0,
                        "Taxa Gestao Med. Pond. (% a.a.)": weighted_mean(dg, "taxa_gestao"),
                        "Remun. Mensal Estimada (R$)":     total_remun,
                    })

                df_rank_remun = (
                    pd.DataFrame(rows_remun)
                    .sort_values("Remun. Mensal Estimada (R$)", ascending=False, na_position="last")
                    .reset_index(drop=True)
                )
                df_rank_remun.index = df_rank_remun.index + 1
                df_rank_remun.index.name = "Pos."

                total_grupo = df_rank_remun["Remun. Mensal Estimada (R$)"].sum()
                st.metric(
                    "Remuneração Total do Grupo (Estimada)",
                    f"R$ {total_grupo/1e6:.2f}M" if total_grupo >= 1e6 else f"R$ {total_grupo:,.0f}",
                )

                # Gráfico de barras horizontais
                df_plot_remun = (
                    pd.DataFrame(rows_remun)
                    .dropna(subset=["Remun. Mensal Estimada (R$)"])
                    .sort_values("Remun. Mensal Estimada (R$)")
                )
                n_br = len(df_plot_remun)
                cores_remun = _make_grad(max(n_br, 2), alpha=0.85)

                fig_remun = go.Figure(go.Bar(
                    y=df_plot_remun["Gestora"],
                    x=df_plot_remun["Remun. Mensal Estimada (R$)"],
                    orientation="h",
                    marker=dict(
                        color=cores_remun[:n_br],
                        line=dict(color="rgba(255,255,255,0.1)", width=0.5),
                    ),
                    text=[
                        f"R$ {v/1e6:.2f}M" if v >= 1e6 else f"R$ {v:,.0f}"
                        for v in df_plot_remun["Remun. Mensal Estimada (R$)"]
                    ],
                    textposition="outside",
                    textfont=dict(size=11, color=PALETTE["text"]),
                    hovertemplate="<b>%{y}</b><br>Remun. Mensal: R$ %{x:,.0f}<extra></extra>",
                ))
                _lr = _base_layout("", max(400, n_br * 42 + 80))
                for _k in ("margin", "font", "legend"): _lr.pop(_k, None)
                fig_remun.update_layout(
                    **_lr, bargap=0.32,
                    margin=dict(l=120, r=100, t=30, b=50),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                )
                fig_remun.update_xaxes(title_text="R$/mês (estimado)", tickfont=dict(size=11), tickformat=",.0f")
                fig_remun.update_yaxes(tickfont=dict(size=12), automargin=True)
                st.plotly_chart(fig_remun, use_container_width=True, key="rank_remun_bar")

                st.markdown("**Detalhamento por Gestora**")
                st.dataframe(
                    df_rank_remun,
                    use_container_width=True,
                    column_config={
                        "PL Total (R$)":                     st.column_config.NumberColumn(format="R$ %,.0f"),
                        "Taxa Gestao Med. Pond. (% a.a.)":   st.column_config.NumberColumn(format="%.3f%%"),
                        "Remun. Mensal Estimada (R$)":        st.column_config.NumberColumn(format="R$ %,.0f"),
                        "N Fundos":                           st.column_config.NumberColumn(width="small"),
                    },
                )

with tab_prest_servico:
    st.markdown(
        '<div class="section-label">Ranking por Prestador de Serviço</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Selecione o tipo de prestador e a métrica desejada para visualizar o ranking "
        "dos prestadores contratados pelos fundos das principais gestoras. "
        "Fundos com múltiplos prestadores do mesmo tipo geram uma linha por prestador."
    )

    @st.cache_data(ttl=3600, show_spinner=False)
    def _get_prest_filtrado(data_base):
        df_p = build_prest_servico()
        if data_base is not None and "Data_Posicao" in df_p.columns:
            df_p = df_p[df_p["Data_Posicao"] == pd.Timestamp(data_base)]
        return df_p

    _data_base = filters.get("data_base", None)
    df_prest = _get_prest_filtrado(_data_base)
    df_prest = df_prest[df_prest["Nome_Gestora"] == gestora_sel]
    df_prest = apply_sidebar_filters(df_prest, filters)

    if df_prest.empty:
        st.info("Nenhum dado de prestador de serviço disponível com os filtros aplicados.")
    else:
        tipos_disponiveis = [t for t in PRESTADOR_TIPOS if t in df_prest["tipo_prestador"].unique()]
        if not tipos_disponiveis:
            st.warning("Nenhum tipo de prestador encontrado.")
            st.stop()

        prest_col1, prest_col2 = st.columns([1.2, 1.8])
        with prest_col1:
            tipo_sel = st.selectbox("Tipo de Prestador", options=tipos_disponiveis, key="prest_tipo_sel")
        
        df_tipo = df_prest[df_prest["tipo_prestador"] == tipo_sel].copy()
        n_prestadores = df_tipo["prestador"].nunique()
        n_fundos_tipo = df_tipo["cnpj_tratado"].nunique()

        with prest_col2:
            st.markdown(" ")
            st.info(f"**{n_prestadores}** prestadores distintos encontrados · **{n_fundos_tipo}** fundos associados")

        METRICAS_PREST = {
            "PL Total":               "pl_total",
            "Inadimplência (PDD/DC)": "inad_dc",
            "Subordinação Jr.":       "sub_jr",
            "Subordinação Jr + Mez":  "sub_jrmz",
            "CVNP Total":             "cvnp",
            "Aging Total":            "aging",
        }
        metrica_label = st.selectbox("Métrica", options=list(METRICAS_PREST.keys()), key="prest_metrica_sel")
        metrica_key = METRICAS_PREST[metrica_label]
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        def _inad_dc_prest(df_):
            if df_.empty or not {"PDD", "DC"}.issubset(df_.columns): return np.nan
            d = df_["DC"].sum()
            return float(min(df_["PDD"].sum() / d * 100, 100.0)) if d > 0 else np.nan
        def _sub_jr_prest(df_):
            if not {"SB", "MZ", "SR"}.issubset(df_.columns): return np.nan
            denom = df_["SB"].sum() + df_["MZ"].sum() + df_["SR"].sum()
            return float(df_["SB"].sum() / denom * 100) if denom > 0 else np.nan
        def _sub_jrmz_prest(df_):
            if not {"SB", "MZ", "SR"}.issubset(df_.columns): return np.nan
            denom = df_["SB"].sum() + df_["MZ"].sum() + df_["SR"].sum()
            return float((df_["SB"].sum() + df_["MZ"].sum()) / denom * 100) if denom > 0 else np.nan

        rows_prest = []
        for prestador, dfp in df_tipo.groupby("prestador"):
            n_f = dfp["cnpj_tratado"].nunique()
            n_g = dfp["Nome_Gestora"].nunique() if "Nome_Gestora" in dfp.columns else 0
            pl  = dfp["Valor_PL"].sum() if "Valor_PL" in dfp.columns else 0
            rows_prest.append({
                "Prestador":               prestador,
                "N Fundos":                n_f,
                "N Gestoras":              n_g,
                "PL Total (R$)":           pl,
                "Inadimplência PDD/DC (%)": _inad_dc_prest(dfp),
                "Subordinação Jr. (%)":    _sub_jr_prest(dfp),
                "Subordinação Jr+Mez (%)": _sub_jrmz_prest(dfp),
                "CVNP Total (R$)":         dfp["CVNP"].sum() if "CVNP" in dfp.columns else 0,
                "Aging Total (R$)":        dfp["Aging"].sum() if "Aging" in dfp.columns else 0,
            })

        df_rank_prest = pd.DataFrame(rows_prest)
        _METRICA_COL = {
            "pl_total": ("PL Total (R$)",              False, True),
            "inad_dc":  ("Inadimplência PDD/DC (%)",   True,  False),
            "sub_jr":   ("Subordinação Jr. (%)",        False, False),
            "sub_jrmz": ("Subordinação Jr+Mez (%)",    False, False),
            "cvnp":     ("CVNP Total (R$)",             True,  True),
            "aging":    ("Aging Total (R$)",            True,  True),
        }
        col_val, asc_order, is_monet = _METRICA_COL[metrica_key]

        df_plot_prest = df_rank_prest.dropna(subset=[col_val]).sort_values(col_val, ascending=asc_order)
        n_bp = len(df_plot_prest)
        st.markdown(f"**{metrica_label} por {tipo_sel} — Ranking dos Prestadores**")

        if n_bp == 0:
            st.warning("A métrica não pôde ser calculada. Consulte a tabela abaixo.")
        else:
            cores_prest = _make_grad(max(n_bp, 2), alpha=0.85)
            _nomes_curtos = [n[:45] + "…" if len(n) > 45 else n for n in df_plot_prest["Prestador"]]
            if is_monet:
                _txt, _xtitle, _htmpl, _xtfmt, _xsuf = [fmt_aum(v) for v in df_plot_prest[col_val]], "R$", f"<b>%{{y}}</b><br>{metrica_label}: R$ %{{x:,.0f}}<extra></extra>", ",.0f", ""
            else:
                _txt, _xtitle, _htmpl, _xtfmt, _xsuf = [fmt_pct(v) for v in df_plot_prest[col_val]], "%", f"<b>%{{y}}</b><br>{metrica_label}: %{{x:.2f}}%<extra></extra>", "", "%"

            fig_prest = go.Figure(go.Bar(y=_nomes_curtos, x=df_plot_prest[col_val].tolist(), orientation="h",
                marker=dict(color=cores_prest[:n_bp], line=dict(color="rgba(255,255,255,0.10)", width=0.5)),
                text=_txt, textposition="outside", textfont=dict(size=11, color=PALETTE["text"]),
                hovertemplate=_htmpl, customdata=df_plot_prest[["N Fundos", "N Gestoras"]].values))

            _mg = df_plot_prest[col_val].mean()
            if pd.notna(_mg):
                fig_prest.add_vline(x=_mg, line=dict(color="rgba(217,119,6,0.9)", dash="dot", width=2))
                _lbl_mg = f"Média: {fmt_aum(_mg)}" if is_monet else f"Média: {_mg:.2f}%"
                fig_prest.add_annotation(x=_mg, y=1.01, yref="paper", text=f"<b>{_lbl_mg}</b>", showarrow=False, xanchor="left", xshift=8, font=dict(size=10, color="#FFFFFF"), bgcolor="rgba(217,119,6,0.8)", borderpad=5, bordercolor="rgba(0,0,0,0)")

            _lt_p = _base_layout("", max(420, n_bp * 44 + 100))
            for _k in ("margin", "font", "legend"): _lt_p.pop(_k, None)
            fig_prest.update_layout(**_lt_p, bargap=0.30, margin=dict(l=20, r=100, t=40, b=50), font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]))
            fig_prest.update_xaxes(title_text=_xtitle, tickfont=dict(size=11), tickformat=_xtfmt, ticksuffix=_xsuf, automargin=True)
            fig_prest.update_yaxes(tickfont=dict(size=11), automargin=True)
            st.plotly_chart(fig_prest, use_container_width=True, key=f"prest_rank_{tipo_sel}_{metrica_key}")

        st.markdown("---")
        st.markdown(f"**Tabela Resumo — {tipo_sel}**")
        df_tabela_prest = df_rank_prest.sort_values(col_val, ascending=asc_order, na_position="last").reset_index(drop=True)
        df_tabela_prest.index = df_tabela_prest.index + 1
        df_tabela_prest.index.name = "Pos."
        _cfg_prest = {
            "PL Total (R$)":             st.column_config.NumberColumn(format="R$ %,.0f"),
            "CVNP Total (R$)":           st.column_config.NumberColumn(format="R$ %,.0f"),
            "Aging Total (R$)":          st.column_config.NumberColumn(format="R$ %,.0f"),
            "Inadimplência PDD/DC (%)":  st.column_config.NumberColumn(format="%.2f%%"),
            "Subordinação Jr. (%)":      st.column_config.NumberColumn(format="%.2f%%"),
            "Subordinação Jr+Mez (%)":   st.column_config.NumberColumn(format="%.2f%%"),
            "N Fundos":                  st.column_config.NumberColumn(width="small"),
            "N Gestoras":                st.column_config.NumberColumn(width="small"),
        }
        st.dataframe(
            df_tabela_prest,
            use_container_width=True,
            column_config=_cfg_prest,
        )

        # ── Tabela Analítica Detalhada (por fundo) — SEMPRE visível ──────────
        st.markdown("---")
        st.markdown(f"**Tabela Analítica — Detalhamento por Fundo · {tipo_sel}**")
        st.caption(
            "Uma linha por fundo × prestador. Permite validar os números individuais "
            "e exportar para Excel."
        )

        _cols_det_map = {
            "prestador":             "Prestador",
            "tipo_prestador":        "Tipo",
            "Nome_Gestora":          "Gestora",
            "gestor":                "Gestor (Razão Social)",
            "nome_fundo":            "Fundo",
            "cnpj_tratado":          "CNPJ",
            "foco_atuacao":          "Segmento",
            "Data_Posicao":          "Data Base",
            "Valor_PL":              "PL (R$)",
            "PDD":                   "PDD (R$)",
            "DC":                    "DC (R$)",
            "PL_CVM":                "PL CVM (R$)",
            "taxa_inadimplencia":    "Inadimplência PDD/DC (%)",
            "taxa_inadimplencia_pl": "Inadimplência PDD/PL (%)",
            "Sub_JR":                "Sub Jr (%)",
            "Sub_JR_MZ":             "Sub Jr+Mez (%)",
            "CVNP":                  "CVNP (R$)",
            "Aging":                 "Aging (R$)",
        }
        _existing_det = [c for c in _cols_det_map if c in df_tipo.columns]
        df_det = df_tipo[_existing_det].rename(columns=_cols_det_map).copy()

        if "Data Base" in df_det.columns:
            df_det["Data Base"] = pd.to_datetime(
                df_det["Data Base"], errors="coerce"
            ).dt.strftime("%b/%Y")

        _sort_det = [c for c in ["Prestador", "Fundo"] if c in df_det.columns]
        df_det = df_det.sort_values(_sort_det, na_position="last").reset_index(drop=True)

        st.markdown(
            f"<small style='color:var(--text-muted)'>{len(df_det):,} registros</small>",
            unsafe_allow_html=True,
        )

        _cfg_det = {}
        for _orig, _disp in _cols_det_map.items():
            if _disp not in df_det.columns:
                continue
            if _disp in ("PL (R$)", "PDD (R$)", "DC (R$)", "PL CVM (R$)", "CVNP (R$)", "Aging (R$)"):
                _cfg_det[_disp] = st.column_config.NumberColumn(format="R$ %,.0f")
            elif _disp in ("Inadimplência PDD/DC (%)", "Inadimplência PDD/PL (%)",
                           "Sub Jr (%)", "Sub Jr+Mez (%)"):
                _cfg_det[_disp] = st.column_config.NumberColumn(format="%.2f%%")

        st.dataframe(
            df_det,
            use_container_width=True,
            hide_index=True,
            column_config=_cfg_det,
            height=380,
        )

        # Botão de download Excel (duas abas)
        import io as _io_prest
        _buf_prest = _io_prest.BytesIO()
        with pd.ExcelWriter(_buf_prest, engine="openpyxl") as _writer_prest:
            df_det.to_excel(_writer_prest, index=False, sheet_name="Detalhado_por_Fundo")
            df_tabela_prest.to_excel(_writer_prest, index=True, sheet_name="Resumo_Prestadores")
        _buf_prest.seek(0)

        st.download_button(
            label=f"⬇️ Exportar para Excel — {tipo_sel} · {gestora_sel}",
            data=_buf_prest.read(),
            file_name=f"prestadores_{tipo_sel.lower().replace(' ', '_')}_{gestora_sel.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ─── Toggle: Evolucao Temporal por Foco de Atuacao ───────────────────────
with tab_evolucao:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-label">Evolu\u00e7\u00e3o Temporal das Principais Gestoras</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Compara a evolu\u00e7\u00e3o de cada gestora individualmente ao longo do tempo. "
        "A gestora selecionada globalmente \u00e9 destacada em dourado."
    )

    if "Data_Posicao" not in df_historico.columns:
        st.warning("Coluna Data_Posicao nao encontrada no dataset.")
    else:
        # ── Controles ────────────────────────────────────────────────────────
        ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([1.4, 1, 1.6])

        with ctrl_c1:
            VARIAVEIS_EV = {
                "PL Total (AuM)":         "pl_total",
                "Remun. Esperada Mensal": "remun_esperada",
                "Taxa de Gestao":         "taxa_gestao",
                "Taxa de Administracao":  "taxa_administracao",
                "Taxa de Performance":    "taxa_performance",
                "Inadimplencia (PDD/DC)": "inad_dc",
                "Inadimplencia (PDD/PL)": "inad_pl",
                "Subordinacao Jr.":        "sub_jr",
                "Subordinacao Jr + Mez":   "sub_jrmz",
                "CVNP Total":             "cvnp_total",
                "Aging Total":            "aging_total",
            }
            var_ev_label = st.selectbox(
                "Vari\u00e1vel",
                options=list(VARIAVEIS_EV.keys()),
                key="evolucao_var",
            )
            var_ev_key = VARIAVEIS_EV[var_ev_label]

        with ctrl_c2:
            modo_foco = st.radio(
                "Visualiza\u00e7\u00e3o",
                options=["Agregado", "Por Foco de Atua\u00e7\u00e3o"],
                key="evolucao_modo_foco",
                horizontal=False,
            )

        with ctrl_c3:
            focos_disponiveis_all = sorted(df_historico["foco_atuacao"].dropna().unique().tolist())
            foco_ev = None
            if modo_foco == "Por Foco de Atua\u00e7\u00e3o" and focos_disponiveis_all:
                foco_ev = st.selectbox(
                    "Foco de Atua\u00e7\u00e3o",
                    options=focos_disponiveis_all,
                    key="evolucao_foco",
                )
            else:
                st.caption("\u00a0")  # placeholder para manter layout

        # ── Fun\u00e7\u00e3o de s\u00e9rie temporal (reutiliz\u00e1vel) ────────────────────────────
        def _serie_temporal(df_, var_key_):
            if df_.empty or "Data_Posicao" not in df_.columns:
                return pd.Series(dtype=float)
            if df_["Data_Posicao"].dropna().empty:
                return pd.Series(dtype=float)
            if var_key_ in ["taxa_gestao", "taxa_administracao", "taxa_performance"]:
                if var_key_ not in df_.columns: return pd.Series(dtype=float)
                agg_t = df_[["Data_Posicao", var_key_, "PL_CVM"]].dropna()
                agg_t = agg_t[agg_t["PL_CVM"] > 0]
                if agg_t.empty:
                    return df_.groupby("Data_Posicao")[var_key_].mean().sort_index()
                num = agg_t.groupby("Data_Posicao").apply(lambda g: (g[var_key_] * g["PL_CVM"]).sum())
                den = agg_t.groupby("Data_Posicao")["PL_CVM"].sum()
                return (num / den).sort_index()
            if var_key_ == "inad_dc":
                if not {"PDD", "DC"}.issubset(df_.columns): return pd.Series(dtype=float)
                agg = df_.groupby("Data_Posicao")[["PDD", "DC"]].sum()
                vals = np.where(agg["DC"] > 0, (agg["PDD"] / agg["DC"] * 100).clip(upper=100), np.nan)
                return pd.Series(vals, index=agg.index).sort_index()
            if var_key_ == "inad_pl":
                if not {"PDD", "PL_CVM"}.issubset(df_.columns): return pd.Series(dtype=float)
                agg = df_.groupby("Data_Posicao")[["PDD", "PL_CVM"]].sum()
                vals = np.where(agg["PL_CVM"] > 0, (agg["PDD"] / agg["PL_CVM"] * 100).clip(upper=100), np.nan)
                return pd.Series(vals, index=agg.index).sort_index()
            if var_key_ == "sub_jr":
                if not {"SB", "MZ", "SR"}.issubset(df_.columns): return pd.Series(dtype=float)
                agg   = df_.groupby("Data_Posicao")[["SB", "MZ", "SR"]].sum()
                denom = agg["SB"] + agg["MZ"] + agg["SR"]
                vals  = np.where(denom > 0, agg["SB"] / denom * 100, np.nan)
                return pd.Series(vals, index=agg.index).sort_index()
            if var_key_ == "sub_jrmz":
                if not {"SB", "MZ", "SR"}.issubset(df_.columns): return pd.Series(dtype=float)
                agg   = df_.groupby("Data_Posicao")[["SB", "MZ", "SR"]].sum()
                denom = agg["SB"] + agg["MZ"] + agg["SR"]
                vals  = np.where(denom > 0, (agg["SB"] + agg["MZ"]) / denom * 100, np.nan)
                return pd.Series(vals, index=agg.index).sort_index()
            if var_key_ == "cvnp_total":
                if "CVNP" not in df_.columns: return pd.Series(dtype=float)
                return df_.groupby("Data_Posicao")["CVNP"].sum().sort_index()
            if var_key_ == "aging_total":
                if "Aging" not in df_.columns: return pd.Series(dtype=float)
                return df_.groupby("Data_Posicao")["Aging"].sum().sort_index()
            if var_key_ == "pl_total":
                if "Valor_PL" not in df_.columns: return pd.Series(dtype=float)
                return df_.groupby("Data_Posicao")["Valor_PL"].sum().sort_index()
            if var_key_ == "remun_esperada":
                if "taxa_gestao" not in df_.columns or "Valor_PL" not in df_.columns:
                    return pd.Series(dtype=float)
                tmp = df_[["Data_Posicao", "taxa_gestao", "Valor_PL"]].dropna()
                tmp = tmp[tmp["Valor_PL"] > 0]
                if tmp.empty: return pd.Series(dtype=float)
                tmp["remun"] = (((1 + tmp["taxa_gestao"] / 100) ** (21 / 252)) - 1) * tmp["Valor_PL"]
                return tmp.groupby("Data_Posicao")["remun"].sum().sort_index()
            return pd.Series(dtype=float)

        # ── Paleta de cores para as gestoras ─────────────────────────────────
        # Gera uma cor distinta para cada gestora; gestora_sel fica dourada e mais grossa
        _CORES_GESTORAS = [
            "rgba(99,179,237,0.9)",   # azul claro
            "rgba(154,117,222,0.9)",  # roxo
            "rgba(72,199,142,0.9)",   # verde
            "rgba(237,100,166,0.9)",  # rosa
            "rgba(247,144,73,0.9)",   # laranja
            "rgba(100,210,223,0.9)",  # ciano
            "rgba(200,214,94,0.9)",   # amarelo-verde
            "rgba(183,110,121,0.9)",  # vinho
            "rgba(111,165,198,0.9)",  # azul acinzentado
            "rgba(200,160,80,0.9)",   # dourado escuro
        ]
        _COR_DESTAQUE = "rgba(255,195,106,1.0)"  # dourado brilhante para gestora_sel

        # ── Construir gr\u00e1fico ───────────────────────────────────────────────
        is_monetary = var_ev_key in ["cvnp_total", "aging_total", "pl_total", "remun_esperada"]
        y_suffix    = "" if is_monetary else "%"

        fig_ev  = go.Figure()
        n_com_dados = 0

        gestoras_no_historico = [
            g for g in gestoras_disponiveis
            if g in df_historico["Nome_Gestora"].dropna().unique()
        ]

        cor_idx = 0
        for g in gestoras_no_historico:
            df_g_hist = df_historico[df_historico["Nome_Gestora"] == g]

            # Filtrar por foco se o modo exigir
            if foco_ev is not None:
                df_g_hist = df_g_hist[df_g_hist["foco_atuacao"] == foco_ev]

            serie_g = _serie_temporal(df_g_hist, var_ev_key)
            if serie_g.empty:
                continue

            eh_destaque = (g == gestora_sel)
            if eh_destaque:
                cor      = _COR_DESTAQUE
                espessura = 3.0
                tamanho_pt = 8
                dash_style = "solid"
            else:
                cor      = _CORES_GESTORAS[cor_idx % len(_CORES_GESTORAS)]
                espessura = 1.8
                tamanho_pt = 5
                dash_style = "solid"
                cor_idx += 1

            x_dates = [pd.Timestamp(d).strftime("%b/%Y") for d in serie_g.index]
            fig_ev.add_trace(go.Scatter(
                x=x_dates, y=serie_g.values,
                name=g,
                mode="lines+markers",
                line=dict(color=cor, width=espessura, dash=dash_style),
                marker=dict(size=tamanho_pt, color=cor,
                            line=dict(width=1.2 if eh_destaque else 0.5,
                                      color="#F89B66" if eh_destaque else "rgba(255,255,255,0.3)")),
                hovertemplate=(
                    f"<b>{g}</b><br>%{{x}}<br>"
                    + ("R$ %{y:,.0f}" if is_monetary else f"%{{y:.2f}}{y_suffix}")
                    + "<extra></extra>"
                ),
            ))
            n_com_dados += 1

        titulo_foco = f" | {foco_ev}" if foco_ev else " | Agregado"
        if n_com_dados == 0:
            st.info(f"Nenhum dado dispon\u00edvel para {var_ev_label}{titulo_foco}.")
        else:
            ev_h = max(460, 380 + n_com_dados * 6)
            _layout_ev = _base_layout("", ev_h)
            for _k in ("margin", "font", "legend"):
                _layout_ev.pop(_k, None)
            fig_ev.update_layout(
                **_layout_ev,
                margin=dict(l=60, r=40, t=40, b=80),
                font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                legend=dict(
                    orientation="h", yanchor="top", y=-0.15,
                    xanchor="left", x=0,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)",
                    itemwidth=120,
                ),
                hovermode="x unified",
            )
            fig_ev.update_xaxes(tickfont=dict(size=11), title_text="Per\u00edodo", tickangle=-30)
            if is_monetary:
                fig_ev.update_yaxes(tickfont=dict(size=11), title_text="R$", tickformat=",.0f")
            else:
                fig_ev.update_yaxes(tickfont=dict(size=11), title_text=f"% \u2014 {var_ev_label}", ticksuffix="%")

            titulo_grafico = f"{var_ev_label}{titulo_foco} \u2014 Todas as Gestoras"
            st.markdown(f"**{titulo_grafico}**")
            st.caption(
                f"Gestora destacada (dourado): **{gestora_sel}**. "
                "Passe o mouse sobre as linhas para ver os valores."
            )
            _ev_key = f"evolucao_all_{var_ev_key}_{foco_ev or 'agregado'}"
            st.plotly_chart(fig_ev, use_container_width=True, key=_ev_key)


with tab_tabela_analitica:                          
        # ─── Tabela Analitica — Fundos das Principais Gestoras ────────────────
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="section-label">Tabela Analitica — Fundos das Principais Gestoras</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Detalhamento completo dos fundos das principais gestoras com todos os periodos disponiveis. "
            "Use a busca para filtrar por fundo, CNPJ, gestora ou segmento."
        )

        # Colunas a exibir
        _cols_map = {
            "Nome_Gestora":          "Gestora",
            "foco_atuacao":          "Segmento",
            "gestor":                "Gestor (Razao Social)",
            "nome_fundo":            "Fundo",
            "cnpj_tratado":          "CNPJ",
            "Data_Posicao":          "Data Base",
            "Valor_PL":              "PL (R$)",
            "taxa_gestao_raw":       "Taxa Gestao Real (% a.a.)",
            "taxa_gestao":           "Taxa Gestao (% a.a.)",
            "taxa_administracao":    "Taxa Adm (% a.a.)",
            "taxa_performance":      "Taxa Performance (% a.a.)",
            "PDD":                   "PDD (R$)",
            "DC":                    "DC (R$)",
            "PL_CVM":                "PL CVM (R$)",
            "taxa_inadimplencia":    "Inadimplencia PDD/DC (%)",
            "taxa_inadimplencia_pl": "Inadimplencia PDD/PL (%)",
            "Sub_JR":                "Sub Jr (%)",
            "Sub_JR_MZ":             "Sub Jr+Mez (%)",
            "CVNP":                  "CVNP (R$)",
            "Aging":                 "Aging (R$)",
            "Situacao":              "Situacao",
        }

        # Usar df_historico para trazer todos os periodos
        _existing = [c for c in _cols_map if c in df_historico.columns]
        df_analitica = df_historico[_existing].rename(columns=_cols_map).copy()

        # Formatar Data Base
        if "Data Base" in df_analitica.columns:
            df_analitica["Data Base"] = pd.to_datetime(
                df_analitica["Data Base"], errors="coerce"
            ).dt.strftime("%b/%Y")

        # Busca textual
        _search = st.text_input(
            "Busca na tabela",
            key="analitica_search_toggle",
            placeholder="Buscar por fundo, CNPJ, gestora ou segmento...",
        )
        if _search:
            _mask = df_analitica.apply(
                lambda row: row.astype(str).str.contains(_search, case=False).any(), axis=1
            )
            df_analitica = df_analitica[_mask]

        st.markdown(
            f"<small style='color:var(--text-muted)'>{len(df_analitica):,} registros encontrados</small>",
            unsafe_allow_html=True,
        )

        _col_cfg_an = {}
        for _orig, _disp in _cols_map.items():
            if _disp not in df_analitica.columns:
                continue
            if _disp in ("PL (R$)", "PDD (R$)", "DC (R$)", "PL CVM (R$)", "CVNP (R$)", "Aging (R$)"):
                _col_cfg_an[_disp] = st.column_config.NumberColumn(format="R$ %,.0f")
            elif _disp in ("Taxa Gestao Real (% a.a.)", "Taxa Gestao (% a.a.)",
                           "Taxa Adm (% a.a.)", "Taxa Performance (% a.a.)"):
                _col_cfg_an[_disp] = st.column_config.NumberColumn(format="%.3f%%")
            elif _disp in ("Inadimplencia PDD/DC (%)", "Inadimplencia PDD/PL (%)",
                           "Sub Jr (%)", "Sub Jr+Mez (%)"):
                _col_cfg_an[_disp] = st.column_config.NumberColumn(format="%.2f%%")

        st.dataframe(
            df_analitica,
            use_container_width=True,
            hide_index=True,
            column_config=_col_cfg_an,
            height=400,
        )

        # Botao de download
        import io as _io
        _buf = _io.BytesIO()
        with pd.ExcelWriter(_buf, engine="openpyxl") as _writer:
            df_analitica.to_excel(_writer, index=False, sheet_name="Principais Gestoras")
        _buf.seek(0)

        st.download_button(
            label="Exportar para Excel (.xlsx)",
            data=_buf.read(),
            file_name="principais_gestoras_analitico.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )