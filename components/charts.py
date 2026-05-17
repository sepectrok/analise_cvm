"""Charts — Solis Investimentos Platform (Plotly) — Premium v2"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from utils.data_loader import TAXA_LABELS, TAXA_COLS

# ─── Plotly Palette — Premium Institutional ──────────────────────────────────
PALETTE = {
    "bg":      "#08090F",
    "paper":   "#12141E",
    "grid":    "rgba(148,163,184,0.06)",
    "text":    "#94A3B8",
    "text_hi": "#F1F5F9",
    "blue":    "#3B82F6",
    "blue_lt": "#60A5FA",
    "teal":    "#0D9488",
    "copper":  "#D97706",
    "copper_lt": "#F59E0B",
    "green":   "#10B981",
    "red":     "#EF4444",
    "colors":  ["#3B82F6", "#0D9488", "#D97706", "#10B981", "#8B5CF6", "#F59E0B"],
    "solis":   "#3B82F6",
    "mercado": "#D97706",
}


def _base_layout(title: str = "", height: int = 420) -> dict:
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PALETTE["bg"],
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color=PALETTE["text"]),
        height=height,
        margin=dict(l=16, r=24, t=44 if title else 20, b=36),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color=PALETTE["text"]),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
        colorway=PALETTE["colors"],
        xaxis=dict(
            gridcolor=PALETTE["grid"], zerolinecolor=PALETTE["grid"],
            tickfont=dict(size=11, color=PALETTE["text"]),
            title_font=dict(size=12, color=PALETTE["text"]),
            linecolor="rgba(0,0,0,0)", showline=False,
        ),
        yaxis=dict(
            gridcolor=PALETTE["grid"], zerolinecolor=PALETTE["grid"],
            tickfont=dict(size=11, color=PALETTE["text"]),
            title_font=dict(size=12, color=PALETTE["text"]),
            linecolor="rgba(0,0,0,0)", showline=False,
        ),
        hoverlabel=dict(
            bgcolor="#1A1D2B",
            bordercolor="rgba(148,163,184,0.15)",
            font=dict(family="Inter", size=12, color=PALETTE["text_hi"]),
        ),
    )
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(family="Space Grotesk, Inter, sans-serif", size=15, color=PALETTE["text_hi"]),
            x=0.01, xanchor="left", y=0.98,
        )
    return layout


def histogram_taxa(df: pd.DataFrame, col: str, height: int = 400) -> go.Figure:
    """Elegant histogram with stat markers."""
    label = TAXA_LABELS.get(col, col)
    s = df[col].dropna()
    if s.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=s, nbinsx=35, name="Distribuição",
        marker=dict(color=PALETTE["blue"], opacity=0.7, line=dict(color=PALETTE["bg"], width=0.8)),
    ))

    for val, color, label_v in [(s.mean(), PALETTE["copper"], "Média"),
                                  (s.median(), PALETTE["green"], "Mediana")]:
        fig.add_vline(x=val, line=dict(color=color, dash="dot", width=1.5),
                      annotation=dict(
                          text=f"{label_v}: {val:.3f}%",
                          font=dict(size=12, color=color),
                          showarrow=False, yshift=12
                      ))

    layout = _base_layout(f"Distribuição — {label}", height)
    layout["bargap"] = 0.08
    fig.update_layout(**layout)

    max_val = s.quantile(0.98)
    if pd.notna(max_val) and max_val > 0:
        fig.update_xaxes(title_text=f"{label} (% a.a.)", range=[0, max_val * 1.1])
    else:
        fig.update_xaxes(title_text=f"{label} (% a.a.)")

    fig.update_yaxes(title_text="Fundos")
    return fig


def boxplot_by_group(df: pd.DataFrame, col: str, group_col: str, height: int = 420) -> go.Figure:
    """Boxplot grouped by a categorical column."""
    label = TAXA_LABELS.get(col, col)
    df_v = df[[col, group_col]].dropna()
    if df_v.empty:
        return go.Figure()

    fig = px.box(df_v, x=group_col, y=col,
                 color_discrete_sequence=[PALETTE["blue"]],
                 points="outliers",
                 labels={col: f"{label} (% a.a.)", group_col: ""},
                 template=None)
    fig.update_traces(marker=dict(size=3, opacity=0.5, color=PALETTE["copper"]),
                      line_color=PALETTE["blue"],
                      fillcolor="rgba(59,130,246,0.15)")
    fig.update_layout(**_base_layout(f"Boxplot — {label}", height))
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=9))
    return fig


def violin_taxa(df: pd.DataFrame, col: str, height: int = 360) -> go.Figure:
    label = TAXA_LABELS.get(col, col)
    s = df[col].dropna()
    if s.empty:
        return go.Figure()
    fig = go.Figure(go.Violin(
        y=s, name=label, box_visible=True, meanline_visible=True,
        fillcolor="rgba(59,130,246,0.15)", line_color=PALETTE["blue"],
        points="outliers", marker=dict(color=PALETTE["copper"], size=3, opacity=0.5),
    ))
    fig.update_layout(**_base_layout(f"Violin — {label}", height))
    fig.update_yaxes(title_text=f"{label} (% a.a.)")
    return fig


def scatter_two_taxas(df: pd.DataFrame, col_x: str, col_y: str,
                       color_col: str = "foco_atuacao", height: int = 420) -> go.Figure:
    df_v = df[[col_x, col_y, color_col, "nome_curto"]].dropna(subset=[col_x, col_y])
    if df_v.empty:
        return go.Figure()
    fig = px.scatter(df_v, x=col_x, y=col_y, color=color_col,
                     hover_name="nome_curto",
                     labels={col_x: TAXA_LABELS.get(col_x, col_x),
                             col_y: TAXA_LABELS.get(col_y, col_y)},
                     color_discrete_sequence=PALETTE["colors"])
    fig.update_traces(marker=dict(size=7, opacity=0.7, line=dict(width=0.5, color=PALETTE["bg"])))
    fig.update_layout(**_base_layout(
        f"{TAXA_LABELS.get(col_x,col_x)} × {TAXA_LABELS.get(col_y,col_y)}", height))
    return fig


def heatmap_corr(df: pd.DataFrame, height: int = 420) -> go.Figure:
    cols = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 5]
    if len(cols) < 2:
        return go.Figure()
    corr = df[cols].corr()
    labels = [TAXA_LABELS.get(c, c).replace("Taxa de ", "").replace("Taxa Máx. de ", "") for c in cols]
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels,
        colorscale=[[0, PALETTE["blue"]], [0.5, PALETTE["bg"]], [1, PALETTE["copper"]]],
        zmid=0, text=np.round(corr.values, 2), texttemplate="%{text}",
        textfont=dict(size=10, color=PALETTE["text_hi"]),
        colorbar=dict(thickness=10, tickfont=dict(size=9)),
    ))
    fig.update_layout(**_base_layout("Correlação entre Taxas", height))
    return fig


def radar_fund(df: pd.DataFrame, cnpjs: list[str], height: int = 420) -> go.Figure:
    """Radar chart for one or more funds."""
    cols = [c for c in TAXA_COLS if c in df.columns]
    labels = [TAXA_LABELS.get(c, c).replace("Taxa de ", "") for c in cols]

    fig = go.Figure()
    for i, cnpj in enumerate(cnpjs):
        row = df[df["cnpj_tratado"] == cnpj]
        if row.empty:
            continue
        vals = [row[c].values[0] if c in row.columns else np.nan for c in cols]
        vals_clean = [v if not np.isnan(v) else 0 for v in vals]
        nome = row["nome_curto"].values[0] if "nome_curto" in row.columns else cnpj

        fig.add_trace(go.Scatterpolar(
            r=vals_clean + [vals_clean[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=nome[:40],
            line=dict(color=PALETTE["colors"][i % len(PALETTE["colors"])], width=2),
            fillcolor=f"rgba({','.join(str(int(c,16)) for c in [PALETTE['colors'][i%len(PALETTE['colors'])][1:3], PALETTE['colors'][i%len(PALETTE['colors'])][3:5], PALETTE['colors'][i%len(PALETTE['colors'])][5:7]])},0.1)",
            hovertemplate="%{theta}: %{r:.3f}%<extra>%{fullData.name}</extra>",
        ))

    fig.update_layout(
        **_base_layout("Radar de Taxas", height),
        polar=dict(
            bgcolor=PALETTE["bg"],
            radialaxis=dict(visible=True, gridcolor=PALETTE["grid"],
                            tickfont=dict(size=8, color=PALETTE["text"]),
                            ticksuffix="%"),
            angularaxis=dict(gridcolor=PALETTE["grid"],
                             tickfont=dict(size=9, color=PALETTE["text_hi"])),
        ),
    )
    return fig


def bar_ranking(df_agg: pd.DataFrame, val_col: str, name_col: str,
                title: str = "", top_n: int = 15, height: int = None, is_percent: bool = True,
                highlight_name: str = "Solis") -> go.Figure:
    """Premium horizontal bar chart ranking."""
    df_sorted = df_agg.dropna(subset=[val_col]).nlargest(top_n, val_col).iloc[::-1]
    n = len(df_sorted)
    if height is None:
        height = max(400, n * 32 + 80)

    colors = []
    for name in df_sorted[name_col]:
        if highlight_name.lower() in str(name).lower():
            colors.append(PALETTE["solis"])
        else:
            colors.append("rgba(148,163,184,0.18)")

    fig = go.Figure(go.Bar(
        x=df_sorted[val_col],
        y=df_sorted[name_col],
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        text=[f"{v:.3f}%" if is_percent else str(int(v)) for v in df_sorted[val_col]],
        textposition="outside",
        textfont=dict(size=11, color=PALETTE["text"]),
    ))
    _layout = _base_layout(title, height)
    for _k in ("margin", "font", "legend", "bargap", "colorway"):
        _layout.pop(_k, None)
    _layout["bargap"] = 0.4
    fig.update_layout(
        **_layout,
        margin=dict(l=220, r=80, t=50 if title else 20, b=36),
    )
    fig.update_xaxes(
        title_text="% a.a." if is_percent else "",
        title_font=dict(size=12, color=PALETTE["text"]),
        showgrid=False,
        tickfont=dict(size=11),
    )
    fig.update_yaxes(tickfont=dict(size=11), automargin=True)
    return fig


def bar_ranking_desc(df_agg: pd.DataFrame, val_col: str, name_col: str,
                     title: str = "", top_n: int = 15, height: int = 420) -> go.Figure:
    """Horizontal bar chart — descending (most expensive on top)."""
    df_sorted = df_agg.dropna(subset=[val_col]).nlargest(top_n, val_col)
    return bar_ranking(df_sorted, val_col, name_col, title, top_n, height)


def donut_foco(df: pd.DataFrame, height: int = 380) -> go.Figure:
    counts = df["foco_atuacao"].value_counts().head(10)
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.6,
        marker=dict(colors=PALETTE["colors"] * 3,
                    line=dict(color=PALETTE["bg"], width=2)),
        textfont=dict(size=9),
        hovertemplate="%{label}<br>%{value} fundos (%{percent})<extra></extra>",
    ))
    fig.update_layout(**_base_layout("Distribuição por Foco", height))
    fig.update_layout(legend=dict(orientation="v", font=dict(size=9)))
    return fig


def heatmap_entity_taxa(df_agg: pd.DataFrame, entity_col: str, height: int = 500) -> go.Figure:
    """Heatmap: entity (rows) × taxa type (cols)."""
    taxa_cols = [c for c in TAXA_COLS if c in df_agg.columns]
    labels = [TAXA_LABELS.get(c, c).replace("Taxa de ", "") for c in taxa_cols]
    entities = df_agg[entity_col].tolist()

    z = df_agg[taxa_cols].values
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=entities,
        colorscale=[[0, PALETTE["blue"]], [0.5, "rgba(18,20,30,0.8)"], [1, PALETTE["copper"]]],
        colorbar=dict(thickness=10, ticksuffix="%", tickfont=dict(size=8)),
        text=np.where(np.isnan(z), "—", np.round(z, 3).astype(str) + "%"),
        texttemplate="%{text}",
        textfont=dict(size=8, color=PALETTE["text_hi"]),
        hovertemplate="%{y}<br>%{x}: %{z:.3f}%<extra></extra>",
    ))
    fig.update_layout(**_base_layout(f"Heatmap — {entity_col.replace('_',' ').title()}", height))
    fig.update_yaxes(tickfont=dict(size=8), autorange="reversed")
    return fig


def boxplot_solis_vs_mercado(df_solis: pd.DataFrame, df_mercado: pd.DataFrame, col: str, height: int = 440) -> go.Figure:
    """Side-by-side boxplots for Solis vs Mercado."""
    label = TAXA_LABELS.get(col, col).replace("Taxa de ", "")
    fig = go.Figure()

    s_mercado = df_mercado[col].dropna()
    if not s_mercado.empty:
        fig.add_trace(go.Box(
            y=s_mercado, name="Mercado",
            marker_color=PALETTE["mercado"],
            boxmean=True,
            line_width=1.5,
            fillcolor="rgba(217,119,6,0.1)",
            marker=dict(size=4, opacity=0.5),
        ))

    s_solis = df_solis[col].dropna()
    if not s_solis.empty:
        fig.add_trace(go.Box(
            y=s_solis, name="Solis",
            marker_color=PALETTE["solis"],
            boxmean=True,
            line_width=1.5,
            fillcolor="rgba(59,130,246,0.1)",
            marker=dict(size=4, opacity=0.5),
        ))

    layout = _base_layout(f"Comparativo — {label}", height)
    layout["margin"] = dict(l=40, r=40, t=60, b=36)
    fig.update_layout(**layout)
    fig.update_yaxes(title_text="% a.a.")
    fig.update_xaxes(tickfont=dict(size=13))
    return fig


def multi_box_taxas(df: pd.DataFrame, height: int = 400) -> go.Figure:
    """Side-by-side boxplots for all taxa columns."""
    cols = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 5]
    if not cols:
        return go.Figure()
    fig = go.Figure()
    for i, col in enumerate(cols):
        s = df[col].dropna()
        fig.add_trace(go.Box(
            y=s, name=TAXA_LABELS.get(col, col).replace("Taxa de ", ""),
            marker_color=PALETTE["colors"][i % len(PALETTE["colors"])],
            boxmean="sd",
            line_width=1.2,
            fillcolor=f"rgba({','.join(str(int(PALETTE['colors'][i % len(PALETTE['colors'])][j:j+2], 16)) for j in (1,3,5))},0.12)",
        ))
    fig.update_layout(**_base_layout("Comparativo de Taxas", height))
    fig.update_yaxes(title_text="% a.a.", title_font=dict(size=9, color=PALETTE["text"]))
    return fig


def bar_foco_comparativo(df_solis: pd.DataFrame, df_mercado: pd.DataFrame, height: int = None) -> go.Figure:
    """Grouped horizontal bar chart comparing Solis vs Mercado."""
    counts_solis = df_solis["foco_atuacao"].value_counts()
    counts_mercado = df_mercado["foco_atuacao"].value_counts()

    top_focos = counts_mercado.nlargest(10).index.tolist()

    for f in counts_solis.index:
        if f not in top_focos:
            top_focos.append(f)

    df_plot = pd.DataFrame({
        "Foco": top_focos,
        "Mercado": [counts_mercado.get(f, 0) for f in top_focos],
        "Solis": [counts_solis.get(f, 0) for f in top_focos],
    }).sort_values("Mercado", ascending=True)

    n_cats = len(df_plot)
    chart_h = height or max(500, n_cats * 52 + 100)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_plot["Foco"], x=df_plot["Mercado"], name="Mercado", orientation="h",
        marker_color="rgba(217,119,6,0.55)",
        text=df_plot["Mercado"].astype(str),
        textposition="inside",
        textfont=dict(size=11, color=PALETTE["text_hi"]),
    ))
    fig.add_trace(go.Bar(
        y=df_plot["Foco"], x=df_plot["Solis"], name="Solis", orientation="h",
        marker_color=PALETTE["solis"],
        text=df_plot["Solis"].astype(str),
        textposition="inside",
        textfont=dict(size=11, color=PALETTE["text_hi"]),
    ))

    _layout = _base_layout("", chart_h)
    for _k in ("margin", "font", "legend", "barmode", "bargap", "bargroupgap"):
        _layout.pop(_k, None)
    _layout["barmode"] = "group"
    _layout["bargap"] = 0.28
    _layout["bargroupgap"] = 0.06
    _layout["font"] = dict(family="Inter, sans-serif", size=12, color=PALETTE["text"])
    _layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
        font=dict(size=12), bgcolor="rgba(0,0,0,0)"
    )
    fig.update_layout(
        **_layout,
        margin=dict(l=220, r=40, t=40, b=36),
    )
    fig.update_xaxes(showgrid=False, title_text="", tickfont=dict(size=11))
    fig.update_yaxes(tickfont=dict(size=11), automargin=True)
    return fig
