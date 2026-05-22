"""Sidebar — Solis Investimentos Platform — Premium v2"""

import streamlit as st
import pandas as pd
import os


def load_css():
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles", "main.css")
    with open(css_path, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # ── Botão flutuante para abrir/fechar a sidebar ──────────────────────────────
    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function() {
        var doc = window.parent.document;
        var win = window.parent;

        // Dispara click compatível com React (event bubbling no root)
        function reactClick(el) {
            el.dispatchEvent(new MouseEvent('click', {
                bubbles: true, cancelable: true, view: win
            }));
        }

        function getSidebarWidth() {
            var sb = doc.querySelector('[data-testid="stSidebar"]');
            return sb ? sb.getBoundingClientRect().width : 0;
        }

        function toggleSidebar() {
            var sbWidth = getSidebarWidth();
            var clicked = false;

            if (sbWidth > 50) {
                // ── Sidebar ABERTA: procurar botão de fechar ──────────────────
                // Em Streamlit 1.x, o botão de colapso dentro da sidebar usa
                // data-testid="baseButton-header"
                var closeCandidates = [
                    '[data-testid="stSidebar"] [data-testid="baseButton-header"]',
                    '[data-testid="stSidebar"] button[aria-label]',
                    '[data-testid="stSidebarContent"] button',
                    '[data-testid="stSidebar"] button',
                ];
                for (var i = 0; i < closeCandidates.length && !clicked; i++) {
                    var els = doc.querySelectorAll(closeCandidates[i]);
                    for (var j = 0; j < els.length && !clicked; j++) {
                        var r = els[j].getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            reactClick(els[j]);
                            clicked = true;
                        }
                    }
                }
            } else {
                // ── Sidebar FECHADA: procurar botão de abrir ──────────────────
                var openCandidates = [
                    '[data-testid="collapsedControl"] button',
                    '[data-testid="stSidebarCollapsedControl"] button',
                    '[data-testid="collapsedControl"]',
                    'header [data-testid="baseButton-header"]',
                    'header button',
                ];
                for (var k = 0; k < openCandidates.length && !clicked; k++) {
                    var els2 = doc.querySelectorAll(openCandidates[k]);
                    for (var l = 0; l < els2.length && !clicked; l++) {
                        reactClick(els2[l]);
                        clicked = true;
                    }
                }
            }

            // Fallback: atalho de teclado nativo do Streamlit ('[' fecha/abre sidebar)
            if (!clicked) {
                doc.body.dispatchEvent(new KeyboardEvent('keydown', {
                    key: '[', code: 'BracketLeft', keyCode: 219, which: 219,
                    bubbles: true, cancelable: true
                }));
            }

            // Atualiza visual do botão após toggle
            setTimeout(updateBtnIcon, 200);
        }

        function updateBtnIcon() {
            var btn = doc.getElementById('_solis_sidebar_toggle');
            if (!btn) return;
            btn.innerHTML = getSidebarWidth() > 50 ? '&#8249;' : '&#9776;';
            btn.title = getSidebarWidth() > 50 ? 'Fechar menu lateral' : 'Abrir menu lateral';
        }

        function createToggleBtn() {
            if (doc.getElementById('_solis_sidebar_toggle')) {
                updateBtnIcon();
                return;
            }

            var btn = doc.createElement('button');
            btn.id = '_solis_sidebar_toggle';
            btn.innerHTML = '&#9776;';
            btn.title = 'Abrir / Fechar menu lateral';
            btn.style.cssText = [
                'position:fixed', 'top:10px', 'left:10px',
                'z-index:2147483647', 'width:36px', 'height:36px',
                'background:#12141E', 'color:#94A3B8',
                'border:1px solid rgba(148,163,184,0.15)',
                'border-radius:8px', 'font-size:18px', 'cursor:pointer',
                'display:flex', 'align-items:center', 'justify-content:center',
                'box-shadow:0 2px 8px rgba(0,0,0,0.4)',
                'transition:background 0.2s,color 0.2s,border-color 0.2s',
                'line-height:1'
            ].join(';');

            btn.onmouseover = function() {
                btn.style.background = '#1A1D2B';
                btn.style.color = '#F1F5F9';
                btn.style.borderColor = 'rgba(59,130,246,0.3)';
            };
            btn.onmouseout = function() {
                btn.style.background = '#12141E';
                btn.style.color = '#94A3B8';
                btn.style.borderColor = 'rgba(148,163,184,0.15)';
            };
            btn.onclick = function(e) {
                e.stopPropagation();
                toggleSidebar();
            };

            doc.body.appendChild(btn);
            updateBtnIcon();
        }

        createToggleBtn();
        setTimeout(createToggleBtn, 500);
        setTimeout(updateBtnIcon, 1000);

        // Regarante após rerenders do Streamlit
        var obs = new MutationObserver(function() {
            createToggleBtn();
        });
        obs.observe(doc.body, { childList: true, subtree: false });
    })();
    </script>
    """, height=1, scrolling=False)


def render_sidebar(df: pd.DataFrame) -> dict:
    """Render the sidebar with filters. Returns a dict of active filter values."""
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
            <div class="logo-title">Solis Analytics</div>
            <div class="logo-sub">Inteligência Competitiva · FIDCs</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-title">Filtros</div>', unsafe_allow_html=True)

        incluir_liquidacao = st.toggle("Incluir fundos em liquidação", value=False)
        filtrar_pl = st.toggle("Apenas fundos com PL Validado (Check PL = OK)", value=False)

        # Foco de Atuação
        focos_disponiveis = sorted(df["foco_atuacao"].dropna().unique().tolist())
        focos = st.multiselect(
            "Segmento",
            options=focos_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Administrador
        adm_disponiveis = sorted(df["administrador"].dropna().unique().tolist())
        administradores = st.multiselect(
            "Administrador",
            options=adm_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Gestor
        ges_disponiveis = sorted(df["gestor"].dropna().unique().tolist())
        gestores = st.multiselect(
            "Gestor",
            options=ges_disponiveis,
            default=[],
            placeholder="Todos",
        )

        # Dataset stats
        st.markdown("---")
        st.markdown(f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat">
                <span class="stat-value">{len(df)}</span>
                <span class="stat-label">FIDCs</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['administrador'].nunique()}</span>
                <span class="stat-label">Admins</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['gestor'].nunique()}</span>
                <span class="stat-label">Gestores</span>
            </div>
            <div class="sidebar-stat">
                <span class="stat-value">{df['foco_atuacao'].nunique()}</span>
                <span class="stat-label">Segmentos</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.6rem; color:var(--text-dim); text-align:center; letter-spacing:0.5px;">
            Fonte: Regulamentos CVM / FNET
        </div>
        """, unsafe_allow_html=True)

    filters_dict = {
        "incluir_liquidacao": incluir_liquidacao,
        "filtrar_pl": filtrar_pl,
        "focos": focos,
        "administradores": administradores,
        "gestores": gestores,
    }

    return filters_dict


def apply_sidebar_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply the sidebar filter selections to df."""
    f = df.copy()
    if not filters.get("incluir_liquidacao", False) and "Situacao" in f.columns:
        f = f[~f["Situacao"].astype(str).str.contains("Liquida", case=False, na=False)]
    if filters.get("filtrar_pl", False) and "Check_PL" in f.columns:
        f = f[f["Check_PL"] == "OK"]
    if filters.get("focos"):
        f = f[f["foco_atuacao"].isin(filters["focos"])]
    if filters.get("administradores"):
        f = f[f["administrador"].isin(filters["administradores"])]
    if filters.get("gestores"):
        f = f[f["gestor"].isin(filters["gestores"])]
    return f
