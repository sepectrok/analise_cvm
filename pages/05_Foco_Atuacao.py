"""Página 5 — Foco de Atuação"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


from components.sidebar import load_css, render_sidebar, apply_sidebar_filters
from components.metrics_cards import page_header
from components.charts import boxplot_by_group, PALETTE, _base_layout
from utils.data_loader import build_df_fidc, TAXA_LABELS, TAXA_COLS
from utils.formatters import fmt_pct

load_css()
df_full = build_df_fidc()
filters = render_sidebar(df_full)
df = apply_sidebar_filters(df_full, filters)

page_header("🎯", "Foco de Atuação", "Taxa média por segmento e competitividade relativa")

taxa_cols_avail = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 3]

df_seg = (
    df.groupby("foco_atuacao")[taxa_cols_avail + ["cnpj_tratado"]]
    .agg({**{c: ["mean", "median", "count"] for c in taxa_cols_avail}, "cnpj_tratado": "count"})
    .reset_index()
)
# Flatten cols
df_seg.columns = ["foco_atuacao"] + [
    f"{c}_{s}" for c in taxa_cols_avail for s in ["mean", "median", "count"]
] + ["n_fundos"]

st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Taxas por Segmento", "Boxplot", "Tabela", "Inadimplência", "Subordinação"])

with tab1:
    col_sel = st.selectbox(
        "Tipo de Taxa",
        taxa_cols_avail,
        format_func=lambda c: TAXA_LABELS.get(c, c),
        key="foco_taxa",
    )
    mean_col = f"{col_sel}_mean"

    if mean_col not in df_seg.columns:
        st.info("Sem dados suficientes para este tipo de taxa.")
        st.stop()

    taxa_label = TAXA_LABELS.get(col_sel, col_sel)

    # ── Gráfico comparativo Solis vs Mercado (apenas para gestao e performance) ──
    if col_sel in ["taxa_gestao", "taxa_performance"]:
        is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
        df_solis  = df[is_solis]
        df_mercado = df[~is_solis]

        df_plot = df_seg.dropna(subset=[mean_col]).sort_values(mean_col, ascending=True)
        focos = df_plot["foco_atuacao"].tolist()

        solis_means   = df_solis.groupby("foco_atuacao")[col_sel].mean().to_dict()
        mercado_means = df_mercado.groupby("foco_atuacao")[col_sel].mean().to_dict()
        mkt_mean      = df_mercado[col_sel].mean()
        solis_mean    = df_solis[col_sel].mean()

        n_cats  = len(focos)
        chart_h = max(700, n_cats * 55 + 120)

        fig = go.Figure()

        # ── Barras sem texto (sem sobreposição) ──
        fig.add_trace(go.Bar(
            y=focos,
            x=[mercado_means.get(f, np.nan) for f in focos],
            name="Mercado",
            orientation="h",
            marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Mercado: %{x:.3f}%<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=focos,
            x=[solis_means.get(f, np.nan) for f in focos],
            name="Solis Investimentos",
            orientation="h",
            marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Solis: %{x:.3f}%<extra></extra>",
        ))

        # ── Linha + badge: Média Mercado (topo) ──
        fig.add_vline(
            x=mkt_mean,
            line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2),
        )
        fig.add_annotation(
            x=mkt_mean, y=1.01, yref="paper",
            text=f"Méd. Mercado: <b>{mkt_mean:.3f}%</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=10, color="#FFFFFF"),
            bgcolor="rgba(217,119,6,0.8)", borderpad=5,
            bordercolor="rgba(0,0,0,0)",
        )

        # ── Linha + badge: Média Solis (20% abaixo para não sobrepor) ──
        if pd.notna(solis_mean):
            fig.add_vline(
                x=solis_mean,
                line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2),
            )
            fig.add_annotation(
                x=solis_mean, y=0.86, yref="paper",
                text=f"Méd. Solis: <b>{solis_mean:.3f}%</b>",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(size=10, color="#FFFFFF"),
                bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                bordercolor="rgba(0,0,0,0)",
            )

        # ── Layout ──
        _layout = _base_layout("", chart_h)
        for _k in ("margin", "font", "legend"):
            _layout.pop(_k, None)
        fig.update_layout(
            **_layout,
            barmode="group",
            bargap=0.28,
            bargroupgap=0.06,
            margin=dict(l=240, r=40, t=20, b=60),
            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
            legend=dict(
                orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                font=dict(size=12), bgcolor="rgba(0,0,0,0)",
            ),
        )
        fig.update_xaxes(title_text="% a.a.", title_font=dict(size=12), tickfont=dict(size=11))
        fig.update_yaxes(tickfont=dict(size=11), automargin=True)

        # Título fora do gráfico (evita sobreposição com legenda)
        st.markdown(f"**{taxa_label} — Média por Segmento · Mercado vs Solis**")
        st.plotly_chart(fig, use_container_width=True)

    # ── Gráfico geral (outras taxas) ──────────────────────────────────────────
    else:
        df_plot  = df_seg.dropna(subset=[mean_col]).sort_values(mean_col, ascending=True)
        mkt_mean = df[col_sel].mean()

        n_cats  = len(df_plot)
        chart_h = max(500, n_cats * 38 + 80)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_plot[mean_col],
            y=df_plot["foco_atuacao"],
            orientation="h",
            marker=dict(
                color=df_plot[mean_col],
                colorscale=[[0, PALETTE["teal"]], [0.5, PALETTE["blue"]], [1, PALETTE["copper"]]],
                showscale=False,
            ),
            text=[f"{v:.3f}%" for v in df_plot[mean_col]],
            textposition="outside",
            textfont=dict(size=11, color=PALETTE["text"]),
            hovertemplate="<b>%{y}</b><br>Média: %{x:.3f}%<extra></extra>",
        ))
        fig.add_vline(
            x=mkt_mean,
            line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2),
        )
        fig.add_annotation(
            x=mkt_mean, y=1.01, yref="paper",
            text=f"Média Geral: <b>{mkt_mean:.3f}%</b>",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(size=10, color="#FFFFFF"),
            bgcolor="rgba(217,119,6,0.8)", borderpad=5,
            bordercolor="rgba(0,0,0,0)",
        )

        _layout = _base_layout("", chart_h)
        for _k in ("margin", "font", "legend"):
            _layout.pop(_k, None)
        fig.update_layout(
            **_layout,
            bargap=0.35,
            margin=dict(l=240, r=80, t=20, b=50),
            font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
        )
        fig.update_xaxes(title_text="% a.a.", title_font=dict(size=12), tickfont=dict(size=11))
        fig.update_yaxes(tickfont=dict(size=11), automargin=True)

        st.markdown(f"**{taxa_label} — Média por Segmento**")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_box = st.selectbox(
        "Tipo de Taxa",
        taxa_cols_avail,
        format_func=lambda c: TAXA_LABELS.get(c, c),
        key="foco_box",
    )
    st.plotly_chart(boxplot_by_group(df, col_box, "foco_atuacao", height=500), use_container_width=True)

with tab3:
    rows = []
    for _, seg_row in df_seg.iterrows():
        r = {"Segmento": seg_row["foco_atuacao"], "Nº Fundos": int(seg_row["n_fundos"])}
        for c in taxa_cols_avail:
            mean_val = seg_row.get(f"{c}_mean", np.nan)
            med_val = seg_row.get(f"{c}_median", np.nan)
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Média %)"]  = round(mean_val, 4) if pd.notna(mean_val) else np.nan
            r[TAXA_LABELS.get(c, c).replace("Taxa de ", "") + " (Med. %)"]   = round(med_val, 4) if pd.notna(med_val) else np.nan
        rows.append(r)

    if rows:
        df_table = pd.DataFrame(rows).sort_values("Nº Fundos", ascending=False)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados para a tabela.")

with tab4:
    st.markdown('<div class="section-label">Inadimplência por Segmento — Solis vs Mercado</div>', unsafe_allow_html=True)
    st.caption("Comparativo da taxa de inadimplência média ponderada real entre a carteira Solis e o Mercado geral por segmento.")

    subtab_dc, subtab_pl = st.tabs(["📊 PDD / DC", "📉 PDD / PL"])

    # ── Sub-tab: PDD / DC ─────────────────────────────────────────────────────
    with subtab_dc:
        st.caption(
            "**PDD / DC** — Provisão para Devedores Duvidosos sobre os Direitos Creditórios em atraso. "
            "Mede a cobertura de PDD sobre o crédito inadimplente. Fundos sem DC > 0 são excluídos."
        )
        
        if "taxa_inadimplencia" in df.columns and df["taxa_inadimplencia"].notna().any():
            is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
            df_solis = df[is_solis]
            df_mercado = df[~is_solis]

            # Médias por segmento para cada grupo (soma PDD / soma DC)
            solis_sums = df_solis.groupby("foco_atuacao")[["PDD", "DC"]].sum() if not df_solis.empty else pd.DataFrame(columns=["PDD", "DC"])
            solis_inad_seg = {}
            if "DC" in solis_sums.columns:
                solis_inad_seg = pd.Series(
                    np.where(
                        solis_sums["DC"] > 0,
                        (solis_sums["PDD"] / solis_sums["DC"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=solis_sums.index
                ).to_dict()

            mercado_sums = df_mercado.groupby("foco_atuacao")[["PDD", "DC"]].sum() if not df_mercado.empty else pd.DataFrame(columns=["PDD", "DC"])
            mercado_inad_seg = {}
            focos = []
            if "DC" in mercado_sums.columns:
                mercado_inad_seg = pd.Series(
                    np.where(
                        mercado_sums["DC"] > 0,
                        (mercado_sums["PDD"] / mercado_sums["DC"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=mercado_sums.index
                ).to_dict()
                
                mercado_inad_series = pd.Series(
                    np.where(
                        mercado_sums["DC"] > 0,
                        (mercado_sums["PDD"] / mercado_sums["DC"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=mercado_sums.index
                ).dropna().sort_values(ascending=True)
                focos = mercado_inad_series.index.tolist()

            mkt_inad_mean = np.nan
            if not df_mercado.empty and "DC" in df_mercado.columns and df_mercado["DC"].sum() > 0:
                mkt_inad_mean = float(min(df_mercado["PDD"].sum() / df_mercado["DC"].sum() * 100, 100.0))

            solis_inad_mean = np.nan
            if not df_solis.empty and "DC" in df_solis.columns and df_solis["DC"].sum() > 0:
                solis_inad_mean = float(min(df_solis["PDD"].sum() / df_solis["DC"].sum() * 100, 100.0))

            if focos:
                import plotly.graph_objects as go
                from components.charts import _base_layout, PALETTE

                n_cats  = len(focos)
                chart_h = max(500, n_cats * 45 + 100)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=focos,
                    x=[mercado_inad_seg.get(f, np.nan) for f in focos],
                    name="Mercado",
                    orientation="h",
                    marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Mercado: %{x:.2f}%<extra></extra>",
                ))
                fig.add_trace(go.Bar(
                    y=focos,
                    x=[solis_inad_seg.get(f, np.nan) for f in focos],
                    name="Solis Investimentos",
                    orientation="h",
                    marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Solis: %{x:.2f}%<extra></extra>",
                ))

                if pd.notna(mkt_inad_mean):
                    fig.add_vline(x=mkt_inad_mean, line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2))
                    fig.add_annotation(
                        x=mkt_inad_mean, y=1.01, yref="paper",
                        text=f"Méd. Mercado: <b>{mkt_inad_mean:.1f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5,
                    )
                if pd.notna(solis_inad_mean):
                    fig.add_vline(x=solis_inad_mean, line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2))
                    fig.add_annotation(
                        x=solis_inad_mean, y=0.86, yref="paper",
                        text=f"Méd. Solis: <b>{solis_inad_mean:.1f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                    )

                _layout = _base_layout("", chart_h)
                for _k in ("margin", "font", "legend"):
                    _layout.pop(_k, None)
                fig.update_layout(
                    **_layout,
                    barmode="group",
                    bargap=0.28,
                    bargroupgap=0.06,
                    margin=dict(l=240, r=40, t=20, b=60),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)",
                    ),
                )
                fig.update_xaxes(title_text="% (PDD/DC)", title_font=dict(size=12), tickfont=dict(size=11))
                fig.update_yaxes(tickfont=dict(size=11), automargin=True)

                st.markdown("**Inadimplência (PDD/DC) por Segmento — Mercado vs Solis**")
                st.plotly_chart(fig, use_container_width=True)

            # Tabela resumo segura
            all_segments_dc = sorted(list(set(list(mercado_inad_seg.keys()) + list(solis_inad_seg.keys()))))
            rows_inad = [
                {
                    "Segmento":    f,
                    "Mercado (%)": round(mercado_inad_seg.get(f, np.nan), 2) if pd.notna(mercado_inad_seg.get(f, np.nan)) else np.nan,
                    "Solis (%)":   round(solis_inad_seg.get(f, np.nan), 2) if pd.notna(solis_inad_seg.get(f, np.nan)) else np.nan,
                }
                for f in all_segments_dc
            ]
            df_inad_table = pd.DataFrame(rows_inad, columns=["Segmento", "Mercado (%)", "Solis (%)"])
            if not df_inad_table.empty:
                st.dataframe(
                    df_inad_table.sort_values("Mercado (%)", ascending=False, na_position="last"),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Mercado (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Solis (%)":   st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )
            else:
                st.info("Nenhum dado de PDD/DC para exibir na tabela.")
        else:
            st.info("Dados de inadimplência (PDD/DC) não disponíveis para os segmentos filtrados.")

    # ── Sub-tab: PDD / PL ─────────────────────────────────────────────────────
    with subtab_pl:
        st.caption(
            "**PDD / PL** — Provisão para Devedores Duvidosos sobre o Patrimônio Líquido total. "
            "Mede o peso da inadimplência em relação ao patrimônio do fundo. Fundos sem PL_CVM > 0 são excluídos."
        )

        if "taxa_inadimplencia_pl" in df.columns and df["taxa_inadimplencia_pl"].notna().any():
            is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
            df_solis = df[is_solis]
            df_mercado = df[~is_solis]

            # Médias por segmento para cada grupo (soma PDD / soma PL_CVM)
            solis_sums_pl = df_solis.groupby("foco_atuacao")[["PDD", "PL_CVM"]].sum() if not df_solis.empty else pd.DataFrame(columns=["PDD", "PL_CVM"])
            solis_inad_seg_pl = {}
            if "PL_CVM" in solis_sums_pl.columns:
                solis_inad_seg_pl = pd.Series(
                    np.where(
                        solis_sums_pl["PL_CVM"] > 0,
                        (solis_sums_pl["PDD"] / solis_sums_pl["PL_CVM"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=solis_sums_pl.index
                ).to_dict()

            mercado_sums_pl = df_mercado.groupby("foco_atuacao")[["PDD", "PL_CVM"]].sum() if not df_mercado.empty else pd.DataFrame(columns=["PDD", "PL_CVM"])
            mercado_inad_seg_pl = {}
            focos_pl = []
            if "PL_CVM" in mercado_sums_pl.columns:
                mercado_inad_seg_pl = pd.Series(
                    np.where(
                        mercado_sums_pl["PL_CVM"] > 0,
                        (mercado_sums_pl["PDD"] / mercado_sums_pl["PL_CVM"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=mercado_sums_pl.index
                ).to_dict()

                mercado_inad_series_pl = pd.Series(
                    np.where(
                        mercado_sums_pl["PL_CVM"] > 0,
                        (mercado_sums_pl["PDD"] / mercado_sums_pl["PL_CVM"] * 100).clip(upper=100),
                        np.nan,
                    ),
                    index=mercado_sums_pl.index
                ).dropna().sort_values(ascending=True)
                focos_pl = mercado_inad_series_pl.index.tolist()

            mkt_inad_mean_pl = np.nan
            if not df_mercado.empty and "PL_CVM" in df_mercado.columns and df_mercado["PL_CVM"].sum() > 0:
                mkt_inad_mean_pl = float(min(df_mercado["PDD"].sum() / df_mercado["PL_CVM"].sum() * 100, 100.0))

            solis_inad_mean_pl = np.nan
            if not df_solis.empty and "PL_CVM" in df_solis.columns and df_solis["PL_CVM"].sum() > 0:
                solis_inad_mean_pl = float(min(df_solis["PDD"].sum() / df_solis["PL_CVM"].sum() * 100, 100.0))

            if focos_pl:
                import plotly.graph_objects as go
                from components.charts import _base_layout, PALETTE

                n_cats  = len(focos_pl)
                chart_h = max(500, n_cats * 45 + 100)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=focos_pl,
                    x=[mercado_inad_seg_pl.get(f, np.nan) for f in focos_pl],
                    name="Mercado",
                    orientation="h",
                    marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Mercado: %{x:.2f}%<extra></extra>",
                ))
                fig.add_trace(go.Bar(
                    y=focos_pl,
                    x=[solis_inad_seg_pl.get(f, np.nan) for f in focos_pl],
                    name="Solis Investimentos",
                    orientation="h",
                    marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Solis: %{x:.2f}%<extra></extra>",
                ))

                if pd.notna(mkt_inad_mean_pl):
                    fig.add_vline(x=mkt_inad_mean_pl, line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2))
                    fig.add_annotation(
                        x=mkt_inad_mean_pl, y=1.01, yref="paper",
                        text=f"Méd. Mercado: <b>{mkt_inad_mean_pl:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5,
                    )
                if pd.notna(solis_inad_mean_pl):
                    fig.add_vline(x=solis_inad_mean_pl, line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2))
                    fig.add_annotation(
                        x=solis_inad_mean_pl, y=0.86, yref="paper",
                        text=f"Méd. Solis: <b>{solis_inad_mean_pl:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                    )

                _layout = _base_layout("", chart_h)
                for _k in ("margin", "font", "legend"):
                    _layout.pop(_k, None)
                fig.update_layout(
                    **_layout,
                    barmode="group",
                    bargap=0.28,
                    bargroupgap=0.06,
                    margin=dict(l=240, r=40, t=20, b=60),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)",
                    ),
                )
                fig.update_xaxes(title_text="% (PDD/PL)", title_font=dict(size=12), tickfont=dict(size=11))
                fig.update_yaxes(tickfont=dict(size=11), automargin=True)

                st.markdown("**Inadimplência (PDD/PL) por Segmento — Mercado vs Solis**")
                st.plotly_chart(fig, use_container_width=True)

            # Tabela resumo segura
            all_segments_pl = sorted(list(set(list(mercado_inad_seg_pl.keys()) + list(solis_inad_seg_pl.keys()))))
            rows_inad_pl = [
                {
                    "Segmento":    f,
                    "Mercado (%)": round(mercado_inad_seg_pl.get(f, np.nan), 2) if pd.notna(mercado_inad_seg_pl.get(f, np.nan)) else np.nan,
                    "Solis (%)":   round(solis_inad_seg_pl.get(f, np.nan), 2) if pd.notna(solis_inad_seg_pl.get(f, np.nan)) else np.nan,
                }
                for f in all_segments_pl
            ]
            df_inad_table_pl = pd.DataFrame(rows_inad_pl, columns=["Segmento", "Mercado (%)", "Solis (%)"])
            if not df_inad_table_pl.empty:
                st.dataframe(
                    df_inad_table_pl.sort_values("Mercado (%)", ascending=False, na_position="last"),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Mercado (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Solis (%)":   st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )
            else:
                st.info("Nenhum dado de PDD/PL para exibir na tabela.")
        else:
            st.info("Dados de inadimplência (PDD/PL) não disponíveis para os segmentos filtrados.")

with tab5:
    st.markdown('<div class="section-label">Subordinação por Segmento — Solis vs Mercado</div>', unsafe_allow_html=True)
    st.caption("Comparativo da subordinação média (simples) entre a carteira Solis e o Mercado geral por segmento.")

    subtab_jr, subtab_jrmz = st.tabs(["Subordinação Jr", "Subordinação Jr + Mez"])

    with subtab_jr:
        st.caption("Média simples da cota Subordinada Júnior (%) por fundo.")
        if "Sub_JR" in df.columns and df["Sub_JR"].notna().any():
            is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
            df_solis = df[is_solis]
            df_mercado = df[~is_solis]

            solis_means = df_solis.groupby("foco_atuacao")["Sub_JR"].mean().to_dict() if not df_solis.empty else {}
            mercado_means_series = df_mercado.groupby("foco_atuacao")["Sub_JR"].mean().dropna() if not df_mercado.empty else pd.Series(dtype=float)
            mercado_means = mercado_means_series.to_dict()
            focos = mercado_means_series.sort_values(ascending=True).index.tolist()

            mkt_mean = df_mercado["Sub_JR"].mean() if not df_mercado.empty else np.nan
            solis_mean = df_solis["Sub_JR"].mean() if not df_solis.empty else np.nan

            if focos:
                import plotly.graph_objects as go
                from components.charts import _base_layout, PALETTE

                n_cats  = len(focos)
                chart_h = max(500, n_cats * 45 + 100)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=focos,
                    x=[mercado_means.get(f, np.nan) for f in focos],
                    name="Mercado",
                    orientation="h",
                    marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Mercado: %{x:.2f}%<extra></extra>",
                ))
                fig.add_trace(go.Bar(
                    y=focos,
                    x=[solis_means.get(f, np.nan) for f in focos],
                    name="Solis Investimentos",
                    orientation="h",
                    marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Solis: %{x:.2f}%<extra></extra>",
                ))

                if pd.notna(mkt_mean):
                    fig.add_vline(x=mkt_mean, line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2))
                    fig.add_annotation(
                        x=mkt_mean, y=1.01, yref="paper",
                        text=f"Méd. Mercado: <b>{mkt_mean:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5,
                    )
                if pd.notna(solis_mean):
                    fig.add_vline(x=solis_mean, line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2))
                    fig.add_annotation(
                        x=solis_mean, y=0.86, yref="paper",
                        text=f"Méd. Solis: <b>{solis_mean:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                    )

                _layout = _base_layout("", chart_h)
                for _k in ("margin", "font", "legend"):
                    _layout.pop(_k, None)
                fig.update_layout(
                    **_layout,
                    barmode="group",
                    bargap=0.28,
                    bargroupgap=0.06,
                    margin=dict(l=240, r=40, t=20, b=60),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)",
                    ),
                )
                fig.update_xaxes(title_text="% (Subordinação Jr)", title_font=dict(size=12), tickfont=dict(size=11))
                fig.update_yaxes(tickfont=dict(size=11), automargin=True)

                st.markdown("**Subordinação Jr por Segmento — Mercado vs Solis**")
                st.plotly_chart(fig, use_container_width=True)

            all_segments = sorted(list(set(list(mercado_means.keys()) + list(solis_means.keys()))))
            rows_table = [
                {
                    "Segmento":    f,
                    "Mercado (%)": round(mercado_means.get(f, np.nan), 2) if pd.notna(mercado_means.get(f, np.nan)) else np.nan,
                    "Solis (%)":   round(solis_means.get(f, np.nan), 2) if pd.notna(solis_means.get(f, np.nan)) else np.nan,
                }
                for f in all_segments
            ]
            df_table = pd.DataFrame(rows_table, columns=["Segmento", "Mercado (%)", "Solis (%)"])
            if not df_table.empty:
                st.dataframe(
                    df_table.sort_values("Mercado (%)", ascending=False, na_position="last"),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Mercado (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Solis (%)":   st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )
        else:
            st.info("Dados de Subordinação Jr não disponíveis para os segmentos filtrados.")

    with subtab_jrmz:
        st.caption("Média simples da cota Subordinada Júnior + Mezanino (%) por fundo.")
        if "Sub_JR_MZ" in df.columns and df["Sub_JR_MZ"].notna().any():
            is_solis = df["gestor"].str.contains("Solis", case=False, na=False)
            df_solis = df[is_solis]
            df_mercado = df[~is_solis]

            solis_means_mz = df_solis.groupby("foco_atuacao")["Sub_JR_MZ"].mean().to_dict() if not df_solis.empty else {}
            mercado_means_mz_series = df_mercado.groupby("foco_atuacao")["Sub_JR_MZ"].mean().dropna() if not df_mercado.empty else pd.Series(dtype=float)
            mercado_means_mz = mercado_means_mz_series.to_dict()
            focos_mz = mercado_means_mz_series.sort_values(ascending=True).index.tolist()

            mkt_mean_mz = df_mercado["Sub_JR_MZ"].mean() if not df_mercado.empty else np.nan
            solis_mean_mz = df_solis["Sub_JR_MZ"].mean() if not df_solis.empty else np.nan

            if focos_mz:
                import plotly.graph_objects as go
                from components.charts import _base_layout, PALETTE

                n_cats  = len(focos_mz)
                chart_h = max(500, n_cats * 45 + 100)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=focos_mz,
                    x=[mercado_means_mz.get(f, np.nan) for f in focos_mz],
                    name="Mercado",
                    orientation="h",
                    marker=dict(color="rgba(217,119,6,0.7)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Mercado: %{x:.2f}%<extra></extra>",
                ))
                fig.add_trace(go.Bar(
                    y=focos_mz,
                    x=[solis_means_mz.get(f, np.nan) for f in focos_mz],
                    name="Solis Investimentos",
                    orientation="h",
                    marker=dict(color="rgba(59,130,246,0.85)", line=dict(width=0)),
                    hovertemplate="<b>%{y}</b><br>Solis: %{x:.2f}%<extra></extra>",
                ))

                if pd.notna(mkt_mean_mz):
                    fig.add_vline(x=mkt_mean_mz, line=dict(color="rgba(217,119,6,1.0)", dash="dot", width=2))
                    fig.add_annotation(
                        x=mkt_mean_mz, y=1.01, yref="paper",
                        text=f"Méd. Mercado: <b>{mkt_mean_mz:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(217,119,6,0.8)", borderpad=5,
                    )
                if pd.notna(solis_mean_mz):
                    fig.add_vline(x=solis_mean_mz, line=dict(color="rgba(96,165,250,1.0)", dash="dash", width=2))
                    fig.add_annotation(
                        x=solis_mean_mz, y=0.86, yref="paper",
                        text=f"Méd. Solis: <b>{solis_mean_mz:.2f}%</b>",
                        showarrow=False, xanchor="left", xshift=8,
                        font=dict(size=10, color="#FFFFFF"),
                        bgcolor="rgba(59,130,246,0.8)", borderpad=5,
                    )

                _layout = _base_layout("", chart_h)
                for _k in ("margin", "font", "legend"):
                    _layout.pop(_k, None)
                fig.update_layout(
                    **_layout,
                    barmode="group",
                    bargap=0.28,
                    bargroupgap=0.06,
                    margin=dict(l=240, r=40, t=20, b=60),
                    font=dict(family="Inter, sans-serif", size=12, color=PALETTE["text"]),
                    legend=dict(
                        orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)",
                    ),
                )
                fig.update_xaxes(title_text="% (Subordinação Jr+Mez)", title_font=dict(size=12), tickfont=dict(size=11))
                fig.update_yaxes(tickfont=dict(size=11), automargin=True)

                st.markdown("**Subordinação Jr+Mez por Segmento — Mercado vs Solis**")
                st.plotly_chart(fig, use_container_width=True)

            all_segments_mz = sorted(list(set(list(mercado_means_mz.keys()) + list(solis_means_mz.keys()))))
            rows_table_mz = [
                {
                    "Segmento":    f,
                    "Mercado (%)": round(mercado_means_mz.get(f, np.nan), 2) if pd.notna(mercado_means_mz.get(f, np.nan)) else np.nan,
                    "Solis (%)":   round(solis_means_mz.get(f, np.nan), 2) if pd.notna(solis_means_mz.get(f, np.nan)) else np.nan,
                }
                for f in all_segments_mz
            ]
            df_table_mz = pd.DataFrame(rows_table_mz, columns=["Segmento", "Mercado (%)", "Solis (%)"])
            if not df_table_mz.empty:
                st.dataframe(
                    df_table_mz.sort_values("Mercado (%)", ascending=False, na_position="last"),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "Mercado (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Solis (%)":   st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )
        else:
            st.info("Dados de Subordinação Jr+Mez não disponíveis para os segmentos filtrados.")

st.markdown("---")

st.markdown('<div class="section-label">📋 Tabela Detalhada de Ativos Analisados</div>', unsafe_allow_html=True)
st.caption("Detalhamento completo por fundo contendo patrimônio líquido, taxas, inadimplência e subordinação.")

# Criar DataFrame formatado para visualização e download
df_down = df.copy()

# Definir colunas amigáveis
cols_map = {
    "foco_atuacao": "Segmento",
    "gestor": "Gestor",
    "nome_fundo": "Fundo",
    "cnpj_tratado": "CNPJ",
    "Valor_PL": "Patrimônio Líquido (PL)",
    "taxa_gestao_raw": "Taxa de Gestão Real (% a.a.)",
    "taxa_gestao": "Taxa de Gestão (% a.a.)",
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
search_query = st.text_input("🔍 Busca na tabela detalhada", key="atuacao_detalhada_search", placeholder="Buscar por segmento, fundo ou CNPJ...")
if search_query:
    mask = df_down_filtered.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
    df_down_filtered = df_down_filtered[mask]

st.markdown(f"<small style='color:var(--text-muted)'>{len(df_down_filtered)} registros encontrados</small>", unsafe_allow_html=True)

# Configuração de Colunas do Dataframe para exibição premium
col_cfg_down = {
    "Segmento": st.column_config.TextColumn(width="medium"),
    "Gestor": st.column_config.TextColumn(width="medium"),
    "Fundo": st.column_config.TextColumn(width="large"),
    "CNPJ": st.column_config.TextColumn(width="medium"),
}
if "Patrimônio Líquido (PL)" in df_down_filtered.columns:
    col_cfg_down["Patrimônio Líquido (PL)"] = st.column_config.NumberColumn(format="R$ %,.2f", width="medium")
if "Taxa de Gestão Real (% a.a.)" in df_down_filtered.columns:
    col_cfg_down["Taxa de Gestão Real (% a.a.)"] = st.column_config.NumberColumn(format="%.3f%%", width="small")
if "Taxa de Gestão (% a.a.)" in df_down_filtered.columns:
    col_cfg_down["Taxa de Gestão (% a.a.)"] = st.column_config.NumberColumn(format="%.3f%%", width="small")
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
    file_name="detalhamento_ativos_foco_atuacao.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
