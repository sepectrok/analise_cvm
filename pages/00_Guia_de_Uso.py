"""Página 0 — Guia de Uso"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

st.set_page_config(page_title="Guia de Uso | Benchmarking Institucional da Solis Investimentos", page_icon="📖", layout="wide")

from components.sidebar import load_css
from components.metrics_cards import page_header

load_css()

page_header("📖", "Guia de Uso do App", "Entenda como navegar e extrair o máximo valor da plataforma")

st.markdown("""
Bem-vindo ao **Benchmarking Institucional da Solis Investimentos**. 
Esta plataforma foi desenvolvida para oferecer uma visão competitiva profunda sobre o mercado de FIDCs (Fundos de Investimento em Direitos Creditórios), com foco especial na estrutura de custos (taxas) praticada pela indústria.
Utilizamos uma leitura guiada por IA para mapear os regulamentos de todos os fundos em atividade registrados pela CVM.
Através desse mapeamento, conseguimos extrair uma visão das características de cada fundo, incluindo informações sobre a taxa de administração e gestão.
Premissas:
- Fundos que possuiam taxas acima de 5% foram tratados como outliers e não foram incluídos na base de dados.
- Fundos com taxas escalares por PL do fundo, foi tirado a média das taxas para composição de análises.
- Todos os regulamentos foram lidos por uma IA e são passíveis de erro, aqui faz-se necessário sempre um olhar analítico.
- O estudo pode ser melhorado por uma futura dupla checagem de dados e ampliação da base de dados.

Para facilitar a análise, fizemos um guia de uso para o usuário.
Abaixo detalhamos a finalidade de cada aba do aplicativo para facilitar sua navegação e análise:

### 1. Visão Geral
**Objetivo:** Oferecer uma visão executiva geral sobre o mercado de FIDCs e o posicionamento da Solis em relação ao restante do mercado.
* **O que você encontra:** KPIs executivos do mercado e da Solis, distribuição geral da taxa de gestão (Solis vs Mercado) e rankings dos maiores gestores e administradores.

### 2. Análise de Taxas
**Objetivo:** Mergulho estatístico detalhado nas estruturas de custos dos fundos.
* **O que você encontra:** Histogramas, boxplots (por segmento) e diagramas de dispersão. É a aba ideal para analisar as distribuições matemáticas, identificar *outliers*.

### 3. Administradores
**Objetivo:** Visão focada na concentração do mercado por entidade administradora.
* **O que você encontra:** Ranking dos administradores com maior número de fundos sob gestão e a distribuição da taxa de administração cobrada. Essencial para mapear os maiores *players* de administração fiduciária.

### 4. Gestores
**Objetivo:** Análise do mercado sob a ótica dos gestores de recursos.
* **O que você encontra:** Semelhante à aba de administradores, mas focada nas gestoras. Exibe rankings de tamanho (quantidade de fundos sob gestão) e comparações das taxas médias de gestão praticadas.

### 5. Foco de Atuação
**Objetivo:** Entender o comportamento do mercado de acordo com a área de atuação do fundo (segmento de crédito).
* **O que você encontra:** Análises mostrando quais segmentos de FIDCs (ex: Multimercado, Consignado, Agronegócio, etc.) apresentam as maiores ou menores taxas. Inclui também uma visão comparativa avançada entre as taxas médias praticadas pela **Solis** versus o **Mercado** em cada um dos segmentos.

### 6. Tabela Analítica
**Objetivo:** Liberdade total para explorar o detalhe, filtrar dados e exportar a base.
* **O que você encontra:** A tabela completa e granular com todos os FIDCs mapeados. Permite realizar buscas avançadas, ordenar colunas, aplicar filtros cruzados adicionais e exportar a base filtrada (em Excel ou CSV) para apresentações ou modelagens externas.

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
