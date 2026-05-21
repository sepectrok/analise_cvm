"""
app_pipeline.py
================
Pipeline Streamlit para extração de taxas de regulamentos de fundos.

Aba 1 — Pré-processamento:
  • Upload de PDFs (múltiplos) ou leitura de pasta
  • Converte PDF → .md completo  → regulamento_convertido_md/
  • Gera recorte de seções relevantes → regulamento_recorte_md/

Aba 2 — Extração LLM:
  • Lista arquivos de regulamento_recorte_md/
  • Pula arquivos já processados (verifica data_raw_process/data_raw_process.xlsx)
  • Envia ao LLM, salva resultado incremental no Excel
  • Registra custo por requisição (gpt-4o-mini pricing)
"""

import os
import sys
import json
import re
import datetime
import hashlib
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# Garante importação do preprocessamento_v2.py no mesmo diretório
sys.path.insert(0, str(Path(__file__).parent))
from preprocessamento_v2 import run_pipeline

load_dotenv()

# =========================================================
# CONSTANTES
# =========================================================

MODEL = "gpt-4o-mini"
# Preços gpt-4o-mini (USD por token)
PRICE_INPUT_PER_TOKEN  = 0.150 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 0.600 / 1_000_000

SYSTEM_PROMPT = """
Você é um especialista em leitura de regulamentos de fundos no Brasil, com foco em mapeamento de taxas e identificação de prestadores.

Sua tarefa é ler o regulamento enviado e construir uma tabela estruturada.

Objetivo principal:
1. Identificar o fundo e a data de validade/assinatura do regulamento (data_regulamento).
   - data_regulamento DEVE estar no formato DD/MM/AAAA (ex: 30/01/2026). Nunca deixe em outro formato.
2. Identificar gestor, administrador e custodiante.
3. Identificar TODAS as taxas cobradas pelo fundo. Priorize:
   - "Taxa de Administração" (sinônimos: administração fiduciária, taxa adm, controladoria, escrituração)
   - "Taxa de Gestão" (sinônimos: remuneração da gestora, gestão de recursos)
   - "Taxa de Custódia" (custódia qualificada)
   - "Taxa Global" (engloba adm + gestão)
   - "Taxa de Performance" / incentivo
   - "Taxa de Ingresso" / entrada
   - "Taxa de Saída" / resgate
   - "Taxa de Distribuição" máxima

ATENÇÃO CRÍTICA PARA FAIXAS (TIERS) DE TAXA:
- Se a taxa for escalonada em faixas (ex: faixas de Patrimônio Líquido, "Até 10 milhões", "Acima de 10 milhões"), você DEVE criar UMA LINHA (registro JSON) SEPARADA PARA CADA FAIXA. Não agrupe múltiplas faixas no mesmo registro.
- faixa_pl_texto = o texto EXATO da faixa de Patrimônio Líquido (PL) a qual a taxa se refere (ex: "Até R$ 50.000.000,00", "Acima de R$ 100 milhões"). Se não houver, deixe em branco.
- valor_minimo = limite INFERIOR numérico da faixa de PL, OU o valor mínimo monetário da taxa (ex: "16000.00" se houver valor mínimo mensal). Se não houver, deixe em branco.
- valor_maximo = limite SUPERIOR numérico da faixa de PL, OU o valor máximo monetário da taxa. Se for "acima de" ou não houver, deixe em branco.
- inequacao_valor = operador lógico ou texto da faixa extraído do original (ex: ">", ">=", "<", "<=", "entre", "Até", "Acima de"). Se não houver faixa, deixe em branco.

Exemplo de estruturação de faixas de PL:
Se o texto diz "A taxa é 1,00% até R$ 50 milhões e 0,80% acima de R$ 50 milhões":
  Linha 1: taxa_pct="1,00%", faixa_pl_texto="até R$ 50 milhões", valor_minimo="", valor_maximo="50000000", inequacao_valor="<="
  Linha 2: taxa_pct="0,80%", faixa_pl_texto="acima de R$ 50 milhões", valor_minimo="50000000", valor_maximo="", inequacao_valor=">"

OUTRAS REGRAS CRÍTICAS:
- O campo taxa_pct deve conter apenas a taxa limpa (ex: "0,63% a.a.").
- tipo_taxa: copie EXATAMENTE o nome da taxa como aparece no texto (ex: "Taxa de Administração", "Taxa de Gestão"). Não normalize.
- texto_regulamento_relacao_taxa: OBRIGATÓRIO. Copie o trecho do regulamento que justifica a taxa/faixa desta linha. Se a taxa estiver em uma tabela, copie o cabeçalho e a linha exata da tabela correspondente a essa faixa.
- nome_responsavel e cnpj_responsavel: identifique quem recebe a taxa. ATENÇÃO: Busque rigorosamente no texto as definições de "Gestor", "Administrador", "Custodiante" (mesmo que estejam no formato de tabela de Termos Definidos) e preencha esses dados na taxa correspondente (ex: colocar o nome do Administrador na Taxa de Administração).
- Nunca invente dados; deixe campo vazio se não encontrar.

Saída — JSON com chave "linhas". Cada item:
- cnpj_fundo
- nome_fundo
- data_regulamento  (formato DD/MM/AAAA)
- texto_regulamento_relacao_taxa  (trecho obrigatório onde a taxa aparece)
- taxa_pct
- faixa_pl_texto
- valor_minimo
- valor_maximo
- inequacao_valor
- cnpj_responsavel
- nome_responsavel
- tipo_taxa  (nome exato do texto)
- taxa_valor_original
- pagina_referencia
- observacoes_modelo

Se não encontrar nada, retorne {"linhas": []}.
""".strip()

