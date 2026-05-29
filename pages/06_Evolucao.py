"""Página 6 — Evolução Temporal"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import PALETTE, _base_layout
from utils.data_loader import build_df_fidc

load_css()

# ── Carregar dados ────────────────────────────────────────────────────────────
df_full = build_df_fidc()

# Na página de evolução desabilitamos o filtro de data — queremos todo o histórico
filters = render_sidebar(df_full, show_date_filter=False)

# Aplicar filtros de segmento/gestor/adm preservando todas as datas
df = apply_sidebar_filters(df_full, filters)

if df.empty or "Data_Posicao" not in df.columns:
    st.warning("Não há dados temporais disponíveis para os filtros selecionados.")
    st.stop()

# ── Normalizar datas para 1º do mês — evita shift de UTC no eixo X ──────────
# Datas originais são fim de mês (jan-31, fev-28…). Plotly exibe corretamente
# como "Feb/2026" porque interpreta o último dia como pertencente ao mês seguinte
# em certos fusos. Normalizar para o 1º do mês elimina a ambiguidade.
def _to_month_start(series: pd.Series) -> pd.Series:
    """Converte qualquer data para o primeiro dia do respectivo mês."""
    return pd.to_datetime(series).dt.to_period("M").dt.to_timestamp()

df = df.copy()
df["Data_Posicao"] = _to_month_start(df["Data_Posicao"])

page_header("📈", "Evolução Histórica",
            "Análise temporal de remuneração, inadimplência e subordinação")

st.markdown("---")

tab_remun_gest, tab_remun_adm, tab_inad, tab_sub = st.tabs(["Remuneração do Gestor", "Remuneração do Administrador", "Inadimplência", "Subordinação"])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de gráfico
# ──────────────────────────────────────────────────────────────────────────────

def _build_fig(title: str, y_title: str, height: int = 460) -> go.Figure:
    """Cria figura vazia com layout padrão já aplicado."""
    fig = go.Figure()
    _layout = _base_layout(title, height)
    _layout["xaxis"].update(dict(title="Data Base", tickformat="%b/%Y", dtick="M1"))
    _layout["yaxis"].update(dict(title=y_title))
    _layout["legend"].update(dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5))
    fig.update_layout(**_layout)
    return fig


def _fmt_currency(v: float) -> str:
    """Formata número como moeda de forma legível."""
    if v >= 1e9:
        return f"R$ {v/1e9:.2f}B"
    if v >= 1e6:
        return f"R$ {v/1e6:.2f}M"
    if v >= 1e3:
        return f"R$ {v/1e3:.0f}K"
    return f"R$ {v:,.0f}"


def add_trace_line(fig, x, y, name: str, is_highlight: bool,
                   hover_fmt: str = ".3f", dash: str | None = None):
    """Adiciona uma linha ao gráfico com estilo adequado."""
    if is_highlight:
        color, width = "rgba(59,130,246,0.95)", 4
        dash = dash or "solid"
        marker_size = 10
        opacity = 1.0
    else:
        color, width = "rgba(217,119,6,0.75)", 2
        dash = dash or "dot"
        marker_size = 7
        opacity = 0.70

    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines+markers",
        name=name,
        line=dict(color=color, width=width, dash=dash),
        marker=dict(size=marker_size),
        opacity=opacity,
        hovertemplate=f"<b>{name}</b><br>%{{x|%b/%Y}}: %{{y:{hover_fmt}}}<extra></extra>",
    ))


# ──────────────────────────────────────────────────────────────────────────────
# Funções de evolução
# ──────────────────────────────────────────────────────────────────────────────

def plot_remun_by_entity(df_all: pd.DataFrame, date_col: str, val_col: str,
                          entity_col: str, highlight_name: str,
                          y_title: str, title: str, top_n_other: int = 5) -> go.Figure:
    """
    Evolução da SOMA da remuneração por entidade (gestora ou administradora).
    Plota a entidade selecionada em destaque + as top_n_other com mais AuM.
    """
    fig = _build_fig(title, y_title)

    needed = [val_col, date_col, entity_col]
    if any(c not in df_all.columns for c in needed):
        return fig

    df_work = df_all.dropna(subset=[val_col, date_col, entity_col]).copy()
    if df_work.empty:
        return fig

    is_highlight = df_work[entity_col].str.contains(highlight_name, case=False, na=False)
    df_hi = df_work[is_highlight]
    df_other = df_work[~is_highlight]

    # Top entidades do mercado por REMUNERAÇÃO TOTAL acumulada (mesmo critério do ranking)
    top_entities = (
        df_other.groupby(entity_col)[val_col].sum()
        .nlargest(top_n_other)
        .index.tolist()
    )

    # Linhas das outras entidades primeiro (ficam atrás)
    for ent in top_entities:
        df_e = df_other[df_other[entity_col] == ent]
        evo = df_e.groupby(date_col)[val_col].sum().sort_index()
        if evo.empty:
            continue
        fig.add_trace(go.Scatter(
            x=evo.index, y=evo.values,
            mode="lines+markers",
            name=str(ent)[:45],
            line=dict(width=2, dash="dot"),
            marker=dict(size=6),
            opacity=0.60,
            hovertemplate=f"<b>{str(ent)[:45]}</b><br>%{{x|%b/%Y}}: %{{customdata}}<extra></extra>",
            customdata=[_fmt_currency(v) for v in evo.values],
        ))

    # Entidade em destaque por cima
    if not df_hi.empty:
        evo_hi = df_hi.groupby(date_col)[val_col].sum().sort_index()
        if not evo_hi.empty:
            fig.add_trace(go.Scatter(
                x=evo_hi.index, y=evo_hi.values,
                mode="lines+markers",
                name=f"{highlight_name} (destaque)",
                line=dict(color="rgba(59,130,246,0.95)", width=4, dash="solid"),
                marker=dict(size=10),
                hovertemplate=f"<b>{highlight_name}</b><br>%{{x|%b/%Y}}: %{{customdata}}<extra></extra>",
                customdata=[_fmt_currency(v) for v in evo_hi.values],
            ))

    return fig


def plot_inad_pondered(df_all: pd.DataFrame, date_col: str,
                        pdd_col: str, base_col: str,
                        y_title: str, title: str) -> go.Figure:
    """
    Evolução da inadimplência ponderada: sum(PDD) / sum(DC ou PL) × 100.
    Metodologia idêntica ao KPI da Visão Geral.
    """
    fig = _build_fig(title, y_title)

    needed = [date_col, pdd_col, base_col, "gestor"]
    if any(c not in df_all.columns for c in needed):
        return fig

    df_work = df_all.dropna(subset=[pdd_col, base_col, date_col]).copy()
    df_work = df_work[df_work[base_col] > 0]
    if df_work.empty:
        return fig

    is_solis_mask = df_work["gestor"].str.contains("Solis", case=False, na=False)

    for label, mask, is_sol in [
        ("Mercado (excl. Solis)", ~is_solis_mask, False),
        ("Solis Investimentos", is_solis_mask, True),
    ]:
        df_g = df_work[mask]
        if df_g.empty:
            continue
        # Agregar com soma antes de dividir (sem apply, mais robusto)
        agg = df_g.groupby(date_col)[[pdd_col, base_col]].sum()
        evo = (agg[pdd_col] / agg[base_col] * 100).clip(upper=100).sort_index()
        if evo.empty:
            continue
        add_trace_line(fig, evo.index, evo.values, label, is_highlight=is_sol,
                       hover_fmt=".2f")

    return fig


def plot_mean_simple(df_all: pd.DataFrame, date_col: str, val_col: str,
                      y_title: str, title: str) -> go.Figure:
    """Média simples de uma métrica — Solis vs Mercado."""
    fig = _build_fig(title, y_title)

    if any(c not in df_all.columns for c in [val_col, date_col, "gestor"]):
        return fig

    df_work = df_all.dropna(subset=[val_col, date_col, "gestor"]).copy()
    if df_work.empty:
        return fig

    is_solis_mask = df_work["gestor"].str.contains("Solis", case=False, na=False)

    for label, mask, is_sol in [
        ("Mercado (excl. Solis)", ~is_solis_mask, False),
        ("Solis Investimentos", is_solis_mask, True),
    ]:
        df_g = df_work[mask]
        if df_g.empty:
            continue
        evo = df_g.groupby(date_col)[val_col].mean().sort_index()
        if evo.empty:
            continue
        add_trace_line(fig, evo.index, evo.values, label, is_highlight=is_sol,
                       hover_fmt=".2f")

    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Aba: Remuneração
# ──────────────────────────────────────────────────────────────────────────────

with tab_remun_gest:
    if "Valor_PL" not in df.columns:
        st.info("Dados de PL não disponíveis para calcular a evolução de remuneração.")
    else:
        # ── Toggle: taxa real vs. imputada ─────────────────────────────────────
        usar_taxa_real = st.toggle(
            "Usar apenas taxa real (sem imputação pela média da gestora)",
            value=True,
            key="toggle_remun_gest",
        )

        taxa_gest_col = "taxa_gestao_raw" if usar_taxa_real else "taxa_gestao"
        taxa_adm_col  = "taxa_administracao_raw" if usar_taxa_real else "taxa_administracao"
        modo_label    = "Taxa Real" if usar_taxa_real else "Taxa Imputada"

        df_remun = df.copy()

        # Calcular remuneração conforme modo selecionado
        if taxa_gest_col in df_remun.columns:
            df_remun["remun_mensal_gestao"] = (
                ((1 + df_remun[taxa_gest_col] / 100) ** (21 / 252)) - 1
            ) * df_remun["Valor_PL"]
        if taxa_adm_col in df_remun.columns:
            df_remun["remun_mensal_adm"] = (
                ((1 + df_remun[taxa_adm_col] / 100) ** (21 / 252)) - 1
            ) * df_remun["Valor_PL"]

        ultima_data = df_remun["Data_Posicao"].max()

        # ── Bloco Gestoras ────────────────────────────────────────────────────
        st.markdown(
            f'<div class="section-label">Evolução de Remuneração — Gestoras ({modo_label})</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Soma da remuneração mensal estimada (`((1 + taxa/100)^(21/252) - 1) × PL`) "
            f"de todos os fundos sob gestão — **{modo_label}**. "
            "Solis em azul sólido vs. top 5 gestoras por AuM."
        )

        if "remun_mensal_gestao" in df_remun.columns:
            # Gráfico — linha inteira
            st.plotly_chart(
                plot_remun_by_entity(
                    df_remun, "Data_Posicao", "remun_mensal_gestao",
                    entity_col="gestor", highlight_name="Solis",
                    y_title="Remuneração Total (R$/mês)",
                    title=f"Remuneração de Gestão — Total por Gestora ({modo_label})",
                ),
                use_container_width=True,
            )

            # Ranking — linha inteira abaixo
            df_ult_gest = df_remun[df_remun["Data_Posicao"] == ultima_data]
            rank_gest = (
                df_ult_gest.dropna(subset=["remun_mensal_gestao", "gestor"])
                .groupby("gestor")["remun_mensal_gestao"].sum()
                .sort_values(ascending=False)
                .head(15)
                .reset_index()
            )
            rank_gest.columns = ["Gestora", "Remuneração (R$/mês)"]
            rank_gest["Remuneração (R$/mês)"] = rank_gest["Remuneração (R$/mês)"].apply(_fmt_currency)
            st.markdown(f"**Ranking de Gestoras — {ultima_data.strftime('%b/%Y')} ({modo_label})**")
            st.dataframe(rank_gest, use_container_width=True, hide_index=True)
        else:
            st.info(f"Taxa `{taxa_gest_col}` não disponível para o cálculo.")


# ──────────────────────────────────────────────────────────────────────────────
# Aba: Remuneracao Admin
# ──────────────────────────────────────────────────────────────────────────────

with tab_remun_adm:
    if "Valor_PL" not in df.columns:
        st.info("Dados de PL não disponíveis para calcular a evolução de remuneração.")
    else:
        # ── Toggle: taxa real vs. imputada ─────────────────────────────────────
        usar_taxa_real = st.toggle(
            "Usar apenas taxa real (sem imputação pela média da administradora)",
            value=True,
            key="toggle_remun_adm",
        )

        taxa_adm_col  = "taxa_administracao_raw" if usar_taxa_real else "taxa_administracao"
        modo_label    = "Taxa Real" if usar_taxa_real else "Taxa Imputada"

        df_remun = df.copy()

        # Calcular remuneração conforme modo selecionado
        if taxa_adm_col in df_remun.columns:
            df_remun["remun_mensal_adm"] = (
                ((1 + df_remun[taxa_adm_col] / 100) ** (21 / 252)) - 1
            ) * df_remun["Valor_PL"]

        ultima_data = df_remun["Data_Posicao"].max()
        # ── Bloco Administradoras ─────────────────────────────────────────────
        if "administrador" in df_remun.columns:
            st.markdown(
                f'<div class="section-label">Evolução de Remuneração — Administradoras ({modo_label})</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                f"Soma da remuneração mensal estimada de todos os fundos sob administração — **{modo_label}**. "
                "Top 5 administradoras por AuM total."
            )

            if "remun_mensal_adm" in df_remun.columns:
                # Gráfico — linha inteira
                st.plotly_chart(
                    plot_remun_by_entity(
                        df_remun, "Data_Posicao", "remun_mensal_adm",
                        entity_col="administrador", highlight_name="Solis",
                        y_title="Remuneração Total (R$/mês)",
                        title=f"Remuneração de Administração — Total por Adm. ({modo_label})",
                    ),
                    use_container_width=True,
                )

                # Ranking — linha inteira abaixo
                df_ult_adm = df_remun[df_remun["Data_Posicao"] == ultima_data]
                rank_adm = (
                    df_ult_adm.dropna(subset=["remun_mensal_adm", "administrador"])
                    .groupby("administrador")["remun_mensal_adm"].sum()
                    .sort_values(ascending=False)
                    .head(15)
                    .reset_index()
                )
                rank_adm.columns = ["Administradora", "Remuneração (R$/mês)"]
                rank_adm["Remuneração (R$/mês)"] = rank_adm["Remuneração (R$/mês)"].apply(_fmt_currency)
                st.markdown(f"**Ranking de Administradoras — {ultima_data.strftime('%b/%Y')} ({modo_label})**")
                st.dataframe(rank_adm, use_container_width=True, hide_index=True)
            else:
                st.info(f"Taxa `{taxa_adm_col}` não disponível para o cálculo.")

# ──────────────────────────────────────────────────────────────────────────────
# Aba: Inadimplência
# ──────────────────────────────────────────────────────────────────────────────

with tab_inad:
    st.markdown('<div class="section-label">Evolução da Inadimplência — Metodologia Ponderada</div>',
                unsafe_allow_html=True)
    st.caption(
        "Inadimplência calculada como `Σ(PDD) / Σ(DC ou PL) × 100` — "
        "mesmo critério do KPI da Visão Geral. "
        "Fundos sem DC > 0 são excluídos do cálculo PDD/DC."
    )

    col1, col2 = st.columns(2)
    with col1:
        if "PDD" in df.columns and "DC" in df.columns:
            df_dc_ok = df[df["DC"] > 0]
            st.plotly_chart(
                plot_inad_pondered(
                    df_dc_ok, "Data_Posicao", "PDD", "DC",
                    y_title="PDD / DC (%)",
                    title="Inadimplência Ponderada — PDD / DC (%)",
                ),
                use_container_width=True,
            )
        else:
            st.info("Colunas PDD/DC não disponíveis.")
    with col2:
        if "PDD" in df.columns and "PL_CVM" in df.columns:
            df_pl_ok = df[df["PL_CVM"] > 0]
            st.plotly_chart(
                plot_inad_pondered(
                    df_pl_ok, "Data_Posicao", "PDD", "PL_CVM",
                    y_title="PDD / PL (%)",
                    title="Inadimplência Ponderada — PDD / PL (%)",
                ),
                use_container_width=True,
            )
        else:
            st.info("Colunas PDD/PL não disponíveis.")


# ──────────────────────────────────────────────────────────────────────────────
# Aba: Subordinação
# ──────────────────────────────────────────────────────────────────────────────

with tab_sub:
    st.markdown('<div class="section-label">Evolução da Subordinação Média — Solis vs Mercado</div>',
                unsafe_allow_html=True)
    st.caption("Média simples da subordinação dos fundos — Solis vs. Mercado (excl. Solis).")

    col1, col2 = st.columns(2)
    with col1:
        if "Sub_JR" in df.columns:
            st.plotly_chart(
                plot_mean_simple(df, "Data_Posicao", "Sub_JR",
                                 y_title="Subordinação Jr (%)",
                                 title="Subordinação Júnior — Evolução Média (%)"),
                use_container_width=True,
            )
    with col2:
        if "Sub_JR_MZ" in df.columns:
            st.plotly_chart(
                plot_mean_simple(df, "Data_Posicao", "Sub_JR_MZ",
                                 y_title="Subordinação Jr+Mez (%)",
                                 title="Subordinação Jr+Mez — Evolução Média (%)"),
                use_container_width=True,
            )
