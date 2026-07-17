"""Página 3 — Agrupamento por Administrador"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.colors as pc

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import bar_ranking, histogram_taxa, PALETTE, _base_layout
from components.tables import render_entity_ranking
from utils.data_loader import (
    build_df_fidc, TAXA_LABELS, TAXA_COLS, add_subordinacao_ponderada,
    CVNP_COLS, CVNP_LABELS, AGING_COLS, AGING_LABELS,
    weighted_mean, weighted_mean_by_group,
)

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("","Agrupamento por Administrador",
            "Ranking, taxas médias e concentração por entidade administradora")

df_adm = df.dropna(subset=["administrador"])
if df_adm.empty:
    st.warning("Nenhum dado disponível para administradores com os filtros aplicados.")
    st.stop()

# ── Aggregate ─────────────────────────────────────────────────────────────────
taxa_cols_avail = [c for c in TAXA_COLS if c in df_adm.columns]
agg_dict = {c: "mean" for c in taxa_cols_avail}
agg_dict["cnpj_tratado"] = "count"

if "Valor_PL" in df_adm.columns:
    agg_dict["Valor_PL"] = "sum"

if "PDD" in df_adm.columns:
    agg_dict["PDD"] = "sum"
if "DC" in df_adm.columns:
    agg_dict["DC"] = "sum"
if "PL_CVM" in df_adm.columns:
    agg_dict["PL_CVM"] = "sum"
# Tranches brutas — necessárias para calcular subordinação ponderada pós-agregação
for _t in ["SB", "MZ", "SR"]:
    if _t in df_adm.columns:
        agg_dict[_t] = "sum"

# CVNP — crédito vencido não pago
for _c in ["CVNP"] + CVNP_COLS:
    if _c in df_adm.columns:
        agg_dict[_c] = "sum"

# Aging — envelhecimento da carteira
for _c in ["Aging"] + AGING_COLS:
    if _c in df_adm.columns:
        agg_dict[_c] = "sum"

if "taxa_administracao" in df_adm.columns and "Valor_PL" in df_adm.columns:
    df_adm = df_adm.copy()
    # Versão com imputação (usa média do administrador quando taxa ausente)
    df_adm["remun_esperada_adm"] = (((1 + df_adm["taxa_administracao"] / 100) ** (21 / 252)) - 1) * df_adm["Valor_PL"]
    agg_dict["remun_esperada_adm"] = "sum"
    # Versão somente taxa real (exclui fundos sem taxa explícita no regulamento)
    if "taxa_administracao_raw" in df_adm.columns:
        df_adm["remun_esperada_adm_real"] = np.where(
            df_adm["taxa_administracao_raw"].notna(),
            (((1 + df_adm["taxa_administracao_raw"] / 100) ** (21 / 252)) - 1) * df_adm["Valor_PL"],
            np.nan,
        )
        agg_dict["remun_esperada_adm_real"] = "sum"

df_agg = (
    df_adm.groupby("administrador")
    .agg(agg_dict)
    .reset_index()
    .rename(columns={"cnpj_tratado": "n_fundos"})
    .sort_values("n_fundos", ascending=False)
)

# Substituir médias simples de taxas por médias ponderadas pelo PL_CVM
for _tc in taxa_cols_avail:
    _pond = weighted_mean_by_group(df_adm, "administrador", _tc)
    if not _pond.empty:
        df_agg[_tc] = df_agg["administrador"].map(_pond)

# Subordinação ponderada: Σ(SB) / Σ(SB+MZ+SR) por administrador
df_agg = add_subordinacao_ponderada(df_agg, df_adm, groupby_col="administrador")

# Calcula inadimplência ponderada realista: soma(PDD) / soma(DC ou PL)
if "PDD" in df_agg.columns:
    if "DC" in df_agg.columns:
        df_agg["taxa_inadimplencia"] = np.where(
            df_agg["DC"] > 0,
            (df_agg["PDD"] / df_agg["DC"] * 100).clip(upper=100),
            np.nan,
        )
    if "PL_CVM" in df_agg.columns:
        df_agg["taxa_inadimplencia_pl"] = np.where(
            df_agg["PL_CVM"] > 0,
            (df_agg["PDD"] / df_agg["PL_CVM"] * 100).clip(upper=100),
            np.nan,
        )

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Administradores", df_agg["administrador"].nunique())
c2.metric("Total de FIDCs", int(df_agg["n_fundos"].sum()))
if "taxa_administracao" in df_agg.columns:
    # Ponderado pelo PL total de cada administrador
    wa = weighted_mean(df_adm, "taxa_administracao")
    c3.metric("Taxa Adm. Pond. por PL", f"{wa:.3f}%")

st.markdown("---")

col_min_global, _ = st.columns([1, 2])
with col_min_global:
    min_fundos = st.slider("Nº mínimo de fundos sob Administração", 1, 25, 10, key="adm_min_global")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab_cvnp, tab_aging = st.tabs(
    ["Ranking", "Distribuição", "Remuneração Esperada", "Inadimplência", "Subordinação", "CVNP", "Aging"]
)

with tab1:
    df_rank = df_agg[df_agg["n_fundos"] >= min_fundos].sort_values("taxa_administracao")
    render_entity_ranking(df_rank, "administrador", "n_fundos", key="adm_rank", taxa_col_to_show="taxa_administracao")

with tab2:
    if "taxa_administracao" in df.columns:
        # Filtrar apenas fundos dos admins que atendem ao critério de min_fundos
        adm_validos = df_agg[df_agg["n_fundos"] >= min_fundos]["administrador"]
        df_dist = df_adm[df_adm["administrador"].isin(adm_validos)]
        st.plotly_chart(histogram_taxa(df_dist, "taxa_administracao"), use_container_width=True)
    else:
        st.info("Dados de taxa de administração não disponíveis.")

with tab3:
    st.markdown('<div class="section-label">Remuneração Esperada por Administrador</div>', unsafe_allow_html=True)
    st.caption("`((1 + taxa_administração/100)^(21/252) - 1) × PL_CVM` — Estimativa da receita mensal gerada pela taxa de administração.")

    subtab_real, subtab_imp = st.tabs(["Taxa Real", "Com Imputação de Média"])

    # ── Sub-tab: Taxa Real ────────────────────────────────────────────────────
    with subtab_real:
        st.caption(
            "Considera apenas fundos que possuem **taxa de administração explícita** no regulamento. "
            "Fundos sem taxa informada são excluídos deste cálculo."
        )
        if "remun_esperada_adm_real" in df_agg.columns and df_agg["remun_esperada_adm_real"].notna().any():
            df_real = (
                df_agg[df_agg["remun_esperada_adm_real"].notna() & (df_agg["n_fundos"] >= min_fundos)]
                .sort_values("remun_esperada_adm_real")
            )
            if not df_real.empty:
                total_real = df_real["remun_esperada_adm_real"].sum()
                st.metric(
                    "Remuneração Total (Taxa Real)",
                    f"R$ {total_real/1e6:.2f}M" if total_real >= 1e6 else f"R$ {total_real:,.0f}",
                )
                st.plotly_chart(
                    bar_ranking(
                        df_real.rename(columns={"remun_esperada_adm_real": "_val", "administrador": "_name"}),
                        "_val", "_name",
                        title="Remuneração Esperada — Somente Taxa Real (R$/Mês)",
                        top_n=20, highlight_name="Solis", height=520,
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_real[["administrador", "n_fundos", "remun_esperada_adm_real"]]
                    .sort_values("remun_esperada_adm_real", ascending=False)
                    .rename(columns={
                        "administrador": "Administrador",
                        "n_fundos": "Nº Fundos",
                        "remun_esperada_adm_real": "Remuneração Mensal Estimada (R$)",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"Remuneração Mensal Estimada (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
                )
            else:
                st.info("Nenhum administrador com taxa real disponível para os filtros aplicados.")
        else:
            st.info("Dados de taxa de administração real não disponíveis para o cálculo.")

    # ── Sub-tab: Com Imputação de Média ───────────────────────────────────────
    with subtab_imp:
        st.caption(
            "Quando um fundo não possui taxa de administração no regulamento, utiliza-se a **média dos demais fundos do mesmo administrador**. "
            "Inclui todos os fundos com PL disponível."
        )
        if "remun_esperada_adm" in df_agg.columns:
            df_rank_remun = df_agg[df_agg["n_fundos"] >= min_fundos].sort_values("remun_esperada_adm")
            if not df_rank_remun.empty:
                total_imp = df_rank_remun["remun_esperada_adm"].sum()
                st.metric(
                    "Remuneração Total (Com Imputação)",
                    f"R$ {total_imp/1e6:.2f}M" if total_imp >= 1e6 else f"R$ {total_imp:,.0f}",
                )
                st.plotly_chart(
                    bar_ranking(
                        df_rank_remun.rename(columns={"remun_esperada_adm": "_val", "administrador": "_name"}),
                        "_val", "_name",
                        title="Remuneração Esperada — Com Imputação de Média (R$/Mês)",
                        top_n=20, highlight_name="Solis", height=520,
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_rank_remun[["administrador", "n_fundos", "remun_esperada_adm"]]
                    .sort_values("remun_esperada_adm", ascending=False)
                    .rename(columns={
                        "administrador": "Administrador",
                        "n_fundos": "Nº Fundos",
                        "remun_esperada_adm": "Remuneração Mensal Estimada (R$)",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"Remuneração Mensal Estimada (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
                )
            else:
                st.info("Nenhum dado disponível para os filtros aplicados.")
        else:
            st.info("Dados de PL Médio ou Taxa de Administração não disponíveis para o cálculo.")

with tab4:
    st.markdown('<div class="section-label">Inadimplência Média por Administrador</div>', unsafe_allow_html=True)

    subtab_dc, subtab_pl = st.tabs(["PDD / DC", "PDD / PL"])

    # ── Sub-tab: PDD / DC ─────────────────────────────────────────────────────
    with subtab_dc:
        st.caption(
            "**PDD / DC** — Provisão para Devedores Duvidosos sobre os Direitos Creditórios em atraso. "
            "Mede a cobertura de PDD sobre o crédito inadimplente. Fundos sem DC > 0 são excluídos."
        )
        if "taxa_inadimplencia" in df_agg.columns and df_agg["taxa_inadimplencia"].notna().any():
            df_inad_dc = (
                df_agg[df_agg["taxa_inadimplencia"].notna() & (df_agg["n_fundos"] >= min_fundos)]
                .sort_values("taxa_inadimplencia", ascending=True)
            )
            st.plotly_chart(
                bar_ranking(
                    df_inad_dc.rename(columns={"taxa_inadimplencia": "_val", "administrador": "_name"}),
                    "_val", "_name",
                    title="Inadimplência por Administrador — PDD / DC (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_inad_dc[["administrador", "n_fundos", "taxa_inadimplencia"]]
                .sort_values("taxa_inadimplencia", ascending=False)
                .rename(columns={"administrador": "Administrador", "n_fundos": "Nº Fundos", "taxa_inadimplencia": "PDD / DC (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"PDD / DC (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de PDD/DC não disponíveis para os administradores filtrados.")

    # ── Sub-tab: PDD / PL ─────────────────────────────────────────────────────
    with subtab_pl:
        st.caption(
            "**PDD / PL** — Provisão para Devedores Duvidosos sobre o Patrimônio Líquido total do fundo. "
            "Mede o impacto da inadimplência relativo ao tamanho do fundo. Inclui todos os fundos com PL > 0."
        )
        if "taxa_inadimplencia_pl" in df_agg.columns and df_agg["taxa_inadimplencia_pl"].notna().any():
            df_inad_pl = (
                df_agg[df_agg["taxa_inadimplencia_pl"].notna() & (df_agg["n_fundos"] >= min_fundos)]
                .sort_values("taxa_inadimplencia_pl", ascending=True)
            )
            st.plotly_chart(
                bar_ranking(
                    df_inad_pl.rename(columns={"taxa_inadimplencia_pl": "_val", "administrador": "_name"}),
                    "_val", "_name",
                    title="Inadimplência por Administrador — PDD / PL (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_inad_pl[["administrador", "n_fundos", "taxa_inadimplencia_pl"]]
                .sort_values("taxa_inadimplencia_pl", ascending=False)
                .rename(columns={"administrador": "Administrador", "n_fundos": "Nº Fundos", "taxa_inadimplencia_pl": "PDD / PL (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"PDD / PL (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de PDD/PL não disponíveis para os administradores filtrados.")

with tab5:
    st.markdown('<div class="section-label">Subordinação Média por Administrador</div>', unsafe_allow_html=True)

    subtab_jr, subtab_jrmz = st.tabs(["Subordinação Jr", "Subordinação Jr + Mez"])

    with subtab_jr:
        st.caption("Média simples da cota Subordinada Júnior (%) por fundo, agrupada por administrador.")
        if "Sub_JR" in df_agg.columns and df_agg["Sub_JR"].notna().any():
            df_sub_jr = (
                df_agg[df_agg["Sub_JR"].notna() & (df_agg["n_fundos"] >= min_fundos)]
                .sort_values("Sub_JR", ascending=False)
            )
            st.plotly_chart(
                bar_ranking(
                    df_sub_jr.rename(columns={"Sub_JR": "_val", "administrador": "_name"}),
                    "_val", "_name",
                    title="Subordinação Jr Média por Administrador (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_sub_jr[["administrador", "n_fundos", "Sub_JR"]]
                .sort_values("Sub_JR", ascending=False)
                .rename(columns={"administrador": "Administrador", "n_fundos": "Nº Fundos", "Sub_JR": "Subordinação Jr (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"Subordinação Jr (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de Subordinação Jr não disponíveis para os administradores filtrados.")

    with subtab_jrmz:
        st.caption("Média simples da cota Subordinada Júnior + Mezanino (%) por fundo, agrupada por administrador.")
        if "Sub_JR_MZ" in df_agg.columns and df_agg["Sub_JR_MZ"].notna().any():
            df_sub_jrmz = (
                df_agg[df_agg["Sub_JR_MZ"].notna() & (df_agg["n_fundos"] >= min_fundos)]
                .sort_values("Sub_JR_MZ", ascending=False)
            )
            st.plotly_chart(
                bar_ranking(
                    df_sub_jrmz.rename(columns={"Sub_JR_MZ": "_val", "administrador": "_name"}),
                    "_val", "_name",
                    title="Subordinação Jr + Mez Média por Administrador (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_sub_jrmz[["administrador", "n_fundos", "Sub_JR_MZ"]]
                .sort_values("Sub_JR_MZ", ascending=False)
                .rename(columns={"administrador": "Administrador", "n_fundos": "Nº Fundos", "Sub_JR_MZ": "Subordinação Jr+Mez (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"Subordinação Jr+Mez (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de Subordinação Jr+Mez não disponíveis para os administradores filtrados.")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de paleta — degradê blue → orange → amber (igual Taxas por Segmento)
# ─────────────────────────────────────────────────────────────────────────────
def _make_grad_palette(n_faixas: int, alpha: float = 0.90) -> list[str]:
    """Gera n cores interpoladas blue→orange→amber com opacidade alpha."""
    hex_list = pc.sample_colorscale(
        [[0, PALETTE["blue"]], [0.5, PALETTE["orange"]], [1, PALETTE["amber"]]],
        [i / max(n_faixas - 1, 1) for i in range(n_faixas)],
    )
    result = []
    for h in hex_list:
        if h.startswith("#"):
            r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        else:
            parts = h.replace("rgb(", "").replace(")", "").split(",")
            r, g, b = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
        result.append(f"rgba({r},{g},{b},{alpha})")
    return result


def _stacked_dist_chart(
    df_top: pd.DataFrame,
    entity_col: str,
    faixas_cols: list[str],
    faixas_labels: dict,
    total_col: str,
    title: str,
    height: int,
) -> go.Figure:
    """Gráfico de barras empilhadas 100% por faixa, para o top de entidades."""
    n = len(faixas_cols)
    palette = _make_grad_palette(n, alpha=0.90)
    entities_order = df_top.sort_values(total_col)[entity_col].tolist()

    fig = go.Figure()
    for i, col in enumerate(faixas_cols):
        label = faixas_labels.get(col, col)
        cor   = palette[i]
        vals  = [
            float(df_top.loc[df_top[entity_col] == ent, f"{col}_pct"].iloc[0])
            if not df_top[df_top[entity_col] == ent].empty else 0.0
            for ent in entities_order
        ]
        fig.add_trace(go.Bar(
            name=label,
            y=entities_order,
            x=vals,
            orientation="h",
            marker=dict(color=cor, line=dict(width=0.3, color="rgba(255,255,255,0.08)")),
            text=[f"{v:.0f}%" if v >= 8 else "" for v in vals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=8, color="#FFFFFF"),
            hovertemplate=f"<b>{label}</b><br>%{{y}}<br>%{{x:.1f}}%<extra></extra>",
        ))

    _lay = _base_layout(title, height)
    _lay["barmode"] = "stack"
    _lay["bargap"]  = 0.22
    _lay["xaxis"].update({"ticksuffix": "%", "range": [0, 105], "title": "% do Total"})
    _lay["margin"] = dict(l=16, r=170, t=56, b=16)  # r=170 acomoda legenda vertical à direita
    _lay["legend"] = {
        "orientation": "v",
        "yanchor": "middle", "y": 0.5,
        "xanchor": "left",  "x": 1.01,
        "font": dict(size=9, color="#C8D4E0"),
        "bgcolor": "rgba(16,36,50,0.80)",
        "bordercolor": "rgba(137,155,183,0.20)",
        "borderwidth": 1,
        "itemwidth": 30,
        "tracegroupgap": 2,
    }
    fig.update_layout(**_lay)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Tab: CVNP — Crédito Vencido Não Pago
# ─────────────────────────────────────────────────────────────────────────────
with tab_cvnp:
    cvnp_cols_presentes = [c for c in CVNP_COLS if c in df_agg.columns]

    if "CVNP" not in df_agg.columns or not cvnp_cols_presentes:
        st.info("Dados de CVNP não disponíveis na base atual.")
    else:
        df_cvnp_filt = df_agg[df_agg["n_fundos"] >= min_fundos].copy()
        df_cvnp_filt = df_cvnp_filt[df_cvnp_filt["CVNP"] > 0].copy()

        subtab_cvnp_rank, subtab_cvnp_dist = st.tabs(["Ranking de CVNP", "Distribuição por Faixa"])

        with subtab_cvnp_rank:
            st.markdown('<div class="section-label">Ranking de CVNP por Administradora</div>', unsafe_allow_html=True)
            st.caption(
                "Crédito Vencido Não Pago total (soma dos fundos) por administradora. "
                "Solis destacada em dourado. Filtro de mínimo de fundos global aplicável."
            )
            if df_cvnp_filt.empty:
                st.info("Nenhum dado de CVNP para os filtros aplicados.")
            else:
                st.plotly_chart(
                    bar_ranking(
                        df_cvnp_filt.rename(columns={"CVNP": "_val", "administrador": "_name"}),
                        "_val", "_name",
                        title="Ranking de CVNP por Administradora (R$)",
                        top_n=20, highlight_name="Solis",
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_cvnp_filt[["administrador", "n_fundos", "CVNP"]]
                    .sort_values("CVNP", ascending=False)
                    .rename(columns={"administrador": "Administradora", "n_fundos": "Nº Fundos", "CVNP": "CVNP Total (R$)"}),
                    use_container_width=True, hide_index=True,
                    column_config={"CVNP Total (R$)": st.column_config.NumberColumn(format="R$ %,.0f")},
                )

        with subtab_cvnp_dist:
            st.markdown('<div class="section-label">Distribuição de CVNP por Faixa de Atraso</div>', unsafe_allow_html=True)
            st.caption(
                "Percentual do CVNP em cada faixa de atraso, para as top administradoras por volume. "
                "Degradê **azul → laranja → âmbar** por faixa de vencimento crescente."
            )
            if df_cvnp_filt.empty:
                st.info("Nenhum dado de CVNP para os filtros aplicados.")
            else:
                top_n_cvnp = st.slider("Top N Administradoras por CVNP", 5, 20, 10, key="adm_cvnp_topn")
                df_cvnp_top = df_cvnp_filt.nlargest(top_n_cvnp, "CVNP").copy()
                for c in cvnp_cols_presentes:
                    df_cvnp_top[f"{c}_pct"] = (df_cvnp_top[c] / df_cvnp_top["CVNP"] * 100).fillna(0)

                fig_cvnp = _stacked_dist_chart(
                    df_top=df_cvnp_top,
                    entity_col="administrador",
                    faixas_cols=cvnp_cols_presentes,
                    faixas_labels=CVNP_LABELS,
                    total_col="CVNP",
                    title="Distribuição de CVNP por Faixa — Top Administradoras (%)",
                    height=max(400, top_n_cvnp * 38 + 120),
                )
                # Garante legenda vertical à direita independentemente do estado do slider
                fig_cvnp.update_layout(legend=dict(
                    orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.01,
                    font=dict(size=9, color="#C8D4E0"),
                    bgcolor="rgba(16,36,50,0.80)",
                    bordercolor="rgba(137,155,183,0.20)",
                    borderwidth=1,
                ))
                st.plotly_chart(fig_cvnp, use_container_width=True, key=f"adm_cvnp_dist_{top_n_cvnp}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab: Aging — Envelhecimento da Carteira
# ─────────────────────────────────────────────────────────────────────────────
with tab_aging:
    aging_cols_presentes = [c for c in AGING_COLS if c in df_agg.columns]

    if "Aging" not in df_agg.columns or not aging_cols_presentes:
        st.info("Dados de Aging não disponíveis na base atual.")
    else:
        df_ag_filt = df_agg[df_agg["n_fundos"] >= min_fundos].copy()
        df_ag_filt = df_ag_filt[df_ag_filt["Aging"] > 0].copy()

        subtab_ag_rank, subtab_ag_dist = st.tabs(["Ranking de Aging", "Distribuição por Faixa"])

        with subtab_ag_rank:
            st.markdown('<div class="section-label">Ranking de Aging por Administradora</div>', unsafe_allow_html=True)
            st.caption(
                "Volume total de Aging (envelhecimento da carteira de recebíveis) por administradora. "
                "Solis destacada em dourado. Filtro de mínimo de fundos global aplicável."
            )
            if df_ag_filt.empty:
                st.info("Nenhum dado de Aging para os filtros aplicados.")
            else:
                st.plotly_chart(
                    bar_ranking(
                        df_ag_filt.rename(columns={"Aging": "_val", "administrador": "_name"}),
                        "_val", "_name",
                        title="Ranking de Aging por Administradora (R$)",
                        top_n=20, highlight_name="Solis",
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_ag_filt[["administrador", "n_fundos", "Aging"]]
                    .sort_values("Aging", ascending=False)
                    .rename(columns={"administrador": "Administradora", "n_fundos": "Nº Fundos", "Aging": "Aging Total (R$)"}),
                    use_container_width=True, hide_index=True,
                    column_config={"Aging Total (R$)": st.column_config.NumberColumn(format="R$ %,.0f")},
                )

        with subtab_ag_dist:
            st.markdown('<div class="section-label">Distribuição de Aging por Faixa de Prazo</div>', unsafe_allow_html=True)
            st.caption(
                "Percentual do Aging em cada faixa de prazo, para as top administradoras por volume. "
                "Degradê **azul → laranja → âmbar** por faixa de prazo crescente."
            )
            if df_ag_filt.empty:
                st.info("Nenhum dado de Aging para os filtros aplicados.")
            else:
                top_n_ag = st.slider("Top N Administradoras por Aging", 5, 20, 10, key="adm_aging_topn")
                df_ag_top = df_ag_filt.nlargest(top_n_ag, "Aging").copy()
                for c in aging_cols_presentes:
                    df_ag_top[f"{c}_pct"] = (df_ag_top[c] / df_ag_top["Aging"] * 100).fillna(0)

                fig_ag = _stacked_dist_chart(
                    df_top=df_ag_top,
                    entity_col="administrador",
                    faixas_cols=aging_cols_presentes,
                    faixas_labels=AGING_LABELS,
                    total_col="Aging",
                    title="Distribuição de Aging por Faixa — Top Administradoras (%)",
                    height=max(400, top_n_ag * 38 + 120),
                )
                # Garante legenda vertical à direita independentemente do estado do slider
                fig_ag.update_layout(legend=dict(
                    orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.01,
                    font=dict(size=9, color="#C8D4E0"),
                    bgcolor="rgba(16,36,50,0.80)",
                    bordercolor="rgba(137,155,183,0.20)",
                    borderwidth=1,
                ))
                st.plotly_chart(fig_ag, use_container_width=True, key=f"adm_aging_dist_{top_n_ag}")
