"""
Data Loader — FIDC Analytics Platform
Carrega e transforma os dados de regulamentos analisados em df_fidc consolidado.
"""

import os
import re
import numpy as np
import pandas as pd
import streamlit as st

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(__file__))
DATA_FILE      = os.path.join(BASE_DIR, "regulamentos_analisados.xlsx")
RESP_FILE      = os.path.join(BASE_DIR, "responsaveis_fundo.xlsx")

# ─── Mapeamento de tipos de taxa ───────────────────────────────────────────────
TAXA_MAP = [
    ("administra",   "taxa_administracao"),
    ("gestao",       "taxa_gestao"),
    ("gestã",        "taxa_gestao"),
    ("custodia",     "taxa_custodia"),
    ("custódia",     "taxa_custodia"),
    ("performance",  "taxa_performance"),
    ("desempenho",   "taxa_performance"),
    ("distribui",    "taxa_distribuicao"),
    ("servicing",    "taxa_servicing"),
    ("servicer",     "taxa_servicing"),
]

TAXA_COLS = [
    "taxa_administracao",
    "taxa_gestao",
    "taxa_custodia",
    "taxa_performance",
    "taxa_distribuicao",
]

TAXA_LABELS = {
    "taxa_administracao": "Taxa de Administração",
    "taxa_gestao":        "Taxa de Gestão",
    "taxa_custodia":      "Taxa de Custódia",
    "taxa_performance":   "Taxa de Performance",
    "taxa_distribuicao":  "Taxa de Distribuição",
    "taxa_servicing":     "Taxa de Servicing",
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _ascii_lower(s: str) -> str:
    """Lowercase + remove common accents for matching."""
    s = s.lower()
    for a, b in [("ã", "a"), ("á", "a"), ("â", "a"), ("à", "a"),
                 ("ó", "o"), ("ô", "o"), ("ú", "u"), ("é", "e"),
                 ("ê", "e"), ("í", "i"), ("ç", "c"), ("õ", "o")]:
        s = s.replace(a, b)
    return s


def parse_taxa_pct(valor) -> float:
    """Parse raw taxa string → float (% a.a.). Ignores R$ values."""
    if pd.isna(valor):
        return np.nan
    s = str(valor).strip()
    if "%" not in s:
        return np.nan
    # Remove suffixes
    s = re.sub(r"%\s*a\.?\s*a\.?", "", s, flags=re.IGNORECASE)
    s = re.sub(r"%\s*ao\s*ano",    "", s, flags=re.IGNORECASE)
    s = re.sub(r"%\s*a\.?\s*m\.?", "", s, flags=re.IGNORECASE)
    s = s.replace("%", "").strip()
    # Handle ranges "0,10 a 0,50" → mean
    if re.search(r"\s+a\s+", s, re.IGNORECASE):
        parts = re.split(r"\s+a\s+", s, flags=re.IGNORECASE)
        try:
            return float(np.mean([float(p.replace(",", ".").strip()) for p in parts]))
        except Exception:
            return np.nan
    try:
        return float(s.replace(",", "."))
    except Exception:
        return np.nan


def normalize_tipo_taxa(tipo) -> str | None:
    """Normalize tipo_taxa string → standard column name."""
    if pd.isna(tipo):
        return None
    t = _ascii_lower(str(tipo))
    for keyword, col in TAXA_MAP:
        kw = _ascii_lower(keyword)
        if kw in t:
            return col
    return None


# ─── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_raw_data() -> pd.DataFrame:
    return pd.read_excel(DATA_FILE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_responsaveis() -> pd.DataFrame:
    """
    Carrega a tabela auxiliar de responsáveis por fundo.
    Normaliza o CNPJ para string de 14 dígitos (zfill) para garantir join correto.
    """
    df_resp = pd.read_excel(RESP_FILE)
    df_resp["cnpj_str"] = (
        df_resp["ID_CNPJ_Fundo"]
        .astype(str).str.strip().str.zfill(14)
    )
    # Deduplicar: um CNPJ pode ter múltiplas linhas — manter a primeira
    return df_resp.drop_duplicates("cnpj_str").set_index("cnpj_str")


@st.cache_data(ttl=3600, show_spinner=False)
def build_df_fidc() -> pd.DataFrame:
    """
    Build the consolidated df_fidc DataFrame:
    - One row per FIDC (cnpj_tratado)
    - Columns: taxa_administracao, taxa_gestao, taxa_custodia,
               taxa_performance, taxa_distribuicao  (avg of tiers)
    - Plus: nome_fundo, foco_atuacao, data_regulamento,
            administrador, gestor, nome_curto
    """
    df = load_raw_data()

    # Parse & normalize
    df["_taxa_val"] = df["taxa_pct"].apply(parse_taxa_pct)
    df["_tipo_norm"] = df["tipo_taxa"].apply(normalize_tipo_taxa)

    # Filter valid rows
    df_v = df[df["_taxa_val"].notna() & df["_tipo_norm"].notna()].copy()

    # Clamp extreme outliers per tipo: performance can be 10-30%, others capped at 10%
    NON_PERF = ["taxa_administracao", "taxa_gestao", "taxa_custodia",
                "taxa_distribuicao", "taxa_servicing"]
    
    # User Request: remove taxa_performance == 0% and taxa_gestao/taxa_administracao > 5%
    mask_perf_zero = (df_v["_tipo_norm"] == "taxa_performance") & (df_v["_taxa_val"] == 0)
    mask_gest_adm_high = (df_v["_tipo_norm"].isin(["taxa_gestao", "taxa_administracao"])) & (df_v["_taxa_val"] > 5)
    
    df_v = df_v[~mask_perf_zero].copy()
    df_v = df_v[~mask_gest_adm_high].copy()

    mask_perf  = df_v["_tipo_norm"] == "taxa_performance"
    mask_other = df_v["_tipo_norm"].isin(NON_PERF)
    df_v = df_v[~( mask_other & (df_v["_taxa_val"] > 10) )].copy()
    df_v = df_v[~( mask_perf  & (df_v["_taxa_val"] > 50) )].copy()

    # Aggregate tiered rates → mean per fund per tipo
    agg = (
        df_v.groupby(["cnpj_tratado", "_tipo_norm"])["_taxa_val"]
        .mean()
        .reset_index()
    )

    # Pivot → wide
    wide = agg.pivot_table(
        index="cnpj_tratado",
        columns="_tipo_norm",
        values="_taxa_val",
        aggfunc="mean",
    ).reset_index()

    # Metadata: first occurrence per CNPJ
    meta_cols = ["cnpj_tratado", "nome_fundo", "Foco_Atuacao", "data_regulamento"]
    meta = (
        df[meta_cols]
        .drop_duplicates("cnpj_tratado")
        .set_index("cnpj_tratado")
    )

    # Join
    df_fidc = wide.set_index("cnpj_tratado").join(meta).reset_index()
    df_fidc.rename(columns={"Foco_Atuacao": "foco_atuacao"}, inplace=True)

    # ── Administrador / Gestor — tabela auxiliar responsaveis_fundo.xlsx ────────
    # Normaliza CNPJ do fundo para string de 14 dígitos e faz join com a tabela
    # oficial, que contém administrador e gestor corretos por CNPJ.
    df_resp = load_responsaveis()
    df_fidc["_cnpj_str"] = (
        df_fidc["cnpj_tratado"].astype(str).str.strip().str.zfill(14)
    )
    df_fidc["administrador"] = df_fidc["_cnpj_str"].map(
        df_resp["Administrador_Razao_Social"]
    )
    df_fidc["gestor"] = df_fidc["_cnpj_str"].map(
        df_resp["Gestor_Razao_Social"]
    )
    # Fallback: para fundos sem match na tabela auxiliar, tenta derivar do texto
    _fallback_adm = (
        df[df["_tipo_norm"] == "taxa_administracao"]
        .drop_duplicates("cnpj_tratado")
        .set_index("cnpj_tratado")["nome_responsavel"]
    )
    _fallback_ges = (
        df[df["_tipo_norm"] == "taxa_gestao"]
        .drop_duplicates("cnpj_tratado")
        .set_index("cnpj_tratado")["nome_responsavel"]
    )
    _cnpj_key = df_fidc["cnpj_tratado"]
    df_fidc["administrador"] = df_fidc["administrador"].fillna(_cnpj_key.map(_fallback_adm))
    df_fidc["gestor"]        = df_fidc["gestor"].fillna(_cnpj_key.map(_fallback_ges))
    df_fidc.drop(columns=["_cnpj_str"], inplace=True)

    # Ensure all TAXA_COLS exist
    for col in TAXA_COLS:
        if col not in df_fidc.columns:
            df_fidc[col] = np.nan

    # Clean-ups
    df_fidc["nome_fundo"]   = df_fidc["nome_fundo"].fillna("Fundo sem nome")
    df_fidc["foco_atuacao"] = df_fidc["foco_atuacao"].fillna("Não informado")
    df_fidc["data_regulamento"] = pd.to_datetime(
        df_fidc["data_regulamento"], format="%d/%m/%Y", errors="coerce"
    )
    df_fidc["nome_curto"] = df_fidc["nome_fundo"].apply(
        lambda x: str(x)[:55] + "…" if len(str(x)) > 55 else str(x)
    )

    return df_fidc


# ─── Filter helpers ────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame,
                  focos: list | None = None,
                  administradores: list | None = None,
                  gestores: list | None = None) -> pd.DataFrame:
    f = df.copy()
    if focos:
        f = f[f["foco_atuacao"].isin(focos)]
    if administradores:
        f = f[f["administrador"].isin(administradores)]
    if gestores:
        f = f[f["gestor"].isin(gestores)]
    return f


def get_available_taxas(df: pd.DataFrame) -> list[str]:
    return [c for c in TAXA_COLS if c in df.columns and df[c].notna().sum() >= 5]
