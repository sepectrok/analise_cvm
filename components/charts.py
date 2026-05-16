"""Charts — FIDC Analytics Platform (Plotly)"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from utils.data_loader import TAXA_LABELS, TAXA_COLS

# ─── Plotly Template ──────────────────────────────────────────────────────────
PALETTE = {
    "bg":      "#0B0E1A",
    "paper":   "#151D2E",
    "grid":    "#1E2D45",
    "text":    "#8B96A8",
    "text_hi": "#E8EDF4",
    "blue":    "#2E6FBF",
    "teal":    "#1E5F74",
    "copper":  "#B87C4C",
    "green":   "#2EAC6D",
    "red":     "#E05252",
    "colors":  ["#2E6FBF", "#1E8FA8", "#B87C4C", "#2EAC6D", "#7B5EA7", "#E09B2E"],
}


def _base_layout(title: str = "", height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(family="Space Grotesk", size=15, color=PALETTE["text_hi"]),
                   x=0.01, xanchor="left"),
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["bg"],
        font=dict(family="Inter", size=12, color=PALETTE["text"]),
        height=height,
        margin=dict(l=16, r=16, t=48, b=32),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        colorway=PALETTE["colors"],
        xaxis=dict(gridcolor=PALETTE["grid"], zerolinecolor=PALETTE["grid"],
                   tickfont=dict(size=11), linecolor=PALETTE["grid"]),
        yaxis=dict(gridcolor=PALETTE["grid"], zerolinecolor=PALETTE["grid"],
                   tickfont=dict(size=11), linecolor=PALETTE["grid"]),
    )


def histogram_taxa(df: pd.DataFrame, col: str, height: int = 380) -> go.Figure:
    """Elegant histogram with KDE line and stat markers."""
    label = TAXA_LABELS.get(col, col)
    s = df[col].dropna()
    if s.empty:
        return go.Figure()

    fig = go.Figure()

    # Histogram bars
    fig.add_trace(go.Histogram(
        x=s, nbinsx=30, name="Distribuição",
        marker=dict(color=PALETTE["blue"], opacity=0.7, line=dict(color=PALETTE["bg"], width=0.5)),
    ))

    # Mean & median lines
    for val, color, label_v in [(s.mean(), PALETTE["copper"], "Média"),
                                  (s.median(), PALETTE["green"], "Mediana")]:
        fig.add_vline(x=val, line=dict(color=color, dash="dot", width=1.5),
                      annotation=dict(text=f"  {label_v}: {val:.3f}%",
                                      font=dict(size=10, color=color), showarrow=False))

    fig.update_layout(**_base_layout(f"Distribuição — {label}", height))
    fig.update_xaxes(title_text=f"{label} (% a.a.)")
    fig.update_yaxes(title_text="Quantidade de Fundos")
    return fig


def boxplot_by_group(df: pd.DataFrame, col: str, group_col: str, height: int = 420) -> go.Figure:
    """Boxplot grouped by a categorical column."""
    label = TAXA_LABELS.get(col, col)
    df_v = df[[col, group_col]].dropna()
    if df_v.empty:
        return go.Figure()

    fig = px.box(df_v, x=group_col, y=col,
                 color_discrete_sequence=[PALETTE["teal"]],
                 points="outliers",
                 labels={col: f"{label} (% a.a.)", group_col: ""},
                 template=None)
    fig.update_traces(marker=dict(size=4, opacity=0.6, color=PALETTE["copper"]),
                      line_color=PALETTE["teal"],
                      fillcolor="rgba(30,95,116,0.3)")
    fig.update_layout(**_base_layout(f"Boxplot por {group_col.replace('_',' ').title()} — {label}", height))
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=9))
    return fig


def violin_taxa(df: pd.DataFrame, col: str, height: int = 360) -> go.Figure:
    label = TAXA_LABELS.get(col, col)
    s = df[col].dropna()
    if s.empty:
        return go.Figure()
    fig = go.Figure(go.Violin(
        y=s, name=label, box_visible=True, meanline_visible=True,
        fillcolor="rgba(46,111,191,0.25)", line_color=PALETTE["blue"],
        points="outliers", marker=dict(color=PALETTE["copper"], size=4, opacity=0.7),
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
    fig.update_traces(marker=dict(size=8, opacity=0.75, line=dict(width=0.5, color=PALETTE["bg"])))
    fig.update_layout(**_base_layout(
        f"Scatter — {TAXA_LABELS.get(col_x,col_x)} × {TAXA_LABELS.get(col_y,col_y)}", height))
    return fig


def heatmap_corr(df: pd.DataFrame, height: int = 420) -> go.Figure:
    cols = [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 5]
    if len(cols) < 2:
        return go.Figure()
    corr = df[cols].corr()
    labels = [TAXA_LABELS.get(c, c).replace("Taxa de ", "").replace("Taxa Máx. de ", "") for c in cols]
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels,
        colorscale=[[0, PALETTE["teal"]], [0.5, PALETTE["bg"]], [1, PALETTE["copper"]]],
        zmid=0, text=np.round(corr.values, 2), texttemplate="%{text}",
        textfont=dict(size=11, color=PALETTE["text_hi"]),
        colorbar=dict(thickness=12, tickfont=dict(size=10)),
    ))
    fig.update_layout(**_base_layout("Matriz de Correlação entre Taxas", height))
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
        # Replace nan with 0 for radar
        vals_clean = [v if not np.isnan(v) else 0 for v in vals]
        nome = row["nome_curto"].values[0] if "nome_curto" in row.columns else cnpj

        fig.add_trace(go.Scatterpolar(
            r=vals_clean + [vals_clean[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=nome[:40],
            line=dict(color=PALETTE["colors"][i % len(PALETTE["colors"])], width=2),
            fillcolor=f"rgba({','.join(str(int(c,16)) for c in [PALETTE['colors'][i%len(PALETTE['colors'])][1:3], PALETTE['colors'][i%len(PALETTE['colors'])][3:5], PALETTE['colors'][i%len(PALETTE['colors'])][5:7]])},0.15)",
            hovertemplate="%{theta}: %{r:.3f}%<extra>%{fullData.name}</extra>",
        ))

    fig.update_layout(
        **_base_layout("Radar de Taxas", height),
        polar=dict(
            bgcolor=PALETTE["bg"],
            radialaxis=dict(visible=True, gridcolor=PALETTE["grid"],
                            tickfont=dict(size=9, color=PALETTE["text"]),
                            ticksuffix="%"),
            angularaxis=dict(gridcolor=PALETTE["grid"],
                             tickfont=dict(size=10, color=PALETTE["text_hi"])),
        ),
    )
    return fig


def bar_ranking(df_agg: pd.DataFrame, val_col: str, name_col: str,
                title: str = "", top_n: int = 15, height: int = None, is_percent: bool = True) -> go.Figure:
    """Horizontal bar chart ranking."""
    df_sorted = df_agg.dropna(subset=[val_col]).nlargest(top_n, val_col).iloc[::-1]
    if height is None:
        height = max(400, len(df_sorted) * 22)
    fig = go.Figure(go.Bar(
        x=df_sorted[val_col],
        y=df_sorted[name_col],
        orientation="h",
        marker=dict(
            color=df_sorted[val_col],
            colorscale=[[0, PALETTE["green"]], [0.5, PALETTE["blue"]], [1, PALETTE["copper"]]],
            showscale=False,
        ),
        text=[f"{v:.3f}%" if is_percent else str(int(v)) for v in df_sorted[val_col]],
        textposition="outside",
        textfont=dict(size=10, color=PALETTE["text"]),
    ))
    fig.update_layout(**_base_layout(title, height))
    fig.update_xaxes(title_text="% a.a." if is_percent else "Nº de Fundos")
    fig.update_yaxes(tickfont=dict(size=9))
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
        hole=0.55,
        marker=dict(colors=PALETTE["colors"] * 3,
                    line=dict(color=PALETTE["bg"], width=2)),
        textfont=dict(size=10),
        hovertemplate="%{label}<br>%{value} fundos (%{percent})<extra></extra>",
    ))
    fig.update_layout(**_base_layout("Distribuição por Foco de Atuação", height))
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
        colorscale=[[0, PALETTE["teal"]], [0.5, "rgba(21,29,46,0.8)"], [1, PALETTE["copper"]]],
        colorbar=dict(thickness=12, ticksuffix="%", tickfont=dict(size=9)),
        text=np.where(np.isnan(z), "—", np.round(z, 3).astype(str) + "%"),
        texttemplate="%{text}",
        textfont=dict(size=9, color=PALETTE["text_hi"]),
        hovertemplate="%{y}<br>%{x}: %{z:.3f}%<extra></extra>",
    ))
    fig.update_layout(**_base_layout(f"Heatmap — {entity_col.replace('_',' ').title()} × Tipo de Taxa", height))
    fig.update_yaxes(tickfont=dict(size=9), autorange="reversed")
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
            line_width=1.5,
        ))
    fig.update_layout(**_base_layout("Comparativo de Taxas — Boxplots", height))
    fig.update_yaxes(title_text="% a.a.")
    return fig
