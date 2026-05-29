"""Página 4 — Agrupamento por Gestor"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header, kpi_card, insight_card
from components.charts import bar_ranking, heatmap_entity_taxa, histogram_taxa
from components.tables import render_entity_ranking
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS, CVNP_COLS, CVNP_LABELS
from utils.formatters import fmt_pct

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("👔", "Agrupamento por Gestor",
            "Concentração, clusterização e benchmark de taxas de gestão")

df_ges = df.dropna(subset=["gestor"])
if df_ges.empty:
    st.warning("Nenhum dado disponível para gestores com os filtros aplicados.")
    st.stop()

taxa_cols_avail = [c for c in TAXA_COLS if c in df_ges.columns]
agg_dict = {c: "mean" for c in taxa_cols_avail}
agg_dict["cnpj_tratado"] = "count"

if "Valor_PL" in df_ges.columns:
    agg_dict["Valor_PL"] = "sum"

if "PDD" in df_ges.columns:
    agg_dict["PDD"] = "sum"
if "DC" in df_ges.columns:
    agg_dict["DC"] = "sum"
if "PL_CVM" in df_ges.columns:
    agg_dict["PL_CVM"] = "sum"
if "Sub_JR" in df_ges.columns:
    agg_dict["Sub_JR"] = "mean"
if "Sub_JR_MZ" in df_ges.columns:
    agg_dict["Sub_JR_MZ"] = "mean"

# CVNP — aging de vencidos
for _c in ["CVNP"] + CVNP_COLS:
    if _c in df_ges.columns:
        agg_dict[_c] = "sum"

if "taxa_gestao" in df_ges.columns and "Valor_PL" in df_ges.columns:
    df_ges = df_ges.copy()
    # Versão com imputação (usa média do gestor quando taxa ausente)
    df_ges["remun_esperada"] = (((1 + df_ges["taxa_gestao"] / 100) ** (21 / 252)) - 1) * df_ges["Valor_PL"]
    agg_dict["remun_esperada"] = "sum"
    # Versão somente taxa real (exclui fundos sem taxa explícita no regulamento)
    if "taxa_gestao_raw" in df_ges.columns:
        df_ges["remun_esperada_real"] = np.where(
            df_ges["taxa_gestao_raw"].notna(),
            (((1 + df_ges["taxa_gestao_raw"] / 100) ** (21 / 252)) - 1) * df_ges["Valor_PL"],
            np.nan,
        )
        agg_dict["remun_esperada_real"] = "sum"

df_agg = (
    df_ges.groupby("gestor")
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

if not df_agg.empty and "taxa_gestao" in df_agg.columns:
    max_idx = df_agg["taxa_gestao"].idxmax()
    if pd.notna(max_idx):
        df_agg = df_agg.drop(max_idx)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Gestores", df_agg["gestor"].nunique())
c2.metric("Total FIDCs", int(df_agg["n_fundos"].sum()))
if "taxa_gestao" in df_agg.columns:
    wa = (df_agg["taxa_gestao"].fillna(0) * df_agg["n_fundos"]).sum() / df_agg["n_fundos"].sum()
    c3.metric("Taxa Gestão Pond.", f"{wa:.3f}%")
    top_ges = df_agg.dropna(subset=["taxa_gestao"]).nlargest(1, "taxa_gestao").iloc[0]
    c4.metric("Maior Taxa Gestão", fmt_pct(top_ges["taxa_gestao"]),
              delta=f"↑ {top_ges['gestor'][:25]}", delta_color="inverse")

st.markdown("---")

# O detalhamento completo por fundo está exibido na tabela visual ao final da página.

tab1, tab2, tab3, tab4, tab5, tab_aging = st.tabs(
    ["Ranking", "Distribuição", "Remuneração Esperada", "Inadimplência", "Subordinação", "Aging de Vencidos"]
)

with tab1:
    col_opt, col_min = st.columns([2, 1])
    with col_opt:
        rank_metric = st.radio("Ordenar ranking por:", ["Taxa de Gestão", "AuM (Patrimônio Líquido)"], horizontal=True)
    with col_min:
        min_f = st.slider("Nº mínimo de fundos", 1, 10, 2, key="ges_min")

    if rank_metric == "Taxa de Gestão":
        df_rank = df_agg[df_agg["n_fundos"] >= min_f].sort_values("taxa_gestao")
        if "taxa_gestao" in df_rank.columns:
            st.plotly_chart(bar_ranking(df_rank.rename(columns={"taxa_gestao": "_val", "gestor": "_name"}),
                                        "_val", "_name", title="Ranking de Taxa de Gestão",
                                        top_n=20, highlight_name="Solis", height=500),
                            use_container_width=True)
        render_entity_ranking(df_rank, "gestor", "n_fundos", key="ges_rank", taxa_col_to_show="taxa_gestao")
    else:
        if "Valor_PL" in df_agg.columns:
            df_rank = df_agg[df_agg["n_fundos"] >= min_f].sort_values("Valor_PL")
            st.plotly_chart(bar_ranking(df_rank.rename(columns={"Valor_PL": "_val", "gestor": "_name"}),
                                        "_val", "_name", title="Ranking de AuM",
                                        top_n=20, highlight_name="Solis", height=500, is_percent=False, is_currency=True),
                            use_container_width=True)
            st.dataframe(
                df_rank[["gestor", "n_fundos", "Valor_PL"]].sort_values("Valor_PL", ascending=False).rename(columns={
                    "gestor": "Gestor", "n_fundos": "Nº Fundos", "Valor_PL": "AuM (R$)"
                }),
                use_container_width=True, hide_index=True,
                column_config={"AuM (R$)": st.column_config.NumberColumn(format="R$ %.2f")}
            )

with tab2:
    if "taxa_gestao" in df.columns:
        st.plotly_chart(histogram_taxa(df, "taxa_gestao"), use_container_width=True)
    else:
        st.info("Dados de taxa de gestão não disponíveis.")

with tab3:
    st.markdown('<div class="section-label">Remuneração Esperada por Gestor</div>', unsafe_allow_html=True)
    st.caption("`((1 + taxa_gestão/100)^(21/252) - 1) × PL_CVM` — Estimativa da receita mensal gerada pela taxa de gestão.")

    subtab_real, subtab_imp = st.tabs(["📌 Taxa Real", "📊 Com Imputação de Média"])

    # ── Sub-tab: Taxa Real (somente fundos com taxa explícita no regulamento) ──
    with subtab_real:
        st.caption(
            "Considera apenas fundos que possuem **taxa de gestão explícita** no regulamento. "
            "Fundos sem taxa informada são excluídos deste cálculo."
        )
        if "remun_esperada_real" in df_agg.columns and df_agg["remun_esperada_real"].notna().any():
            df_real = (
                df_agg[df_agg["remun_esperada_real"].notna() & (df_agg["n_fundos"] >= min_f)]
                .sort_values("remun_esperada_real")
            )
            if not df_real.empty:
                # KPI total
                total_real = df_real["remun_esperada_real"].sum()
                st.metric(
                    "Remuneração Total (Taxa Real)",
                    f"R$ {total_real/1e6:.2f}M" if total_real >= 1e6 else f"R$ {total_real:,.0f}",
                )
                st.plotly_chart(
                    bar_ranking(
                        df_real.rename(columns={"remun_esperada_real": "_val", "gestor": "_name"}),
                        "_val", "_name",
                        title="Remuneração Esperada — Somente Taxa Real (R$/Mês)",
                        top_n=20, highlight_name="Solis", height=520,
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_real[["gestor", "n_fundos", "remun_esperada_real"]]
                    .sort_values("remun_esperada_real", ascending=False)
                    .rename(columns={
                        "gestor": "Gestor",
                        "n_fundos": "Nº Fundos",
                        "remun_esperada_real": "Remuneração Mensal Estimada (R$)",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"Remuneração Mensal Estimada (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
                )
            else:
                st.info("Nenhum gestor com taxa real disponível para os filtros aplicados.")
        else:
            st.info("Dados de taxa de gestão real não disponíveis para o cálculo.")

    # ── Sub-tab: Com Imputação de Média (comportamento original) ──────────────
    with subtab_imp:
        st.caption(
            "Quando um fundo não possui taxa de gestão no regulamento, utiliza-se a **média dos demais fundos do mesmo gestor**. "
            "Inclui todos os fundos com PL disponível."
        )
        if "remun_esperada" in df_agg.columns:
            df_rank_remun = df_agg[df_agg["n_fundos"] >= min_f].sort_values("remun_esperada")
            if not df_rank_remun.empty:
                total_imp = df_rank_remun["remun_esperada"].sum()
                st.metric(
                    "Remuneração Total (Com Imputação)",
                    f"R$ {total_imp/1e6:.2f}M" if total_imp >= 1e6 else f"R$ {total_imp:,.0f}",
                )
                st.plotly_chart(
                    bar_ranking(
                        df_rank_remun.rename(columns={"remun_esperada": "_val", "gestor": "_name"}),
                        "_val", "_name",
                        title="Remuneração Esperada — Com Imputação de Média (R$/Mês)",
                        top_n=20, highlight_name="Solis", height=520,
                        is_percent=False, is_currency=True,
                    ),
                    use_container_width=True,
                )
                st.dataframe(
                    df_rank_remun[["gestor", "n_fundos", "remun_esperada"]]
                    .sort_values("remun_esperada", ascending=False)
                    .rename(columns={
                        "gestor": "Gestor",
                        "n_fundos": "Nº Fundos",
                        "remun_esperada": "Remuneração Mensal Estimada (R$)",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"Remuneração Mensal Estimada (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
                )
            else:
                st.info("Nenhum dado disponível para os filtros aplicados.")
        else:
            st.info("Dados de PL Médio ou Taxa de Gestão não disponíveis para o cálculo.")

with tab4:
    st.markdown('<div class="section-label">Inadimplência Média por Gestor</div>', unsafe_allow_html=True)

    min_f_inad = st.slider("Nº mínimo de fundos sob gestão", 1, 50, 1, key="ges_min_inad")

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
                    df_inad_dc.rename(columns={"taxa_inadimplencia": "_val", "gestor": "_name"}),
                    "_val", "_name",
                    title="Inadimplência por Gestor — PDD / DC (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_inad_dc[["gestor", "n_fundos", "taxa_inadimplencia"]]
                .sort_values("taxa_inadimplencia", ascending=False)
                .rename(columns={"gestor": "Gestor", "n_fundos": "Nº Fundos", "taxa_inadimplencia": "PDD / DC (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"PDD / DC (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de PDD/DC não disponíveis para os gestores filtrados.")

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
                    df_inad_pl.rename(columns={"taxa_inadimplencia_pl": "_val", "gestor": "_name"}),
                    "_val", "_name",
                    title="Inadimplência por Gestor — PDD / PL (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_inad_pl[["gestor", "n_fundos", "taxa_inadimplencia_pl"]]
                .sort_values("taxa_inadimplencia_pl", ascending=False)
                .rename(columns={"gestor": "Gestor", "n_fundos": "Nº Fundos", "taxa_inadimplencia_pl": "PDD / PL (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"PDD / PL (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de PDD/PL não disponíveis para os gestores filtrados.")

with tab5:
    st.markdown('<div class="section-label">Subordinação Média por Gestor</div>', unsafe_allow_html=True)

    min_f_sub = st.slider("Nº mínimo de fundos para rankear", 1, 50, 1, key="ges_min_sub")

    subtab_jr, subtab_jrmz = st.tabs(["Subordinação Jr", "Subordinação Jr + Mez"])

    with subtab_jr:
        st.caption("Média simples da cota Subordinada Júnior (%) por fundo, agrupada por gestor.")
        if "Sub_JR" in df_agg.columns and df_agg["Sub_JR"].notna().any():
            df_sub_jr = (
                df_agg[df_agg["Sub_JR"].notna() & (df_agg["n_fundos"] >= min_f_sub)]
                .sort_values("Sub_JR", ascending=False)
            )
            st.plotly_chart(
                bar_ranking(
                    df_sub_jr.rename(columns={"Sub_JR": "_val", "gestor": "_name"}),
                    "_val", "_name",
                    title="Subordinação Jr Média por Gestor (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_sub_jr[["gestor", "n_fundos", "Sub_JR"]]
                .sort_values("Sub_JR", ascending=False)
                .rename(columns={"gestor": "Gestor", "n_fundos": "Nº Fundos", "Sub_JR": "Subordinação Jr (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"Subordinação Jr (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de Subordinação Jr não disponíveis para os gestores filtrados.")

    with subtab_jrmz:
        st.caption("Média simples da cota Subordinada Júnior + Mezanino (%) por fundo, agrupada por gestor.")
        if "Sub_JR_MZ" in df_agg.columns and df_agg["Sub_JR_MZ"].notna().any():
            df_sub_jrmz = (
                df_agg[df_agg["Sub_JR_MZ"].notna() & (df_agg["n_fundos"] >= min_f_sub)]
                .sort_values("Sub_JR_MZ", ascending=False)
            )
            st.plotly_chart(
                bar_ranking(
                    df_sub_jrmz.rename(columns={"Sub_JR_MZ": "_val", "gestor": "_name"}),
                    "_val", "_name",
                    title="Subordinação Jr + Mez Média por Gestor (%)",
                    top_n=25, highlight_name="Solis", height=600,
                ),
                use_container_width=True,
            )
            st.dataframe(
                df_sub_jrmz[["gestor", "n_fundos", "Sub_JR_MZ"]]
                .sort_values("Sub_JR_MZ", ascending=False)
                .rename(columns={"gestor": "Gestor", "n_fundos": "Nº Fundos", "Sub_JR_MZ": "Subordinação Jr+Mez (%)"}),
                use_container_width=True, hide_index=True,
                column_config={"Subordinação Jr+Mez (%)": st.column_config.NumberColumn(format="%.2f%%")},
            )
        else:
            st.info("Dados de Subordinação Jr+Mez não disponíveis para os gestores filtrados.")

st.markdown("---")

st.markdown('<div class="section-label">📋 Tabela de Remuneração e Inadimplência Detalhada por Fundo</div>', unsafe_allow_html=True)
st.caption("Detalhamento completo por fundo e gestor contendo patrimônio líquido, taxas de gestão, remuneração estimada e inadimplência.")

# Criar DataFrame formatado para visualização e download
df_down = df_ges.copy()

# Definir colunas amigáveis
cols_map = {
    "gestor": "Gestor",
    "nome_fundo": "Fundo",
    "cnpj_tratado": "CNPJ",
    "Valor_PL": "Patrimônio Líquido (PL)",
    "taxa_gestao_raw": "Taxa de Gestão Real (% a.a.)",
    "taxa_gestao": "Taxa de Gestão com Imputação (% a.a.)",
    "remun_esperada_real": "Remuneração Estimada (Real)",
    "remun_esperada": "Remuneração Estimada (Imputada)",
    "PDD": "PDD",
    "DC": "DC",
    "PL_CVM": "PL Inadimplência (PL_CVM)",
    "taxa_inadimplencia": "Inadimplência PDD/DC (%)",
    "taxa_inadimplencia_pl": "Inadimplência PDD/PL (%)",
    "Sub_JR": "Subordinação Jr (%)",
    "Sub_JR_MZ": "Subordinação Jr+Mez (%)"
}

# Filtrar colunas que realmente existem no DataFrame
existing_cols = [c for c in cols_map.keys() if c in df_down.columns]
df_down_filtered = df_down[existing_cols].rename(columns=cols_map)

# Campo de Busca
search_query = st.text_input("🔍 Busca na tabela detalhada", key="gestores_detalhada_search", placeholder="Buscar por gestor, fundo ou CNPJ...")
if search_query:
    mask = df_down_filtered.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
    df_down_filtered = df_down_filtered[mask]

st.markdown(f"<small style='color:var(--text-muted)'>{len(df_down_filtered)} registros encontrados</small>", unsafe_allow_html=True)

# Configuração de Colunas do Dataframe para exibição premium
col_cfg_down = {
    "Gestor": st.column_config.TextColumn(width="medium"),
    "Fundo": st.column_config.TextColumn(width="large"),
    "CNPJ": st.column_config.TextColumn(width="medium"),
}
if "Patrimônio Líquido (PL)" in df_down_filtered.columns:
    col_cfg_down["Patrimônio Líquido (PL)"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "Taxa de Gestão Real (% a.a.)" in df_down_filtered.columns:
    col_cfg_down["Taxa de Gestão Real (% a.a.)"] = st.column_config.NumberColumn(format="%.3f%%", width="small")
if "Taxa de Gestão com Imputação (% a.a.)" in df_down_filtered.columns:
    col_cfg_down["Taxa de Gestão com Imputação (% a.a.)"] = st.column_config.NumberColumn(format="%.3f%%", width="small")
if "Remuneração Estimada (Real)" in df_down_filtered.columns:
    col_cfg_down["Remuneração Estimada (Real)"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "Remuneração Estimada (Imputada)" in df_down_filtered.columns:
    col_cfg_down["Remuneração Estimada (Imputada)"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "PDD" in df_down_filtered.columns:
    col_cfg_down["PDD"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "DC" in df_down_filtered.columns:
    col_cfg_down["DC"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "PL Inadimplência (PL_CVM)" in df_down_filtered.columns:
    col_cfg_down["PL Inadimplência (PL_CVM)"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "Inadimplência PDD/DC (%)" in df_down_filtered.columns:
    col_cfg_down["Inadimplência PDD/DC (%)"] = st.column_config.NumberColumn(format="%.2f%%", width="small")
if "Inadimplência PDD/PL (%)" in df_down_filtered.columns:
    col_cfg_down["Inadimplência PDD/PL (%)"] = st.column_config.NumberColumn(format="%.2f%%", width="small")
if "Subordinação Jr (%)" in df_down_filtered.columns:
    col_cfg_down["Subordinação Jr (%)"] = st.column_config.NumberColumn(format="%.2f%%", width="small")
if "Subordinação Jr+Mez (%)" in df_down_filtered.columns:
    col_cfg_down["Subordinação Jr+Mez (%)"] = st.column_config.NumberColumn(format="%.2f%%", width="small")

# Renderizar Tabela
st.dataframe(df_down_filtered, use_container_width=True, hide_index=True, column_config=col_cfg_down, height=400)

# Exportar para Excel
import io
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    df_down_filtered.to_excel(writer, index=False, sheet_name="Detalhamento")
buf.seek(0)

st.download_button(
    label="📥 Exportar Tabela Detalhada para Excel (.xlsx)",
    data=buf.read(),
    file_name="remuneracao_e_inadimplencia_detalhada_gestores.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

# ─────────────────────────────────────────────────────────────────────────────
# Tab: Aging de Vencidos
# ─────────────────────────────────────────────────────────────────────────────

with tab_aging:
    cvnp_cols_presentes = [c for c in CVNP_COLS if c in df_agg.columns]

    if "CVNP" not in df_agg.columns or not cvnp_cols_presentes:
        st.info("Dados de CVNP não disponíveis na base atual.")
    else:
        st.markdown('<div class="section-label">Ranking de CVNP por Gestor</div>', unsafe_allow_html=True)
        st.caption(
            "Crédito Vencido Não Pago total (soma dos fundos) por gestora. "
            "Solis destacada em azul. Mínimo de fundos aplicável."
        )

        min_f_aging = st.slider("Nº mínimo de fundos sob gestão", 1, 10, 2, key="ges_aging_min")
        df_aging = df_agg[df_agg["n_fundos"] >= min_f_aging].copy()

        # ── Ranking CVNP total ────────────────────────────────────────────────
        st.plotly_chart(
            bar_ranking(
                df_aging.rename(columns={"CVNP": "_val", "gestor": "_name"}),
                "_val", "_name",
                title="Ranking de CVNP por Gestora (R$)",
                top_n=15, highlight_name="Solis",
                is_percent=False, is_currency=True,
            ),
            use_container_width=True,
        )

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Perfil de Aging — Solis vs. Média de Mercado (%)</div>',
                    unsafe_allow_html=True)
        st.caption(
            "\n"
            "Distribuição percentual do CVNP por faixa de atraso. "
            "Normalizado sobre o CVNP total de cada grupo para comparabilidade."
        )

        is_solis_ges = df_ges["gestor"].str.contains("Solis", case=False, na=False)
        df_s  = df_ges[is_solis_ges]
        df_mk = df_ges[~is_solis_ges]

        def _aging_pct(df_g):
            totais = {c: df_g[c].sum() for c in cvnp_cols_presentes if c in df_g.columns}
            total_cvnp = sum(totais.values())
            if total_cvnp == 0:
                return {c: 0.0 for c in cvnp_cols_presentes}
            return {c: v / total_cvnp * 100 for c, v in totais.items()}

        pct_solis  = _aging_pct(df_s)
        pct_mercado = _aging_pct(df_mk)

        import plotly.graph_objects as go
        from components.charts import _base_layout, PALETTE

        labels = [CVNP_LABELS.get(c, c) for c in cvnp_cols_presentes]

        fig_aging = go.Figure()
        fig_aging.add_trace(go.Bar(
            name="Mercado (excl. Solis)",
            x=labels,
            y=[pct_mercado.get(c, 0) for c in cvnp_cols_presentes],
            marker_color="rgba(217,119,6,0.75)",
            hovertemplate="%{x}: %{y:.2f}%<extra>Mercado</extra>",
        ))
        fig_aging.add_trace(go.Bar(
            name="Solis Investimentos",
            x=labels,
            y=[pct_solis.get(c, 0) for c in cvnp_cols_presentes],
            marker_color="rgba(59,130,246,0.9)",
            hovertemplate="%{x}: %{y:.2f}%<extra>Solis</extra>",
        ))
        _lay = _base_layout("Distribuição do CVNP por Faixa de Atraso (%)", 440)
        _lay["barmode"] = "group"
        _lay["margin"].update({"t": 72})
        _lay["yaxis"].update({"title": "% do CVNP Total", "ticksuffix": "%"})
        _lay["xaxis"].update({"title": "Faixa de Atraso"})
        fig_aging.update_layout(**_lay)
        st.plotly_chart(fig_aging, use_container_width=True)
