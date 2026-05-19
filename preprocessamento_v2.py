"""
preprocessamento_v2.py
======================
Extração aprimorada de PDFs de regulamentos de fundos.

Melhorias em relação à v1:
  - Detecção de títulos via TAMANHO DE FONTE (muito mais confiável que regex)
  - Extração de TABELAS como Markdown (faixas de PL, taxa a.a., etc.)
  - Padrões de título expandidos (árabe, romano, all-caps, sub-seções)
  - Score aprimorado com PENALIZAÇÃO de glossários e seções irrelevantes
  - Inclusão automática do PREÂMBULO (primeiras páginas com CNPJ/nome)
  - Sub-seções numéricas (12.1, 12.2) incluídas quando relevantes
  - Deduplicação de trechos no recorte final
"""

import re
import fitz
import unicodedata
from pathlib import Path
from collections import Counter


# =========================================================
# 1. CONVERTER PDF PARA MARKDOWN (com tabelas + fonte)
# =========================================================

def _format_table_md(table) -> str:
    """Converte um objeto Table do PyMuPDF em Markdown."""
    rows = table.extract()
    if not rows:
        return ""

    lines = []
    header = rows[0]
    # Garante que células None virem string vazia
    header = [str(c or "").strip() for c in header]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for row in rows[1:]:
        cells = [str(c or "").strip() for c in row]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _collect_font_sizes(doc) -> list:
    """Coleta todos os tamanhos de fonte do documento para definir limiares."""
    sizes = []
    for page in doc:
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    s = span.get("size", 0)
                    if s > 0:
                        sizes.append(round(s, 1))
    return sizes


def pdf_to_markdown(pdf_path, output_md=None) -> str:
    """
    Converte PDF para Markdown estruturado.

    Estratégia:
    - Detecta tabelas via PyMuPDF e as formata como tabelas Markdown.
    - Detecta títulos pelo tamanho de fonte (>= limiar_titulo) e os marca com ##.
    - Preserva a sequência leitura top→bottom, left→right.
    """
    doc = fitz.open(pdf_path)

    # Limiar de título: percentil 90 dos tamanhos de fonte
    all_sizes = _collect_font_sizes(doc)
    if all_sizes:
        sorted_sizes = sorted(all_sizes)
        p90_idx = int(len(sorted_sizes) * 0.88)
        limiar_titulo = sorted_sizes[p90_idx]
    else:
        limiar_titulo = 12.0  # fallback

    md_parts = []

    for page_num, page in enumerate(doc, start=1):
        md_parts.append(f"\n\n# Página {page_num}\n")

        # ── Extrair tabelas e marcar suas coordenadas ──────────────────
        tables_in_page = {}  # bbox_y0 -> texto_tabela
        try:
            tabs = page.find_tables()
            for tab in tabs.tables:
                tab_md = _format_table_md(tab)
                if tab_md:
                    y0 = round(tab.bbox[1])
                    tables_in_page[y0] = tab_md
        except Exception:
            pass  # versões antigas do PyMuPDF sem find_tables

        # ── Extrair blocos de texto ────────────────────────────────────
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks = sorted(
            page_dict.get("blocks", []),
            key=lambda b: (round(b["bbox"][1] / 5) * 5, b["bbox"][0]),
        )

        # Rastreia y0 das tabelas já emitidas
        emitted_table_y0s: set = set()

        for block in blocks:
            block_y0 = round(block["bbox"][1])

            # Emite tabela se estiver nesta posição vertical
            for ty0, tab_md in tables_in_page.items():
                if abs(block_y0 - ty0) <= 15 and ty0 not in emitted_table_y0s:
                    md_parts.append("\n" + tab_md + "\n")
                    emitted_table_y0s.add(ty0)

            if block.get("type") != 0:
                continue

            block_lines = []
            for line in block.get("lines", []):
                line_text = ""
                max_size = 0.0
                is_bold = False

                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        line_text += text + " "
                        sz = span.get("size", 0)
                        if sz > max_size:
                            max_size = sz
                        flags = span.get("flags", 0)
                        if flags & 16:  # bold flag
                            is_bold = True

                line_text = line_text.strip()
                if not line_text:
                    continue

                # Marca títulos por tamanho de fonte
                if max_size >= limiar_titulo and len(line_text) <= 200:
                    block_lines.append(f"## {line_text}")
                elif is_bold and len(line_text) <= 200 and max_size >= limiar_titulo * 0.85:
                    block_lines.append(f"**{line_text}**")
                else:
                    block_lines.append(line_text)

            if block_lines:
                md_parts.append("\n".join(block_lines))
                md_parts.append("\n")

        # Emite tabelas que ficaram no final da página e não foram emitidas
        for ty0, tab_md in tables_in_page.items():
            if ty0 not in emitted_table_y0s:
                md_parts.append("\n" + tab_md + "\n")

    md_text = "\n".join(md_parts)

    if output_md:
        Path(output_md).write_text(md_text, encoding="utf-8")

    return md_text


