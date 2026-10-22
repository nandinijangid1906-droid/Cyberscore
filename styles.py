# -*- coding: utf-8 -*-
"""Central CSS injected once at app startup."""

import streamlit as st


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Reset / Base ───────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
}
.main .block-container {
    padding: 1.2rem 2.2rem 3rem;
    max-width: 1280px;
}

/* ── Sidebar ────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #070b14 !important;
    border-right: 1px solid rgba(148,163,184,0.08);
}
[data-testid="stSidebar"] .stRadio > label {
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
}

/* ── Hero header ────────────────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, #0f1629 0%, #150d30 50%, #0f1629 100%);
    border: 1px solid rgba(139,92,246,0.22);
    border-radius: 18px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.6rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content:''; position:absolute; top:-40%; left:-15%;
    width:55%; height:180%;
    background:radial-gradient(ellipse,rgba(139,92,246,0.09) 0%,transparent 70%);
}
.hero-header::after {
    content:''; position:absolute; top:-40%; right:-15%;
    width:55%; height:180%;
    background:radial-gradient(ellipse,rgba(20,184,166,0.07) 0%,transparent 70%);
}
.hero-badge {
    display:inline-block;
    background:rgba(139,92,246,0.14);
    border:1px solid rgba(139,92,246,0.38);
    color:#a78bfa; border-radius:30px;
    padding:0.22rem 0.8rem;
    font-size:0.72rem; font-weight:600;
    letter-spacing:0.07em; text-transform:uppercase;
    margin-bottom:0.7rem;
}
.hero-title {
    font-size:2.3rem; font-weight:800; margin:0 0 0.35rem;
    background:linear-gradient(90deg,#a78bfa,#38bdf8,#2dd4bf);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; line-height:1.15;
}
.hero-subtitle { font-size:0.96rem; color:#94a3b8; margin:0; }

/* ── Cards ──────────────────────────────────────────────────── */
.card {
    background:#0f1629;
    border:1px solid rgba(148,163,184,0.1);
    border-radius:14px;
    padding:1.4rem 1.6rem;
    margin-bottom:1rem;
    transition: border-color .2s;
}
.card:hover { border-color:rgba(139,92,246,0.28); }
.card-title {
    font-size:0.95rem; font-weight:700; color:#e2e8f0;
    margin:0 0 0.18rem;
}
.card-desc { font-size:0.8rem; color:#64748b; margin:0 0 1rem; }

/* ── Category chip ──────────────────────────────────────────── */
.cat-header {
    background:linear-gradient(90deg,rgba(124,58,237,0.13),transparent);
    border-left:3px solid #7c3aed;
    border-radius:0 10px 10px 0;
    padding:0.6rem 1.1rem;
    margin:1.3rem 0 0.9rem;
}
.cat-header h3 {
    font-size:0.88rem; font-weight:700; color:#c4b5fd;
    margin:0; letter-spacing:0.04em; text-transform:uppercase;
}

/* ── Score ring wrapper ─────────────────────────────────────── */
.score-ring-wrap {
    background:linear-gradient(135deg,#0f1629,#150d30);
    border:1px solid rgba(139,92,246,0.28);
    border-radius:18px;
    padding:1.6rem;
    text-align:center;
}

/* ── Risk badges ────────────────────────────────────────────── */
.risk-badge { display:inline-block; border-radius:8px; padding:.28rem .85rem;
    font-size:.8rem; font-weight:700; letter-spacing:.04em; }
.risk-critical { background:rgba(239,68,68,.14);  color:#f87171; border:1px solid rgba(239,68,68,.28); }
.risk-high      { background:rgba(249,115,22,.14); color:#fb923c; border:1px solid rgba(249,115,22,.28); }
.risk-medium    { background:rgba(234,179,8,.14);  color:#facc15; border:1px solid rgba(234,179,8,.28); }
.risk-low       { background:rgba(34,197,94,.14);  color:#4ade80; border:1px solid rgba(34,197,94,.28); }
.risk-minimal   { background:rgba(20,184,166,.14); color:#2dd4bf; border:1px solid rgba(20,184,166,.28); }

/* ── Metric cards ───────────────────────────────────────────── */
.metric-card {
    background:#0f1629;
    border:1px solid rgba(148,163,184,0.1);
    border-radius:12px;
    padding:1rem 1.2rem;
    text-align:center;
}
.metric-value {
    font-family:'JetBrains Mono',monospace;
    font-size:1.85rem; font-weight:700; margin:.15rem 0 .08rem;
}
.metric-label {
    font-size:.72rem; color:#64748b; font-weight:500;
    text-transform:uppercase; letter-spacing:.07em;
}

/* ── Recommendation / rec cards ────────────────────────────── */
.rec-card {
    background:#0f1629; border-radius:11px;
    padding:.9rem 1.1rem; margin-bottom:.6rem;
    border-left:3px solid; display:flex; gap:.75rem;
}
.rec-critical { border-color:#ef4444; }
.rec-high     { border-color:#f97316; }
.rec-medium   { border-color:#eab308; }
.rec-low      { border-color:#22c55e; }
.rec-title    { font-size:.86rem; font-weight:600; color:#e2e8f0; margin:0 0 .18rem; }
.rec-body     { font-size:.79rem; color:#94a3b8; margin:0; line-height:1.5; }
.rec-icon     { font-size:1.25rem; flex-shrink:0; margin-top:.04rem; }

/* ── Progress bars (custom) ─────────────────────────────────── */
.prog-wrap {
    background:rgba(148,163,184,0.1);
    border-radius:4px; height:7px; margin-top:.3rem;
}
.prog-bar { height:100%; border-radius:4px; }

/* ── Info / warning boxes ───────────────────────────────────── */
.info-box {
    background:rgba(14,165,233,0.08);
    border:1px solid rgba(14,165,233,0.2);
    border-radius:10px; padding:.75rem 1rem;
    font-size:.81rem; color:#7dd3fc; margin:.5rem 0;
}
.warn-box {
    background:rgba(234,179,8,0.08);
    border:1px solid rgba(234,179,8,0.22);
    border-radius:10px; padding:.75rem 1rem;
    font-size:.81rem; color:#fde68a; margin:.5rem 0;
}
.danger-box {
    background:rgba(239,68,68,0.08);
    border:1px solid rgba(239,68,68,0.22);
    border-radius:10px; padding:.75rem 1rem;
    font-size:.81rem; color:#fca5a5; margin:.5rem 0;
}
.success-box {
    background:rgba(34,197,94,0.08);
    border:1px solid rgba(34,197,94,0.22);
    border-radius:10px; padding:.75rem 1rem;
    font-size:.81rem; color:#86efac; margin:.5rem 0;
}

/* ── Streamlit widget tweaks ────────────────────────────────── */
div[data-testid="stRadio"]    > label,
div[data-testid="stSelectbox"]> label,
div[data-testid="stCheckbox"] > label,
div[data-testid="stSlider"]   > label,
div[data-testid="stTextInput"]> label { color:#cbd5e1 !important; font-size:.86rem !important; font-weight:500 !important; }
div[data-testid="stRadio"] > div { flex-wrap:wrap; gap:.35rem; }
.stButton > button {
    background:linear-gradient(135deg,#7c3aed,#0ea5e9) !important;
    color:#fff !important; border:none !important;
    border-radius:10px !important; font-weight:600 !important;
    font-size:.89rem !important; padding:.55rem 1.8rem !important;
    transition:opacity .2s !important;
}
.stButton > button:hover { opacity:.85 !important; }
.stProgress > div > div > div > div {
    background:linear-gradient(90deg,#7c3aed,#0ea5e9);
    border-radius:4px;
}
.stTabs [data-baseweb="tab-list"] {
    gap:.25rem; background:transparent;
    border-bottom:1px solid rgba(148,163,184,0.13);
}
.stTabs [data-baseweb="tab"] {
    background:transparent; border-radius:8px 8px 0 0;
    color:#64748b; font-weight:500; font-size:.86rem;
    padding:.45rem 1.1rem;
}
.stTabs [aria-selected="true"] {
    background:rgba(139,92,246,0.11) !important;
    color:#a78bfa !important;
    border-bottom:2px solid #7c3aed !important;
}
hr { border-color:rgba(148,163,184,0.09) !important; margin:1.3rem 0; }
details summary { color:#94a3b8 !important; font-size:.83rem !important; }

/* ── Task item ──────────────────────────────────────────────── */
.task-item {
    background:#0f1629; border:1px solid rgba(148,163,184,0.1);
    border-radius:10px; padding:.75rem 1rem;
    margin-bottom:.5rem; display:flex;
    justify-content:space-between; align-items:center;
}
.task-done { opacity:.5; text-decoration:line-through; }

/* ── URL analyzer result ────────────────────────────────────── */
.url-safe    { color:#4ade80; }
.url-warn    { color:#facc15; }
.url-danger  { color:#f87171; }

/* ── Footer ─────────────────────────────────────────────────── */
.footer {
    text-align:center; margin-top:2.5rem;
    padding-top:1.2rem;
    border-top:1px solid rgba(148,163,184,0.09);
    color:#475569; font-size:.75rem;
}
</style>
"""