OUTPUT_COLUMNS = [
    "arquivo_origem", "cnpj_fundo", "nome_fundo", "data_regulamento",
    "texto_regulamento_relacao_taxa", "taxa_pct", "faixa_pl_texto", "valor_minimo", "valor_maximo",
    "inequacao_valor",
    "cnpj_responsavel", "nome_responsavel", "tipo_taxa", "taxa_valor_original",
    "pagina_referencia", "observacoes_modelo",
    "data_processamento", "tempo_process", "modelo_llm",
    "custo_usd", "tokens_input", "tokens_output",
]

# =========================================================
# HELPERS
# =========================================================

def get_dirs(base: Path) -> dict:
    dirs = {
        "convertido":  base / "regulamento_convertido_md",
        "recorte":     base / "regulamento_recorte_md",
        "raw":         base / "data_raw_process",
        "log_preproc": base / "data_raw_process_md",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def excel_path(dirs: dict) -> Path:
    return dirs["raw"] / "data_raw_process.xlsx"


def load_registry(dirs: dict) -> pd.DataFrame:
    xls = excel_path(dirs)
    if xls.exists():
        print(xls)
        return pd.read_excel(xls, dtype=str)
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def save_registry(df: pd.DataFrame, dirs: dict):
    df.to_excel(excel_path(dirs), index=False)


def already_processed(arquivo_origem: str, registry: pd.DataFrame) -> bool:
    if registry.empty or "arquivo_origem" not in registry.columns:
        return False
    return arquivo_origem in registry["arquivo_origem"].values


def extract_json_from_text(raw: str) -> dict:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {"linhas": []}


def chunk_text(text: str, max_chars: int = 90_000) -> list:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while text:
        chunk = text[:max_chars]
        break_at = chunk.rfind("\n\n")
        if break_at > max_chars // 2:
            chunk = chunk[:break_at]
        chunks.append(chunk)
        text = text[len(chunk):]
    return chunks

LOG_PREPROC_COLUMNS = [
    "ID_CNPJ_Fundo", "Nome_Documento", "Secao_Relevante",
    "Chars_Recorte", "Data_Process", "Tempo_Process", "Status",
]


def preproc_log_path(dirs: dict) -> Path:
    return dirs["log_preproc"] / "log_preprocessamento.xlsx"


def load_preproc_log(dirs: dict) -> pd.DataFrame:
    p = preproc_log_path(dirs)
    if p.exists():
        return pd.read_excel(p, dtype=str)
    return pd.DataFrame(columns=LOG_PREPROC_COLUMNS)


def append_preproc_log(dirs: dict, row: dict):
    """Acrescenta uma linha ao log de pre-processamento e salva."""
    df = load_preproc_log(dirs)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_excel(preproc_log_path(dirs), index=False)


def extract_cnpj_from_stem(stem: str) -> str:
    """Extrai o CNPJ (14 dígitos) do nome do arquivo (ex: Regulamento_05754060000113_...)."""
    # Busca sequência de exatamente 14 dígitos no nome do arquivo
    match = re.search(r'\b(\d{14})\b', stem)
    if match:
        return match.group(1)
    # Fallback: pega todos os dígitos e recorta 14
    digits = re.sub(r"\D", "", stem)
    return digits[:14] if len(digits) >= 14 else digits


def normalize_date(value: str) -> str:
    """Tenta normalizar qualquer formato de data para DD/MM/AAAA."""
    if not value:
        return value
    # Já está no formato correto
    if re.match(r'^\d{2}/\d{2}/\d{4}$', value.strip()):
        return value.strip()
    # Tenta formatos comuns: AAAA-MM-DD, DD-MM-AAAA, DD.MM.AAAA
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(value.strip(), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return value.strip()  # devolve como veio se não conseguir parsear


# =========================================================
# APP
# =========================================================

st.set_page_config(
    page_title="Pipeline de Extração de Taxas",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Pipeline de Extração de Taxas — Regulamentos CVM")

# Sidebar — configurações globais
with st.sidebar:
    st.header("⚙️ Configurações")
    base_dir_input = st.text_input(
        "Diretório base do projeto",
        value=str(Path(__file__).parent),
        help="Pasta raiz onde serão criados os subdiretórios do pipeline.",
    )
    BASE = Path(base_dir_input)
    DIRS = get_dirs(BASE)

    model_choice = st.selectbox(
        "Modelo LLM",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
        index=0,
    )
    min_score = st.slider("Score mínimo de relevância (pré-processamento)", 3, 10, 5)
    preambulo_pages = st.slider("Páginas do preâmbulo sempre incluídas", 1, 5, 3)

    st.markdown("---")
    st.caption(f"convertido: `{DIRS['convertido'].name}/`")
    st.caption(f"recorte:    `{DIRS['recorte'].name}/`")
    st.caption(f"dados:      `{DIRS['raw'].name}/`")
    st.caption(f"log:        `{DIRS['log_preproc'].name}/`")

tab1, tab2 = st.tabs(["1) Pré-processamento (PDF → MD)", "2) Extração LLM"])

# ===========================================================
# ABA 1 — PRÉ-PROCESSAMENTO
# ===========================================================

with tab1:
    st.subheader("Converter PDFs em Markdown e gerar recortes")
    st.write(
        "Faça upload de PDFs ou informe uma pasta. "
        "O pipeline gera o `.md` completo em `regulamento_convertido_md/` "
        "e o recorte temático em `regulamento_recorte_md/`."
    )

    modo_entrada = st.radio(
        "Origem dos PDFs:",
        ["Upload de arquivos", "Pasta no servidor"],
        horizontal=True,
    )

    pdf_queue: list = []  # lista de (bytes, nome_stem)

    if modo_entrada == "Upload de arquivos":
        uploads = st.file_uploader(
            "Selecione os PDFs", type=["pdf"], accept_multiple_files=True
        )
        if uploads:
            for f in uploads:
                pdf_queue.append((f.read(), Path(f.name).stem))
            st.info(f"{len(pdf_queue)} arquivo(s) prontos para processar.")

    else:
        pasta_pdf = st.text_input(
            "Caminho da pasta com PDFs",
            value=str(BASE / "teste_regulamento_pdf"),
        )
        if st.button("Listar PDFs na pasta"):
            p = Path(pasta_pdf)
            if p.is_dir():
                pdfs = sorted(p.glob("*.pdf"))
                st.session_state["pasta_pdfs"] = [(pdf.read_bytes(), pdf.stem) for pdf in pdfs]
                st.success(f"{len(pdfs)} PDF(s) encontrados.")
            else:
                st.error("Pasta não encontrada.")
        if "pasta_pdfs" in st.session_state:
            pdf_queue = st.session_state["pasta_pdfs"]
            st.write(f"**{len(pdf_queue)} PDF(s) na fila:**")
            for _, stem in pdf_queue:
                st.caption(f"  • {stem}.pdf")

    if pdf_queue:
        st.markdown("---")
        sobrescrever = st.checkbox(
            "Sobrescrever arquivos já convertidos", value=False
        )

        if st.button("Iniciar Pre-processamento", type="primary"):
            prog = st.progress(0)
            log_area = st.empty()
            logs = []

            for i, (pdf_bytes, stem) in enumerate(pdf_queue):
                out_md      = DIRS["convertido"] / f"{stem}.md"
                out_recorte = DIRS["recorte"]    / f"{stem}.md"

                if not sobrescrever and out_recorte.exists():
                    logs.append(f"Pulado (ja existe): `{stem}`")
                    log_area.text("\n".join(logs))
                    prog.progress((i + 1) / len(pdf_queue))
                    continue

                logs.append(f"Processando: `{stem}` ...")
                log_area.text("\n".join(logs))

                # Salva PDF temporariamente para o run_pipeline
                tmp_pdf = DIRS["raw"] / f"_tmp_{stem}.pdf"
                tmp_pdf.write_bytes(pdf_bytes)

                inicio = datetime.datetime.now()
                status = "NOK"
                n_sec, chars = 0, 0

                try:
                    result = run_pipeline(
                        pdf_path=str(tmp_pdf),
                        output_md=str(out_md),
                        output_recorte=str(out_recorte),
                        min_score=min_score,
                        preambulo_pages=preambulo_pages,
                        verbose=False,
                    )
                    n_sec  = len(result["relevant_sections"])
                    chars  = len(result["recorte_text"])
                    status = "OK"
                    logs[-1] = (
                        f"OK `{stem}` - {n_sec} secoes, {chars:,} chars"
                    )
                except Exception as e:
                    logs[-1] = f"ERRO `{stem}`: {e}"
                finally:
                    tmp_pdf.unlink(missing_ok=True)

                fim = datetime.datetime.now()
                tempo_s = round((fim - inicio).total_seconds(), 2)

                # Grava linha no log de pré-processamento
                append_preproc_log(DIRS, {
                    "ID_CNPJ_Fundo":  extract_cnpj_from_stem(stem),
                    "Nome_Documento": stem,
                    "Secao_Relevante": n_sec,
                    "Chars_Recorte":  chars,
                    "Data_Process":   inicio.strftime("%Y-%m-%d %H:%M:%S"),
                    "Tempo_Process":  f"{tempo_s}s",
                    "Status":         status,
                })

                log_area.text("\n".join(logs))
                prog.progress((i + 1) / len(pdf_queue))

            st.success("Pre-processamento concluido!")

    # Exibe status dos diretórios
    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 📁 regulamento_convertido_md/")
        mds = sorted(DIRS["convertido"].glob("*.md"))
        if mds:
            for f in mds:
                st.caption(f"• {f.name}  ({f.stat().st_size/1024:.1f} KB)")
        else:
            st.info("Nenhum arquivo convertido ainda.")
    with col_b:
        st.markdown("#### 📁 regulamento_recorte_md/")
        recortes = sorted(DIRS["recorte"].glob("*.md"))
        if recortes:
            for f in recortes:
                st.caption(f"• {f.name}  ({f.stat().st_size/1024:.1f} KB)")
        else:
            st.info("Nenhum recorte gerado ainda.")

    # Log de pre-processamento
    st.markdown("---")
    st.markdown("#### Log de Pre-processamento (`data_raw_process_md/`)")
    df_log = load_preproc_log(DIRS)
    if not df_log.empty:
        def color_status(val):
            return "background-color: #d4edda" if val == "OK" else "background-color: #f8d7da"
        st.dataframe(
            df_log.style.applymap(color_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )
        col_ok, col_nok, col_dl = st.columns(3)
        with col_ok:
            st.metric("OK", (df_log["Status"] == "OK").sum())
        with col_nok:
            st.metric("NOK", (df_log["Status"] == "NOK").sum())
        with col_dl:
            if preproc_log_path(DIRS).exists():
                st.download_button(
                    "Baixar log_preprocessamento.xlsx",
                    data=preproc_log_path(DIRS).read_bytes(),
                    file_name="log_preprocessamento.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
    else:
        st.info("Nenhum pre-processamento registrado ainda.")


# ===========================================================
# ABA 2 — EXTRAÇÃO LLM
# ===========================================================

with tab2:
    st.subheader("Extrair taxas via LLM dos arquivos recortados")

    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY não encontrada no .env")
        st.stop()

    client = OpenAI(api_key=api_key)

    # Carrega registry (Excel de controle)
    registry = load_registry(DIRS)

    recortes = sorted(DIRS["recorte"].glob("*.md"))

    if not recortes:
        st.info("Nenhum recorte encontrado. Execute o Pré-processamento primeiro.")
    else:
        # Monta tabela de status
        status_rows = []
        for f in recortes:
            stem = f.stem
            proc = already_processed(stem, registry)
            status_rows.append({
                "Arquivo": stem,
                "Tamanho": f"{f.stat().st_size/1024:.1f} KB",
                "Status": "✅ Processado" if proc else "⏳ Pendente",
            })
        df_status = pd.DataFrame(status_rows)

        col_stat, col_btn = st.columns([3, 1])
        with col_stat:
            st.dataframe(df_status, use_container_width=True, hide_index=True)
        with col_btn:
            pendentes = [r["Arquivo"] for r in status_rows if r["Status"] == "⏳ Pendente"]
            st.metric("Total", len(recortes))
            st.metric("Pendentes", len(pendentes))
            st.metric("Processados", len(recortes) - len(pendentes))

        st.markdown("---")

        # Seleção de arquivos
        opcao = st.radio(
            "Quais arquivos processar?",
            ["Apenas pendentes", "Selecionar manualmente", "Todos (reprocessar)"],
            horizontal=True,
        )

        if opcao == "Apenas pendentes":
            selecionados = pendentes
        elif opcao == "Selecionar manualmente":
            selecionados = st.multiselect(
                "Escolha os arquivos:",
                options=[f.stem for f in recortes],
                default=pendentes,
            )
        else:
            selecionados = [f.stem for f in recortes]

        if not selecionados:
            st.info("Nenhum arquivo selecionado.")
        else:
            st.write(f"**{len(selecionados)} arquivo(s) para processar.**")

            if st.button("🚀 Iniciar Extração LLM", type="primary"):
                prog2 = st.progress(0)
                resultado_area = st.empty()
                todas_novas = []
                custo_total = 0.0
                # Guarda stems já processados NESTA execução para evitar duplicatas
                stems_desta_execucao: set = set()

                for i, stem in enumerate(selecionados):
                    # --- Dedup: pula se já processou nesta execução ---
                    if stem in stems_desta_execucao:
                        st.warning(f"Arquivo `{stem}` já foi processado nesta execução — ignorando duplicata.")
                        prog2.progress((i + 1) / len(selecionados))
                        continue

                    md_path = DIRS["recorte"] / f"{stem}.md"
                    if not md_path.exists():
                        st.warning(f"Arquivo não encontrado: {md_path.name}")
                        prog2.progress((i + 1) / len(selecionados))
                        continue

                    with st.spinner(f"Extraindo: `{stem}`..."):
                        inicio_llm = datetime.datetime.now()
                        md_text = md_path.read_text(encoding="utf-8")
                        chunks = chunk_text(md_text)
                        linhas_arquivo = []
                        tok_in_total = 0
                        tok_out_total = 0

                        for ci, chunk in enumerate(chunks):
                            try:
                                completion = client.chat.completions.create(
                                    model=model_choice,
                                    temperature=0.0,
                                    response_format={"type": "json_object"},
                                    messages=[
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {
                                            "role": "user",
                                            "content": (
                                                f"Analise o regulamento (parte {ci+1}/{len(chunks)}) "
                                                f"e extraia o JSON com as taxas:\n\n{chunk}"
                                            ),
                                        },
                                    ],
                                )
                                raw = completion.choices[0].message.content or '{"linhas":[]}'
                                parsed = extract_json_from_text(raw)
                                linhas_arquivo.extend(parsed.get("linhas", []))
                                tok_in_total  += completion.usage.prompt_tokens
                                tok_out_total += completion.usage.completion_tokens
                            except Exception as e:
                                st.error(f"Erro no chunk {ci+1} de `{stem}`: {e}")

                        custo = (
                            tok_in_total  * PRICE_INPUT_PER_TOKEN +
                            tok_out_total * PRICE_OUTPUT_PER_TOKEN
                        )
                        custo_total += custo
                        fim_llm = datetime.datetime.now()
                        agora = fim_llm.strftime("%Y-%m-%d %H:%M:%S")
                        tempo_s = round((fim_llm - inicio_llm).total_seconds(), 2)

                        # CNPJ do nome do arquivo (fallback)
                        cnpj_do_arquivo = extract_cnpj_from_stem(stem)

                        novas_deste_arquivo = []
                        for r in linhas_arquivo:
                            row = {col: r.get(col, "") for col in OUTPUT_COLUMNS}
                            row["arquivo_origem"]     = stem
                            # Fallback CNPJ: se a LLM não trouxe, usa o do filename
                            if not row.get("cnpj_fundo", "").strip():
                                row["cnpj_fundo"] = cnpj_do_arquivo
                            # Normaliza data_regulamento para DD/MM/AAAA
                            row["data_regulamento"]  = normalize_date(row.get("data_regulamento", ""))
                            row["data_processamento"] = agora
                            row["tempo_process"]      = f"{tempo_s}s"
                            row["modelo_llm"]         = model_choice
                            row["custo_usd"]          = round(custo / max(len(linhas_arquivo), 1), 8)
                            row["tokens_input"]       = tok_in_total
                            row["tokens_output"]      = tok_out_total
                            novas_deste_arquivo.append(row)

                        todas_novas.extend(novas_deste_arquivo)
                        stems_desta_execucao.add(stem)

                        # Salva incrementalmente (remove versão anterior do mesmo arquivo)
                        registry = load_registry(DIRS)
                        registry = registry[registry["arquivo_origem"] != stem]
                        novas_df = pd.DataFrame(novas_deste_arquivo)
                        registry = pd.concat([registry, novas_df], ignore_index=True)
                        save_registry(registry, DIRS)

                        st.success(
                            f"✅ `{stem}` — {len(linhas_arquivo)} linha(s) | "
                            f"custo: ${custo:.6f} | "
                            f"tokens: {tok_in_total}+{tok_out_total}"
                        )

                    prog2.progress((i + 1) / len(selecionados))

                st.markdown(f"### Concluído — Custo total: **${custo_total:.5f}**")

        # Exibe dados consolidados
        st.markdown("---")
        st.subheader("📊 Base consolidada (data_raw_process.xlsx)")
        registry = load_registry(DIRS)

        if not registry.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_tipo = st.multiselect(
                    "Filtrar tipo_taxa:",
                    options=sorted(registry["tipo_taxa"].dropna().unique()),
                )
            with col_f2:
                filtro_fundo = st.multiselect(
                    "Filtrar nome_fundo:",
                    options=sorted(registry["nome_fundo"].dropna().unique()),
                )

            df_view = registry.copy()
            if filtro_tipo:
                df_view = df_view[df_view["tipo_taxa"].isin(filtro_tipo)]
            if filtro_fundo:
                df_view = df_view[df_view["nome_fundo"].isin(filtro_fundo)]

            st.dataframe(df_view, use_container_width=True, hide_index=True)

            # Métricas de custo
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                total_custo = pd.to_numeric(registry["custo_usd"], errors="coerce").sum()
                st.metric("Custo total acumulado", f"${total_custo:.5f}")
            with col_m2:
                st.metric("Fundos processados", registry["arquivo_origem"].nunique())
            with col_m3:
                st.metric("Linhas extraídas", len(registry))

            # Download
            xls_bytes = excel_path(DIRS).read_bytes()
            st.download_button(
                "⬇️ Baixar data_raw_process.xlsx",
                data=xls_bytes,
                file_name="data_raw_process.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Nenhuma extração realizada ainda.")
