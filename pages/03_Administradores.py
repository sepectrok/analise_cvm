"""Página 3 — Agrupamento por Administrador"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import bar_ranking, histogram_taxa
from components.tables import render_entity_ranking
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("🏢", "Agrupamento por Administrador",
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
if "Sub_JR" in df_adm.columns:
    agg_dict["Sub_JR"] = "mean"
if "Sub_JR_MZ" in df_adm.columns:
    agg_dict["Sub_JR_MZ"] = "mean"

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
    wa = (df_agg["taxa_administracao"] * df_agg["n_fundos"]).sum() / df_agg["n_fundos"].sum()
    c3.metric("Taxa Adm. Ponderada (por nº fundos)", f"{wa:.3f}%")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Ranking", "Distribuição", "Remuneração Esperada", "Inadimplência", "Subordinação"]
)

with tab1:
    min_fundos = st.slider("Nº mínimo de fundos", 1, 10, 2, key="adm_min")
    df_rank = df_agg[df_agg["n_fundos"] >= min_fundos].sort_values("taxa_administracao")
    render_entity_ranking(df_rank, "administrador", "n_fundos", key="adm_rank", taxa_col_to_show="taxa_administracao")

with tab2:
    if "taxa_administracao" in df.columns:
        st.plotly_chart(histogram_taxa(df, "taxa_administracao"), use_container_width=True)
    else:
        st.info("Dados de taxa de administração não disponíveis.")

with tab3:
    st.markdown('<div class="section-label">Remuneração Esperada por Administrador</div>', unsafe_allow_html=True)
    st.caption("`((1 + taxa_administração/100)^(21/252) - 1) × PL_CVM` — Estimativa da receita mensal gerada pela taxa de administração.")

    subtab_real, subtab_imp = st.tabs(["📌 Taxa Real", "📊 Com Imputação de Média"])

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

    min_f_inad = st.slider("Nº mínimo de fundos para rankear", 1, 50, 1, key="adm_min_inad")

    subtab_dc, subtab_pl = st.tabs(["📊 PDD / DC", "📉 PDD / PL"])

    # ── Sub-tab: PDD / DC ─────────────────────────────────────────────────────
    with subtab_dc:
        st.caption(
            "**PDD / DC** — Provisão para Devedores Duvidosos sobre os Direitos Creditórios em atraso. "
            "Mede a cobertura de PDD sobre o crédito inadimplente. Fundos sem DC > 0 são excluídos."
        )
        if "taxa_inadimplencia" in df_agg.columns and df_agg["taxa_inadimplencia"].notna().any():
            df_inad_dc = (
                df_agg[df_agg["taxa_inadimplencia"].notna() & (df_agg["n_fundos"] >= min_f_inad)]
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
                df_agg[df_agg["taxa_inadimplencia_pl"].notna() & (df_agg["n_fundos"] >= min_f_inad)]
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

    min_f_sub = st.slider("Nº mínimo de fundos para rankear", 1, 50, 1, key="adm_min_sub")

    subtab_jr, subtab_jrmz = st.tabs(["Subordinação Jr", "Subordinação Jr + Mez"])

    with subtab_jr:
        st.caption("Média simples da cota Subordinada Júnior (%) por fundo, agrupada por administrador.")
        if "Sub_JR" in df_agg.columns and df_agg["Sub_JR"].notna().any():
            df_sub_jr = (
                df_agg[df_agg["Sub_JR"].notna() & (df_agg["n_fundos"] >= min_f_sub)]
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
                df_agg[df_agg["Sub_JR_MZ"].notna() & (df_agg["n_fundos"] >= min_f_sub)]
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
