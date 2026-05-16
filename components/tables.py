"""Analytical Tables — FIDC Analytics Platform"""

import io
import numpy as np
import pandas as pd
import streamlit as st
from utils.data_loader import TAXA_COLS, TAXA_LABELS
from utils.formatters import fmt_pct


def _style_pct_cols(val):
    """Color-code percentage values for table display."""
    try:
        v = float(val)
        if v <= 0:
            return ""
        return ""
    except Exception:
        return ""


def render_analytical_table(df: pd.DataFrame, key: str = "tbl"):
    """Full analytical table with search, sort and export."""
    display_cols = ["nome_curto", "foco_atuacao", "administrador", "gestor"] + \
                   [c for c in TAXA_COLS if c in df.columns]

    df_disp = df[display_cols].copy()
    df_disp.rename(columns={
        "nome_curto":     "Fundo",
        "foco_atuacao":   "Foco",
        "administrador":  "Administrador",
        "gestor":         "Gestor",
        **{c: TAXA_LABELS.get(c, c) for c in TAXA_COLS},
    }, inplace=True)

    # Search
    search = st.text_input("🔍 Busca por nome do fundo, administrador ou gestor",
                           key=f"{key}_search", placeholder="Digite para filtrar...")
    if search:
        mask = df_disp.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df_disp = df_disp[mask]

    st.markdown(f"<small style='color:var(--text-muted)'>{len(df_disp)} registros</small>",
                unsafe_allow_html=True)

    # Column config for pct formatting
    col_cfg = {
        "Fundo":         st.column_config.TextColumn(width="large"),
        "Foco":          st.column_config.TextColumn(width="medium"),
        "Administrador": st.column_config.TextColumn(width="medium"),
        "Gestor":        st.column_config.TextColumn(width="medium"),
    }
    for c in TAXA_COLS:
        lbl = TAXA_LABELS.get(c, c)
        if lbl in df_disp.columns:
            col_cfg[lbl] = st.column_config.NumberColumn(
                lbl, format="%.3f%%", width="small"
            )

    st.dataframe(df_disp, use_container_width=True, hide_index=True,
                 column_config=col_cfg, height=460)

    return df_disp


def render_entity_ranking(df_agg: pd.DataFrame, entity_col: str,
                           count_col: str = "n_fundos", key: str = "rank", taxa_col_to_show: str = None):
    """Ranking table for admins/gestors."""
    taxa_labels = {c: TAXA_LABELS.get(c, c).replace("Taxa de ", "") for c in TAXA_COLS}
    
    if taxa_col_to_show and taxa_col_to_show in df_agg.columns:
        present = [taxa_col_to_show]
    else:
        present = [c for c in TAXA_COLS if c in df_agg.columns]
        
    rename_map = {entity_col: "Entidade", count_col: "Nº Fundos"}
    rename_map.update({c: taxa_labels[c] for c in present})

    df_disp = df_agg.rename(columns=rename_map).copy()
    
    display_cols = ["Entidade", "Nº Fundos"] + [taxa_labels[c] for c in present]
    df_disp = df_disp[display_cols]

    col_cfg = {"Entidade": st.column_config.TextColumn(width="large"),
               "Nº Fundos": st.column_config.NumberColumn(width="small", format="%d")}
    for c in present:
        col_cfg[taxa_labels[c]] = st.column_config.NumberColumn(
            taxa_labels[c], format="%.3f%%", width="small"
        )

    st.dataframe(df_disp, use_container_width=True, hide_index=True,
                 column_config=col_cfg, height=400)


def export_buttons(df: pd.DataFrame, label: str = "dados_fidc"):
    """CSV and Excel download buttons."""
    c1, c2 = st.columns(2)

    csv_data = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
    with c1:
        st.download_button(
            "⬇ Exportar CSV",
            data=csv_data.encode("utf-8-sig"),
            file_name=f"{label}.csv",
            mime="text/csv",
        )

    with c2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="FIDC Analytics")
        buf.seek(0)
        st.download_button(
            "⬇ Exportar Excel",
            data=buf.read(),
            file_name=f"{label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