# =========================================================
# 2. NORMALIZAÇÃO
# =========================================================

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode("ASCII")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# 3. DIVIDIR MARKDOWN POR PÁGINAS
# =========================================================

def split_pages(md_text: str) -> list:
    pattern = r"(?=\n# Página\s+\d+)"
    raw_pages = re.split(pattern, md_text)

    pages = []
    for raw in raw_pages:
        raw = raw.strip()
        if not raw:
            continue
        match = re.search(r"# Página\s+(\d+)", raw)
        page_num = int(match.group(1)) if match else None
        pages.append({"pagina": page_num, "texto": raw})

    return pages


# =========================================================
# 4. ACHATAR EM LINHAS
# =========================================================

def flatten_pages(pages: list) -> list:
    rows = []
    global_line = 0
    for page in pages:
        for line in page["texto"].splitlines():
            global_line += 1
            rows.append({
                "global_line": global_line,
                "pagina": page["pagina"],
                "linha": line,
            })
    return rows


# =========================================================
# 5. DETECTOR DE TÍTULOS (EXPANDIDO)
# =========================================================

def is_title_line(line: str) -> bool:
    clean = line.strip()

    if not clean or len(clean) > 200:
        return False

    # Já marcado como título pelo extrator de fonte
    if clean.startswith("## "):
        return True

    # CAPÍTULO II / CAPÍTULO 12
    if re.match(
        r"^CAP[IÍ]TULO\s+([IVXLCDM]+|\d+)",
        clean, re.IGNORECASE
    ):
        return True

    # SEÇÃO / ARTIGO
    if re.match(
        r"^(SE[ÇC][ÃA]O|ARTIGO|ART\.)\s+([IVXLCDM]+|\d+)",
        clean, re.IGNORECASE
    ):
        return True

    # ANEXO / APÊNDICE / SUPLEMENTO
    if re.match(
        r"^(ANEXO|AP[ÊE]NDICE|SUPLEMENTO)\b",
        clean, re.IGNORECASE
    ):
        return True

    # Linhas all-caps curtas (cabeçalhos sem número)
    # Ex: "DAS TAXAS E ENCARGOS"
    alpha_chars = [c for c in clean if c.isalpha()]
    if alpha_chars and len(clean) <= 120:
        upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if upper_ratio >= 0.85 and len(clean.split()) >= 2:
            return True

    # 12. TÍTULO (inteiro, não sub-item)
    m = re.match(r"^(\d+)\.\s+(.+)", clean)
    if m:
        num_str, rest = m.group(1), m.group(2)
        rest_alpha = [c for c in rest if c.isalpha()]
        if rest_alpha:
            up_ratio = sum(1 for c in rest_alpha if c.isupper()) / len(rest_alpha)
            if up_ratio > 0.55 and not clean.endswith("."):
                return True

    # 12.1. Sub-seção (incluída para capturar itens de taxa)
    m2 = re.match(r"^(\d+)\.(\d+)\.?\s+(.+)", clean)
    if m2:
        rest = m2.group(3)
        rest_alpha = [c for c in rest if c.isalpha()]
        if rest_alpha and len(rest) <= 120:
            up_ratio = sum(1 for c in rest_alpha if c.isupper()) / len(rest_alpha)
            if up_ratio > 0.55:
                return True

    return False


# =========================================================
# 6. ENCONTRAR TÍTULOS
# =========================================================

def find_titles(rows: list) -> list:
    titles = []
    for idx, row in enumerate(rows):
        line = row["linha"].strip()
        if is_title_line(line):
            # Remove prefixo ## se presente
            titulo = line.lstrip("# ").strip()
            titles.append({
                "idx": idx,
                "global_line": row["global_line"],
                "pagina": row["pagina"],
                "titulo": titulo,
            })
    return titles


# =========================================================
# 7. CRIAR SEÇÕES ENTRE TÍTULOS
# =========================================================

def build_sections(rows: list, titles: list) -> list:
    sections = []
    for i, title in enumerate(titles):
        start_idx = title["idx"]
        end_idx = titles[i + 1]["idx"] if i + 1 < len(titles) else len(rows)

        section_rows = rows[start_idx:end_idx]
        texto = "\n".join(r["linha"] for r in section_rows).strip()
        paginas = sorted({
            r["pagina"] for r in section_rows if r["pagina"] is not None
        })

        sections.append({
            "titulo": title["titulo"],
            "pagina_inicio": paginas[0] if paginas else None,
            "pagina_fim": paginas[-1] if paginas else None,
            "linha_inicio": title["global_line"],
            "linha_fim": section_rows[-1]["global_line"] if section_rows else None,
            "texto": texto,
        })
    return sections


