"""Página 0 — Guia de Uso"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st


from components.sidebar import load_css
from components.metrics_cards import page_header

load_css()

page_header("📖", "Guia de Uso do App", "Entenda como navegar e extrair o máximo valor da plataforma")

st.markdown("""
O **Benchmarking Institucional Solis** é uma plataforma analítica desenvolvida para monitorar o posicionamento competitivo e a estrutura de custos do mercado de FIDCs.

Os dados apresentados são extraídos de regulamentos da CVM por meio de processamento automatizado via IA, requerendo validação analítica contínua.

### Premissas Metodológicas
- **Outliers:** Fundos com taxas superiores a 5% a.a. foram excluídos da base para evitar distorções estatísticas.
- **Taxas Escalares:** Em regulamentos com taxas vinculadas ao Patrimônio Líquido, adotou-se a média das faixas aplicáveis.
- **Auditoria de Dados:** O modelo de extração possui margem de erro inerente (ex: campos vazios ou classificações incorretas). Recomenda-se o cruzamento de informações atípicas com as fontes oficiais.

### Navegação e Funcionalidades

* **1. Visão Geral:** Painel executivo com os principais indicadores (KPIs) de mercado e o posicionamento relativo da Solis.
* **2. Análise de Taxas:** Painel estatístico dedicado à distribuição matemática de custos, histogramas e identificação de anomalias.
* **3. Administradores:** Mapeamento de concentração fiduciária (*market share*) e comparativo de taxas de administração.
* **4. Gestores:** Cenário competitivo das gestoras de recursos, englobando volume de fundos sob gestão e estrutura de cobrança.
* **5. Foco de Atuação:** Segmentação setorial (ex: Agronegócio, Multimercado) para análise comparativa de prêmios e custos por área de crédito.
* **6. Tabela Analítica:** Base granular de todos os FIDCs mapeados, com suporte a filtros cruzados e exportação de dados (Excel/CSV) para modelagens externas.

---
""",
#<div class="insight-card info" style="margin-top: 30px;">
#    <div class="ic-icon">💡</div>
#    <div>
#        <div class="ic-title">Dica de Navegação: Filtros Globais</div>
#        <div class="ic-text">
#            Utilize os <strong>filtros da barra lateral esquerda</strong> para refinar a sua amostra (por exemplo, analisar apenas fundos de um foco específico, ou definir um tamanho mínimo de patrimônio). Os filtros aplicados na barra lateral refletem simultaneamente em <strong>todas as abas e gráficos</strong> do aplicativo.
#        </div>
#    </div>
#</div>
 unsafe_allow_html=True)