# =========================================================
# 8. TERMOS RELEVANTES (com pesos)
# =========================================================

TERMOS_ALTA_RELEVANCIA = [
    "taxa de administracao",
    "administracao fiduciaria",
    "taxa de gestao",
    "gestao de recursos",
    "remuneracao da gestora",
    "taxa de custodia",
    "custodia qualificada",
    "taxa global",
    "taxa de performance",
    "taxa de incentivo",
    "taxa de ingresso",
    "taxa de saida",
    "taxa de resgate",
    "taxa de distribuicao",
    "taxa maxima",
    "minimo mensal",
]

TERMOS_MEDIA_RELEVANCIA = [
    "taxa",
    "taxas",
    "remuneracao",
    "encargos",
    "prestadores",
    "administrador",
    "gestor",
    "custodiante",
    "patrimonio liquido",
    "taxa a.a.",
    "r$",
    "%",
]

# Termos que indicam seção de GLOSSÁRIO (penalizar)
TERMOS_GLOSSARIO = [
    '"politica de investimento"',
    '"instrucao cvm',
    '"resolucao da cvm',
    '"rcvm',
    '"regulamento"',
    '"cedente"',
    '"instrumento de aquisicao"',
    '"reserva de caixa"',
]


# =========================================================
# 9. SCORE DE RELEVÂNCIA (aprimorado)
# =========================================================

def score_section(section: dict) -> tuple:
    titulo_norm = normalize_text(section["titulo"])
    texto_norm = normalize_text(section["texto"])
    texto_orig = section["texto"]

    score = 0
    termos_detectados = []

    # Termos de alta relevância: +8 no título, +3 no texto
    for termo in TERMOS_ALTA_RELEVANCIA:
        tn = normalize_text(termo)
        if tn in texto_norm:
            termos_detectados.append(termo)
            score += 8 if tn in titulo_norm else 3

    # Termos de média relevância: +3 no título, +1 no texto
    for termo in TERMOS_MEDIA_RELEVANCIA:
        tn = normalize_text(termo)
        if tn in texto_norm:
            if tn not in [normalize_text(t) for t in termos_detectados]:
                termos_detectados.append(termo)
            score += 3 if tn in titulo_norm else 1

    # Bônus por padrões numéricos de taxa
    if re.search(r"\d+[,\.]\d+\s*%", texto_orig):
        score += 5
    if re.search(r"R\$\s*[\d\.\,]+", texto_orig):
        score += 3

    # Bônus por tabela Markdown detectada
    if "|" in texto_orig and "---" in texto_orig:
        score += 6

    # PENALIDADE: parece glossário (muitas aspas + definições curtas)
    quote_count = texto_orig.count('"')
    if quote_count > 8:
        score -= int(quote_count / 4)

    # PENALIDADE: seções de termos de glossário
    for gt in TERMOS_GLOSSARIO:
        if gt in texto_norm:
            score -= 4

    # PENALIDADE: seção muito curta (< 80 chars) sem percentual
    if len(texto_orig) < 80 and "%" not in texto_orig:
        score -= 2

    return score, sorted(set(termos_detectados))


# =========================================================
# 10. FILTRAR SEÇÕES RELEVANTES
# =========================================================

def filter_relevant_sections(sections: list, min_score: int = 5) -> list:
    relevant = []
    for section in sections:
        score, termos = score_section(section)
        if score >= min_score:
            relevant.append({**section, "score": score, "termos_detectados": termos})

    # Ordena por score desc mas mantém a ordem do documento
    # (não reordena — apenas informa o score no output)
    return relevant


# =========================================================
# 11. PREÂMBULO: primeiras N páginas (sempre incluir)
# =========================================================

def extract_preambulo(pages: list, n_pages: int = 3) -> str:
    """
    Inclui as primeiras N páginas sempre no recorte:
    costumam conter nome do fundo, CNPJ, administrador, gestor.
    """
    partes = []
    for p in pages:
        if p["pagina"] is not None and p["pagina"] <= n_pages:
            partes.append(p["texto"])
    return "\n\n".join(partes)


# =========================================================
# 12. SALVAR RECORTE AUTOMÁTICO
# =========================================================

def save_relevant_sections(
    relevant_sections: list,
    preambulo: str,
    output_path: str,
) -> str:
    recorte_parts = []

    # Preâmbulo sempre no topo
    if preambulo.strip():
        recorte_parts.append("=" * 80)
        recorte_parts.append("# PREÂMBULO (páginas iniciais — CNPJ / Identificação)")
        recorte_parts.append("=" * 80)
        recorte_parts.append(preambulo.strip())

    seen_texts: set = set()

    for sec in relevant_sections:
        # Deduplicação: ignora seções com texto idêntico ao preâmbulo
        snippet = sec["texto"][:300]
        if snippet in seen_texts:
            continue
        seen_texts.add(snippet)

        recorte_parts.append("\n\n" + "=" * 80)
        recorte_parts.append(
            f"# {sec['titulo']}\n"
            f"<!-- páginas: {sec['pagina_inicio']} até {sec['pagina_fim']} | "
            f"score: {sec['score']} | "
            f"termos: {', '.join(sec['termos_detectados'])} -->"
        )
        recorte_parts.append(sec["texto"])

    recorte_text = "\n\n".join(recorte_parts).strip()
    Path(output_path).write_text(recorte_text, encoding="utf-8")
    return recorte_text


# =========================================================
# 13. PIPELINE PRINCIPAL
# =========================================================

def run_pipeline(
    pdf_path: str,
    output_md: str = None,
    output_recorte: str = None,
    min_score: int = 5,
    preambulo_pages: int = 3,
    verbose: bool = True,
) -> dict:
    """
    Executa o pipeline completo e retorna um dict com todos os resultados.
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"  PDF: {pdf_path}")
        print(f"{'='*60}")

    # 1. Converter PDF → Markdown
    print("1. Convertendo PDF → Markdown...") if verbose else None
    md_text = pdf_to_markdown(pdf_path, output_md=output_md)

    # 2. Dividir por páginas e achatar
    pages = split_pages(md_text)
    rows = flatten_pages(pages)

    # 3. Detectar títulos e seções
    titles = find_titles(rows)
    sections = build_sections(rows, titles)

    if verbose:
        print(f"   → {len(pages)} páginas | {len(titles)} títulos | {len(sections)} seções")

    # 4. Filtrar seções relevantes
    relevant_sections = filter_relevant_sections(sections, min_score=min_score)

    # 5. Preâmbulo
    preambulo = extract_preambulo(pages, n_pages=preambulo_pages)

    if verbose:
        print(f"2. Seções relevantes (score >= {min_score}): {len(relevant_sections)}")

    # 6. Salvar recorte
    recorte_text = ""
    if output_recorte:
        recorte_text = save_relevant_sections(
            relevant_sections=relevant_sections,
            preambulo=preambulo,
            output_path=output_recorte,
        )
        print(f"3. Recorte salvo: {output_recorte}") if verbose else None

    # 7. Logs detalhados
    if verbose:
        print("\nTÍTULOS DETECTADOS:")
        print("-" * 60)
        for t in titles:
            print(f"  [p.{t['pagina']:>3} | l.{t['global_line']:>5}] {t['titulo']}")

        print(f"\nSEÇÕES RELEVANTES (top por score):")
        print("-" * 60)
        for sec in sorted(relevant_sections, key=lambda x: -x["score"])[:20]:
            print(
                f"  score={sec['score']:>3} | "
                f"p.{sec['pagina_inicio']}-{sec['pagina_fim']} | "
                f"{sec['titulo'][:80]}"
            )

    return {
        "md_text": md_text,
        "pages": pages,
        "titles": titles,
        "sections": sections,
        "relevant_sections": relevant_sections,
        "preambulo": preambulo,
        "recorte_text": recorte_text,
    }


# =========================================================
# 14. UTILIZAÇÃO
# =========================================================

if __name__ == "__main__":
    BASE = r"C:\Users\bruno.oliveira\Documents\bitbucket\ia\chatv2"

    pdf_path = rf"{BASE}\54519663000146-REG29052025V01-000913322.pdf"
    output_md = rf"{BASE}\saida_teste_regulamento_54519663000146.md"
    output_recorte = rf"{BASE}\recorte_automatico_taxas_54519663000146.md"

    result = run_pipeline(
        pdf_path=pdf_path,
        output_md=output_md,
        output_recorte=output_recorte,
        min_score=5,          # mais restritivo que v1 (era 3)
        preambulo_pages=3,    # inclui as 3 primeiras páginas sempre
        verbose=True,
    )

    print(f"\nMARKDOWN COMPLETO: {output_md}")
    print(f"RECORTE DE TAXAS:  {output_recorte}")
    print(f"Total de caracteres no recorte: {len(result['recorte_text']):,}")
