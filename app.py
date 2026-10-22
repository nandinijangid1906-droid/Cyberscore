# -*- coding: utf-8 -*-
"""
CyberScore — Personal Cyber Risk Assessment
Main entry point. Run with:
    streamlit run cyberscore/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="CyberScore — Personal Cyber Risk Assessment",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Local imports (must come after set_page_config)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import db
import scoring as sc
import url_analyzer as ua
import pdf_report
from styles import inject_css

# ── One-time init ─────────────────────────────────────────────────────────────
db.init_db()
inject_css()

# ── Session-state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "page": "Dashboard",
        "answers": {},
        "score_result": None,
        "recommendations": [],
        "assessment_saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ══════════════════════════════════════════════════════════════════════════════
#  SHARED UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
)


def score_gauge(overall: float):
    import plotly.graph_objects as go
    label, _, color = sc.risk_level(overall)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=overall,
        number={"font": {"size": 52, "color": color, "family": "JetBrains Mono"}, "suffix": ""},
        gauge={
            "axis": {"range": [0, 100], "tickvals": [0,25,50,75,100],
                     "tickcolor": "#334155", "tickwidth": 1,
                     "tickfont": {"size": 10}},
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  30],  "color": "rgba(239,68,68,0.10)"},
                {"range": [30, 50],  "color": "rgba(249,115,22,0.10)"},
                {"range": [50, 65],  "color": "rgba(234,179,8,0.10)"},
                {"range": [65, 80],  "color": "rgba(34,197,94,0.10)"},
                {"range": [80, 100], "color": "rgba(20,184,166,0.10)"},
            ],
            "threshold": {"line": {"color": color, "width": 3},
                          "thickness": 0.82, "value": overall},
        },
        title={"text": f"<b>{label} Risk</b>",
               "font": {"size": 14, "color": color}},
    ))
    fig.update_layout(**CHART_BASE, height=260)
    return fig


def category_radar(cat_scores: dict):
    import plotly.graph_objects as go
    cats  = list(cat_scores.keys())
    vals  = [cat_scores[c] for c in cats]
    cv    = vals + [vals[0]]
    ct    = cats + [cats[0]]
    fig   = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=cv, theta=ct, fill="toself",
        fillcolor="rgba(124,58,237,0.14)",
        line=dict(color="#7c3aed", width=2),
        name="Your Score",
        hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[80]*(len(cats)+1), theta=ct, fill="toself",
        fillcolor="rgba(14,165,233,0.05)",
        line=dict(color="#0ea5e9", width=1, dash="dot"),
        name="Target (80)",
    ))
    fig.update_layout(
        **CHART_BASE, height=340,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,100],
                            gridcolor="rgba(148,163,184,0.12)",
                            linecolor="rgba(148,163,184,0.12)",
                            tickfont=dict(size=10, color="#64748b")),
            angularaxis=dict(gridcolor="rgba(148,163,184,0.12)",
                             linecolor="rgba(148,163,184,0.12)",
                             tickfont=dict(size=11, color="#cbd5e1")),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                    xanchor="center", x=0.5, font=dict(size=11)),
    )
    return fig


def category_bar(cat_scores: dict):
    import plotly.graph_objects as go
    cats   = list(cat_scores.keys())
    vals   = [cat_scores[c] for c in cats]
    colors = [sc.score_color(v) for v in vals]
    fig = go.Figure(go.Bar(
        x=cats, y=vals,
        marker=dict(color=colors, opacity=0.85),
        text=[f"{v:.0f}" for v in vals],
        textposition="outside",
        textfont=dict(size=11, color="#cbd5e1"),
        hovertemplate="%{x}: %{y:.1f}<extra></extra>",
    ))
    fig.add_hline(y=80, line=dict(color="#0ea5e9", dash="dot", width=1.5),
                  annotation_text="Target (80)", annotation_font_color="#0ea5e9",
                  annotation_position="top right")
    fig.update_layout(
        **CHART_BASE, height=300,
        yaxis=dict(range=[0,115], gridcolor="rgba(148,163,184,0.1)",
                   zerolinecolor="rgba(148,163,184,0.1)"),
        xaxis=dict(tickfont=dict(size=11)),
        showlegend=False,
    )
    return fig


def render_rec_card(rec: dict):
    pri_class = {"critical": "rec-critical", "high": "rec-high",
                 "medium": "rec-medium", "low": "rec-low"}.get(rec.get("priority","low"), "rec-low")
    st.markdown(f"""
    <div class="rec-card {pri_class}">
      <div class="rec-icon">{rec.get('icon','💡')}</div>
      <div>
        <p class="rec-title">{rec.get('title','')}</p>
        <p class="rec-body">{rec.get('body','')}</p>
      </div>
    </div>""", unsafe_allow_html=True)


def render_score_bar(label: str, score: float, icon: str = ""):
    color = sc.score_color(score)
    lvl, badge_cls, _ = sc.risk_level(score)
    st.markdown(f"""
    <div style="margin-bottom:0.9rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;">
        <span style="font-size:0.87rem;color:#cbd5e1;font-weight:500;">{icon} {label}</span>
        <span style="display:flex;gap:0.5rem;align-items:center;">
          <span class="risk-badge {badge_cls}">{lvl}</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;
                       color:{color};font-weight:700;">{score:.0f}</span>
        </span>
      </div>
      <div class="prog-wrap">
        <div class="prog-bar" style="width:{score:.1f}%;background:{color};"></div>
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════

PAGES = [
    ("🏠", "Dashboard"),
    ("📋", "Assessment"),
    ("📊", "Risk Profile"),
    ("✅", "Improvement Plan"),
    ("🔗", "URL Analyzer"),
    ("📈", "History"),
    ("📄", "PDF Report"),
    ("⚙️", "Settings"),
]

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.2rem;">
      <div style="font-size:1.35rem;font-weight:800;
           background:linear-gradient(90deg,#a78bfa,#38bdf8);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;
           background-clip:text;margin-bottom:0.2rem;">🛡️ CyberScore</div>
      <div style="font-size:0.72rem;color:#475569;letter-spacing:0.05em;
           text-transform:uppercase;">Personal Risk Assessment</div>
    </div>
    """, unsafe_allow_html=True)

    for icon, name in PAGES:
        active = st.session_state.page == name
        btn_style = (
            "background:rgba(124,58,237,0.18);border:1px solid rgba(124,58,237,0.35);"
            "color:#c4b5fd;" if active else
            "background:transparent;border:1px solid transparent;color:#64748b;"
        )
        if st.button(
            f"{icon}  {name}",
            key=f"nav_{name}",
            use_container_width=True,
        ):
            st.session_state.page = name
            st.rerun()

    st.markdown("---")
    sr = st.session_state.score_result
    if sr:
        overall = sr.overall
        lvl, _, col = sc.risk_level(overall)
        st.markdown(f"""
        <div style="background:#0f1629;border:1px solid rgba(148,163,184,0.1);
             border-radius:10px;padding:0.8rem;text-align:center;">
          <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;
               letter-spacing:0.07em;margin-bottom:0.3rem;">Current Score</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:2rem;
               font-weight:700;color:{col};line-height:1;">{overall:.0f}</div>
          <div style="font-size:0.75rem;color:{col};font-weight:600;">{lvl} Risk</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box" style="font-size:0.75rem;">
          Complete the Assessment to see your score.
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.5rem;font-size:0.68rem;color:#334155;text-align:center;">
      All data is stored locally.<br>No personal info leaves your device.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">🛡️ &nbsp;Personal Security Assessment</div>
      <p class="hero-title">CyberScore</p>
      <p class="hero-subtitle">
        Your personalised cyber risk score across 5 domains — based on your
        self-reported security practices. Answer the questionnaire to get started.
      </p>
    </div>""", unsafe_allow_html=True)

    sr = st.session_state.score_result
    if sr is None:
        # No assessment yet — show feature overview cards
        c1, c2, c3, c4 = st.columns(4)
        for col, icon, title, desc in [
            (c1, "📋", "Security Assessment",
             "25 questions across 5 weighted categories"),
            (c2, "📊", "Risk Profile",
             "Strengths, weaknesses & personalised advice"),
            (c3, "✅", "Improvement Plan",
             "Track security tasks and monitor progress"),
            (c4, "📈", "Score History",
             "Track improvement over time with Plotly charts"),
        ]:
            col.markdown(f"""
            <div class="card" style="text-align:center;padding:1.5rem 1rem;">
              <div style="font-size:2rem;margin-bottom:0.5rem;">{icon}</div>
              <div class="card-title">{title}</div>
              <div style="font-size:0.8rem;color:#64748b;margin-top:0.3rem;">{desc}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
          👆 Start by navigating to <strong>Assessment</strong> in the sidebar.
          The questionnaire takes about 5 minutes.
        </div>""", unsafe_allow_html=True)

        # Methodology quick-reference
        st.markdown("---")
        st.markdown("#### Scoring Methodology")
        cols = st.columns(5)
        weights = {
            "Account Security": ("🔑", "25%"),
            "Phishing Awareness": ("🎣", "20%"),
            "Device Security": ("💻", "20%"),
            "Backup Readiness": ("💾", "20%"),
            "Privacy": ("🔒", "15%"),
        }
        for col, (cat, (icon, wt)) in zip(cols, weights.items()):
            col.markdown(f"""
            <div class="metric-card">
              <div style="font-size:1.4rem;">{icon}</div>
              <div class="metric-value" style="font-size:1.2rem;color:#a78bfa;">{wt}</div>
              <div class="metric-label">{cat}</div>
            </div>""", unsafe_allow_html=True)
        return

    # ── Dashboard with scores ────────────────────────────────────────────────
    overall    = sr.overall
    cat_scores = sr.cat_scores
    recs       = st.session_state.recommendations
    lvl, badge_cls, color = sc.risk_level(overall)

    col_gauge, col_right = st.columns([1, 1.6], gap="large")

    with col_gauge:
        st.markdown('<div class="score-ring-wrap">', unsafe_allow_html=True)
        st.plotly_chart(score_gauge(overall), use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown(
            f'<div style="text-align:center;margin-top:-0.5rem;">'
            f'<span class="risk-badge {badge_cls}">{lvl} Risk</span></div>',
            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        # Metric row
        n_crit  = sum(1 for v in cat_scores.values() if v < 30)
        n_good  = sum(1 for v in cat_scores.values() if v >= 80)
        n_recs  = len(recs)
        mc1, mc2, mc3 = st.columns(3)
        for col, val, col_hex, lbl, sub in [
            (mc1, f"{overall:.0f}", color,    "Overall Score", "out of 100"),
            (mc2, str(n_crit),      "#ef4444", "Critical Areas","score < 30"),
            (mc3, str(n_recs),      "#f97316", "Action Items",  "recommendations"),
        ]:
            col.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{lbl}</div>
              <div class="metric-value" style="color:{col_hex};">{val}</div>
              <div style="font-size:0.7rem;color:#475569;">{sub}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Category Scores")
        for cat, score in sorted(cat_scores.items(), key=lambda x: x[1]):
            icon = sc.CATEGORIES[cat]["icon"]
            render_score_bar(cat, score, icon)

    st.markdown("---")

    # Top recommendations
    tab1, tab2 = st.tabs(["🕸️  Radar View", "🛠️  Top Recommendations"])
    with tab1:
        st.plotly_chart(category_radar(cat_scores), use_container_width=True,
                        config={"displayModeBar": False})
    with tab2:
        top = [r for r in recs if r.get("priority") in ("critical", "high")][:5]
        if top:
            for rec in top:
                render_rec_card(rec)
        else:
            st.markdown("""
            <div class="success-box">
              🎉 No critical or high-priority items. Your security posture is strong!
            </div>""", unsafe_allow_html=True)
        if st.button("View all recommendations →", key="dash_view_recs"):
            st.session_state.page = "Risk Profile"
            st.rerun()

    st.markdown('<div class="footer">CyberScore v1.0 · Made with IBM Bob · '
                'Self-reported assessment · Not a technical security audit</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════

def _radio(label, key, options_map: dict, horizontal=True):
    """Render a radio with display labels, return the value key."""
    keys   = list(options_map.keys())
    labels = list(options_map.values())
    # Restore previous answer if any
    prev = st.session_state.answers.get(key)
    idx  = keys.index(prev) if prev in keys else 0
    choice = st.radio(label, labels, index=idx,
                      horizontal=horizontal, key=f"q_{key}")
    return keys[labels.index(choice)]


def page_assessment():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">📋 &nbsp;Questionnaire</div>
      <p class="hero-title" style="font-size:1.8rem;">Security Assessment</p>
      <p class="hero-subtitle">
        25 questions across 5 categories. Answer honestly — scores reflect
        <strong>self-reported practices</strong>, not a technical system scan.
        No passwords, OTPs, or recovery codes are collected.
      </p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
      ℹ️ All answers are stored only in your local session and SQLite database on this machine.
      Nothing is transmitted to any external server.
    </div>""", unsafe_allow_html=True)

    answers = {}

    # ── Account Security ─────────────────────────────────────────────────────
    st.markdown('<div class="cat-header"><h3>🔑 &nbsp;Account Security — 25% of score</h3></div>',
                unsafe_allow_html=True)

    answers["acc_unique_pw"] = _radio(
        "How often do you use a unique password for each online account?",
        "acc_unique_pw",
        {"never": "Never", "rarely": "Rarely (1-2 accounts)",
         "sometimes": "Sometimes (some accounts)", "mostly": "Mostly",
         "always": "Always — every account is unique"},
    )
    answers["acc_pw_manager"] = _radio(
        "Do you use a password manager (e.g. Bitwarden, 1Password, KeePass)?",
        "acc_pw_manager",
        {"no_never": "No, never",
         "sometimes_manually": "I write passwords down / use a spreadsheet",
         "partial": "Yes, for some accounts",
         "yes_all": "Yes, for all accounts"},
    )
    answers["acc_pw_strength"] = _radio(
        "How would you describe your typical password complexity?",
        "acc_pw_strength",
        {"simple_short": "Simple, under 8 chars (e.g. 'password123')",
         "moderate": "8-12 chars, some variety",
         "long_mixed": "12+ chars, mixed case, numbers, symbols",
         "random_16plus": "16+ random characters (generated by manager)"},
    )
    answers["acc_mfa"] = _radio(
        "On how many accounts do you have multi-factor authentication (MFA/2FA) enabled?",
        "acc_mfa",
        {"none": "None", "banking_only": "Banking accounts only",
         "important": "Most important accounts (email, banking, social)",
         "almost_all": "Almost all accounts", "all": "All accounts"},
    )
    answers["acc_mfa_type"] = _radio(
        "What type of second factor do you primarily use?",
        "acc_mfa_type",
        {"none": "None / not using MFA",
         "sms": "SMS text message code",
         "app_totp": "Authenticator app (Google Auth, Authy, Aegis)",
         "hardware_key": "Hardware security key (YubiKey, etc.)"},
    )
    answers["acc_breach_check"] = _radio(
        "Have you checked if your credentials appear in known data breaches?",
        "acc_breach_check",
        {"never": "Never heard of breach-checking tools",
         "years_ago": "Checked once, more than a year ago",
         "once_recently": "Checked within the last 6 months",
         "regularly": "I check regularly and act on alerts"},
    )

    st.markdown("---")

    # ── Phishing Awareness ───────────────────────────────────────────────────
    st.markdown('<div class="cat-header"><h3>🎣 &nbsp;Phishing Awareness — 20% of score</h3></div>',
                unsafe_allow_html=True)

    answers["phi_verify_links"] = _radio(
        "Before clicking a link in an email or SMS, do you verify it?",
        "phi_verify_links",
        {"never": "Never — I click without checking",
         "rarely": "Rarely",
         "sometimes": "Sometimes (when it looks suspicious)",
         "usually": "Usually",
         "always": "Always — I hover/preview every link"},
    )
    answers["phi_share_info"] = _radio(
        "How often do you share sensitive info (OTP codes, passwords, SSN) via email or text?",
        "phi_share_info",
        {"often": "Regularly — when asked",
         "sometimes": "Sometimes",
         "rarely": "Rarely",
         "never": "Never — I know legitimate services don't ask this way"},
    )
    answers["phi_urgency"] = _radio(
        "Can you recognise urgency/fear tactics used in phishing? (e.g. 'Your account will be closed!')",
        "phi_urgency",
        {"no": "No, I often act on urgent messages",
         "sometimes": "Sometimes — I'm not always sure",
         "mostly": "Mostly — I pause and think critically",
         "yes_confident": "Yes, confidently — I recognise and ignore them"},
    )
    answers["phi_training"] = _radio(
        "Have you completed any cybersecurity or phishing awareness training?",
        "phi_training",
        {"never": "Never",
         "once": "Once (during onboarding or school)",
         "few_times": "A few times over the years",
         "regular": "Regularly (annual refreshers)",
         "certified": "I hold a cybersecurity certification"},
    )
    answers["phi_suspicious_email"] = _radio(
        "What do you do when you receive a suspicious email?",
        "phi_suspicious_email",
        {"click_check": "Click links to check if they are real",
         "delete": "Delete it and move on",
         "report_it": "Report it to my email provider as phishing",
         "report_and_warn": "Report it and warn others who may have received it"},
    )

    st.markdown("---")

    # ── Device Security ──────────────────────────────────────────────────────
    st.markdown('<div class="cat-header"><h3>💻 &nbsp;Device Security — 20% of score</h3></div>',
                unsafe_allow_html=True)

    answers["dev_updates"] = _radio(
        "How do you handle OS and application updates?",
        "dev_updates",
        {"ignore": "I ignore or postpone them indefinitely",
         "manual_rarely": "Manual, rarely (every few months or longer)",
         "manual_regularly": "Manual, but I apply them within a week",
         "automatic": "Automatic updates are enabled"},
    )
    answers["dev_lock"] = _radio(
        "How is your primary device secured when not in use?",
        "dev_lock",
        {"no_lock": "No lock — anyone can access it",
         "screen_saver": "Screen saver only, no password required to wake",
         "pin_password": "PIN or password required",
         "biometric_pin": "Biometric (face/fingerprint) plus PIN fallback"},
    )
    answers["dev_encrypt"] = _radio(
        "Is full-disk encryption enabled on your devices? (BitLocker, FileVault, etc.)",
        "dev_encrypt",
        {"no": "No",
         "unsure": "I'm not sure",
         "some": "On some devices",
         "yes_all": "Yes, on all my devices"},
    )
    answers["dev_antivirus"] = _radio(
        "How frequently does your device run antivirus/anti-malware scans?",
        "dev_antivirus",
        {"never": "Never / no antivirus installed",
         "rarely": "Rarely (manually, once a year or less)",
         "monthly": "Monthly manual scans",
         "weekly": "Weekly scans",
         "realtime": "Real-time protection is always active"},
    )
    answers["dev_public_wifi"] = _radio(
        "When using public Wi-Fi (café, airport, hotel), what precautions do you take?",
        "dev_public_wifi",
        {"none": "None — I use it freely",
         "avoid_sensitive": "I avoid logging into sensitive accounts",
         "vpn_sometimes": "I use a VPN sometimes",
         "vpn_always": "I always use a trusted VPN"},
    )

    st.markdown("---")

    # ── Privacy ──────────────────────────────────────────────────────────────
    st.markdown('<div class="cat-header"><h3>🔒 &nbsp;Privacy — 15% of score</h3></div>',
                unsafe_allow_html=True)

    answers["priv_social"] = _radio(
        "What are your social media privacy settings?",
        "priv_social",
        {"public_all": "Public — anyone can see everything",
         "mostly_public": "Mostly public",
         "friends_only": "Friends / connections only",
         "strict": "Strict — very limited audience",
         "no_social": "I don't use social media"},
    )
    answers["priv_app_perms"] = _radio(
        "How do you manage app permissions (location, camera, microphone, contacts)?",
        "priv_app_perms",
        {"allow_all": "Allow all permission requests automatically",
         "allow_most": "Allow most requests",
         "selective": "Selective — I think about each request",
         "minimal": "Minimal — only grant what's necessary",
         "deny_audit": "Deny by default and audit periodically"},
    )
    answers["priv_vpn"] = _radio(
        "Do you use a trusted, privacy-focused VPN service?",
        "priv_vpn",
        {"never": "Never",
         "sometimes": "Sometimes (public Wi-Fi only)",
         "frequently": "Frequently",
         "always": "Always when browsing"},
    )
    answers["priv_browser"] = _radio(
        "Do you use privacy-respecting browser settings or extensions?",
        "priv_browser",
        {"no": "No — default browser settings",
         "basic": "Basic (private/incognito mode)",
         "some_extensions": "Ad-blocker and tracker-blocker extensions",
         "hardened": "Hardened browser (uBlock Origin, Firefox, privacy DNS)"},
    )
    answers["priv_data_share"] = _radio(
        "How careful are you about personal data you share with apps and websites?",
        "priv_data_share",
        {"share_freely": "I share freely — it doesn't concern me",
         "mostly_casual": "Mostly casual",
         "somewhat_careful": "Somewhat careful",
         "very_careful": "Very careful — I read privacy policies",
         "strict": "Strict — minimal data, use aliases where possible"},
    )

    st.markdown("---")

    # ── Backup Readiness ─────────────────────────────────────────────────────
    st.markdown('<div class="cat-header"><h3>💾 &nbsp;Backup Readiness — 20% of score</h3></div>',
                unsafe_allow_html=True)

    answers["bkp_frequency"] = _radio(
        "How often do you back up your important data (documents, photos, etc.)?",
        "bkp_frequency",
        {"never": "Never",
         "rarely": "Rarely (once a year or less)",
         "monthly": "Monthly",
         "weekly": "Weekly",
         "daily_auto": "Daily / automated continuous backup"},
    )
    answers["bkp_location"] = _radio(
        "Where are your backups stored?",
        "bkp_location",
        {"nowhere": "I have no backups",
         "same_device": "Same device only (different folder)",
         "external_only": "External hard drive only",
         "cloud_only": "Cloud storage only (Google Drive, iCloud, etc.)",
         "both_offsite": "Both external drive AND cloud (3-2-1 rule)"},
    )
    answers["bkp_test"] = _radio(
        "Have you ever tested restoring from your backup?",
        "bkp_test",
        {"never": "Never — I've never tested it",
         "not_sure": "Not sure if my backup even works",
         "once": "Yes, once",
         "regularly": "Yes, I test restoration regularly"},
    )
    answers["bkp_ransomware"] = _radio(
        "Are your backups protected from ransomware? (e.g. offline or immutable storage)",
        "bkp_ransomware",
        {"no": "No — backups are always online/connected",
         "unsure": "I'm not sure",
         "partially": "Partially (e.g. versioned cloud with limited history)",
         "yes": "Yes — offline drive or immutable cloud storage"},
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_submit, col_reset = st.columns([3, 1])
    with col_submit:
        if st.button("🔍  Calculate My CyberScore", use_container_width=True,
                     key="btn_calculate"):
            result = sc.compute_score(answers)
            recs   = sc.generate_recommendations(answers, result.cat_scores)
            st.session_state.answers        = answers
            st.session_state.score_result   = result
            st.session_state.recommendations = recs
            st.session_state.assessment_saved = False
            # Auto-seed improvement tasks
            db.seed_tasks_from_recs(recs)
            st.success(
                "✅ Score calculated! Navigate to **Dashboard** or **Risk Profile** to view results.",
                icon="🛡️",
            )

    with col_reset:
        if st.button("↺  Reset", use_container_width=True, key="btn_reset"):
            for k in ["answers", "score_result", "recommendations", "assessment_saved"]:
                st.session_state[k] = {} if k == "answers" else (
                    None if k == "score_result" else ([] if k == "recommendations" else False)
                )
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: RISK PROFILE
# ══════════════════════════════════════════════════════════════════════════════

def page_risk_profile():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">📊 &nbsp;Risk Profile</div>
      <p class="hero-title" style="font-size:1.8rem;">Your Risk Profile</p>
      <p class="hero-subtitle">Strengths, weaknesses and personalised recommendations
      based on your assessment answers.</p>
    </div>""", unsafe_allow_html=True)

    sr = st.session_state.score_result
    if sr is None:
        st.markdown("""<div class="warn-box">
          ⚠️ No assessment found. Complete the <strong>Assessment</strong> first.
        </div>""", unsafe_allow_html=True)
        return

    cat_scores  = sr.cat_scores
    recs        = st.session_state.recommendations
    strong, weak = sc.strengths_weaknesses(cat_scores)

    # ── Strengths / Weaknesses summary ───────────────────────────────────────
    col_s, col_w = st.columns(2, gap="large")
    with col_s:
        st.markdown("#### ✅ Strengths")
        if strong:
            for cat in strong:
                score = cat_scores[cat]
                icon  = sc.CATEGORIES[cat]["icon"]
                render_score_bar(cat, score, icon)
        else:
            st.markdown("""<div class="warn-box">
              No categories have reached the 70+ threshold yet. Keep improving!
            </div>""", unsafe_allow_html=True)

    with col_w:
        st.markdown("#### ⚠️ Weaknesses")
        if weak:
            for cat in weak:
                score = cat_scores[cat]
                icon  = sc.CATEGORIES[cat]["icon"]
                render_score_bar(cat, score, icon)
        else:
            st.markdown("""<div class="success-box">
              No categories are below 50. Great foundation!
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Category detail breakdown ─────────────────────────────────────────────
    st.markdown("#### Score Breakdown")
    st.plotly_chart(category_bar(cat_scores), use_container_width=True,
                    config={"displayModeBar": False})

    # Per-category question detail in expanders
    st.markdown("#### Per-Category Question Detail")
    st.markdown("""<div class="info-box">
      Scores shown are the points earned for each answer (0–100 per question).
      The category score is the average of its questions.
    </div>""", unsafe_allow_html=True)

    for cat, details in sr.cat_details.items():
        cat_score = cat_scores[cat]
        icon      = sc.CATEGORIES[cat]["icon"]
        lvl, badge_cls, color = sc.risk_level(cat_score)
        with st.expander(f"{icon} {cat}  —  {cat_score:.0f} / 100  ({lvl})", expanded=False):
            for q_text, pts in details:
                p_color = sc.score_color(pts)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;
                     align-items:flex-start;padding:0.5rem 0;
                     border-bottom:1px solid rgba(148,163,184,0.08);">
                  <span style="font-size:0.83rem;color:#cbd5e1;flex:1;padding-right:1rem;">
                    {q_text}
                  </span>
                  <span style="font-family:'JetBrains Mono',monospace;font-size:0.88rem;
                       font-weight:700;color:{p_color};white-space:nowrap;">
                    {pts:.0f} pts
                  </span>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Recommendations ───────────────────────────────────────────────────────
    st.markdown("#### Personalised Recommendations")
    st.markdown("""<div class="warn-box">
      ⚠️ These recommendations are based on your <em>self-reported</em> answers.
      They are educational suggestions, not the output of a technical system scan.
      A score does not guarantee safety or predict the exact probability of being compromised.
    </div>""", unsafe_allow_html=True)

    _order_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for priority in ["critical", "high", "medium", "low"]:
        group = [r for r in recs if r.get("priority") == priority]
        if not group:
            continue
        dots = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        st.markdown(f"##### {dots[priority]} {priority.capitalize()} Priority")
        for rec in group:
            render_rec_card(rec)

    # Add all to plan button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕  Add all recommendations to Improvement Plan",
                 key="add_all_to_plan"):
        db.seed_tasks_from_recs(recs)
        st.success("Tasks added to your Improvement Plan.", icon="✅")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: IMPROVEMENT PLAN
# ══════════════════════════════════════════════════════════════════════════════

def page_improvement_plan():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">✅ &nbsp;Task Tracker</div>
      <p class="hero-title" style="font-size:1.8rem;">Improvement Plan</p>
      <p class="hero-subtitle">Track security tasks, mark them complete, and monitor progress.</p>
    </div>""", unsafe_allow_html=True)

    tasks = db.load_tasks()

    # ── Progress summary ─────────────────────────────────────────────────────
    total = len(tasks)
    done  = sum(1 for t in tasks if t["done"])
    pct   = int((done / total * 100) if total else 0)

    mc1, mc2, mc3 = st.columns(3)
    for col, val, col_hex, lbl in [
        (mc1, str(total),       "#a78bfa", "Total Tasks"),
        (mc2, str(done),        "#22c55e", "Completed"),
        (mc3, f"{pct}%",        "#0ea5e9", "Progress"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
          <div class="metric-value" style="color:{col_hex};">{val}</div>
          <div class="metric-label">{lbl}</div>
        </div>""", unsafe_allow_html=True)

    if total:
        st.progress(pct / 100)

    st.markdown("---")

    # ── Add custom task ───────────────────────────────────────────────────────
    with st.expander("➕  Add a custom security task", expanded=False):
        with st.form("add_task_form", clear_on_submit=True):
            t_title = st.text_input("Task title *", max_chars=120,
                                    placeholder="e.g. Enable MFA on email account")
            t_desc  = st.text_area("Description (optional)", max_chars=400,
                                   placeholder="Steps or notes…", height=80)
            t_pri   = st.selectbox("Priority", ["critical", "high", "medium", "low"])
            t_cat   = st.selectbox("Category",
                                   ["Account Security", "Phishing Awareness",
                                    "Device Security", "Privacy", "Backup Readiness", "General"])
            submitted = st.form_submit_button("Add Task")
            if submitted:
                title_clean = t_title.strip()
                if not title_clean:
                    st.error("Task title is required.")
                elif len(title_clean) < 3:
                    st.error("Task title must be at least 3 characters.")
                else:
                    db.add_task(title_clean, t_desc.strip(), t_pri, t_cat)
                    st.success(f"Task '{title_clean}' added.", icon="✅")
                    st.rerun()

    # ── Task list ─────────────────────────────────────────────────────────────
    if not tasks:
        st.markdown("""<div class="info-box">
          No tasks yet. Complete an assessment and tasks will be seeded automatically,
          or add your own above.
        </div>""", unsafe_allow_html=True)
        return

    # Filter
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        show_filter = st.selectbox("Show", ["All", "Pending", "Completed"],
                                   key="task_filter")
    with filter_col2:
        pri_filter = st.selectbox("Priority",
                                  ["All", "critical", "high", "medium", "low"],
                                  key="task_pri_filter")

    visible = tasks
    if show_filter == "Pending":
        visible = [t for t in visible if not t["done"]]
    elif show_filter == "Completed":
        visible = [t for t in visible if t["done"]]
    if pri_filter != "All":
        visible = [t for t in visible if t["priority"] == pri_filter]

    pri_colors = {"critical": "#ef4444", "high": "#f97316",
                  "medium":   "#eab308", "low":  "#22c55e"}

    for task in visible:
        tid    = task["id"]
        is_done = bool(task["done"])
        p_col   = pri_colors.get(task["priority"], "#64748b")
        done_cls = "task-done" if is_done else ""

        col_check, col_body, col_del = st.columns([0.5, 8, 1])
        with col_check:
            new_done = st.checkbox("", value=is_done, key=f"task_chk_{tid}",
                                   label_visibility="collapsed")
            if new_done != is_done:
                db.toggle_task(tid, new_done)
                st.rerun()
        with col_body:
            st.markdown(f"""
            <div style="padding:0.4rem 0;">
              <div style="display:flex;gap:0.6rem;align-items:center;">
                <span style="font-size:0.72rem;font-weight:700;color:{p_col};
                     text-transform:uppercase;letter-spacing:0.05em;">
                  {task['priority']}
                </span>
                <span style="font-size:0.75rem;color:#475569;">
                  {task.get('category','')}
                </span>
              </div>
              <div class="{done_cls}" style="font-size:0.88rem;color:#e2e8f0;
                   font-weight:500;margin-top:0.1rem;">
                {task['title']}
              </div>
              {"<div style='font-size:0.78rem;color:#64748b;margin-top:0.15rem;'>" + task['description'][:120] + "</div>" if task.get('description') else ""}
            </div>""", unsafe_allow_html=True)
        with col_del:
            if st.button("🗑️", key=f"del_{tid}", help="Delete task"):
                db.delete_task(tid)
                st.rerun()

    st.markdown("---")
    if st.button("🗑️  Clear all completed tasks", key="clear_done"):
        for t in tasks:
            if t["done"]:
                db.delete_task(t["id"])
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: URL ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

def page_url_analyzer():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">🔗 &nbsp;Static Analysis Only</div>
      <p class="hero-title" style="font-size:1.8rem;">URL Safety Analyzer</p>
      <p class="hero-subtitle">
        Analyze URLs for suspicious patterns without visiting them.
        Uses lexical and structural checks — no network requests are made.
      </p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="warn-box">
      ⚠️ <strong>Limitations:</strong> This tool performs <em>static pattern analysis only</em>.
      It does not visit the URL, scan the destination server, or query threat-intelligence databases.
      A "clean" result does not guarantee a URL is safe — always verify unfamiliar links independently.
      Never enter credentials on any site you did not intentionally navigate to.
    </div>""", unsafe_allow_html=True)

    url_input = st.text_input(
        "Enter a URL to analyze",
        placeholder="https://example.com/path?param=value",
        max_chars=2000,
        key="url_input",
    )

    col_analyze, col_clear = st.columns([3, 1])
    with col_analyze:
        analyze_clicked = st.button("🔍  Analyze URL", key="btn_analyze_url",
                                    use_container_width=True)
    with col_clear:
        if st.button("✕  Clear", key="btn_clear_url", use_container_width=True):
            if "url_result" in st.session_state:
                del st.session_state["url_result"]
            st.rerun()

    if analyze_clicked:
        raw = url_input.strip()
        if not raw:
            st.error("Please enter a URL to analyze.")
        else:
            result = ua.analyze_url(raw)
            st.session_state["url_result"] = result

    result = st.session_state.get("url_result")
    if result is None:
        return

    st.markdown("---")

    # ── Verdict banner ────────────────────────────────────────────────────────
    verdict_icon = {
        "clean": "✅", "caution": "⚠️",
        "suspicious": "🔶", "dangerous": "🚨", "unknown": "❓"
    }.get(result.verdict, "❓")

    verdict_box_class = {
        "clean": "success-box", "caution": "warn-box",
        "suspicious": "warn-box", "dangerous": "danger-box", "unknown": "info-box"
    }.get(result.verdict, "info-box")

    st.markdown(f"""
    <div class="{verdict_box_class}" style="font-size:1rem;font-weight:600;">
      {verdict_icon} &nbsp;Verdict: <span style="text-transform:capitalize;">
      {result.verdict}</span>
      &nbsp;·&nbsp; {result.danger_count} danger flag(s)
      &nbsp;·&nbsp; {result.warning_count} warning(s)
    </div>""", unsafe_allow_html=True)

    # ── Parsed URL breakdown ──────────────────────────────────────────────────
    if result.valid:
        st.markdown("#### Parsed URL Structure")
        sc1, sc2, sc3 = st.columns(3)
        sc1.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Scheme</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;
               font-weight:700;color:{'#22c55e' if result.scheme=='https' else '#f97316'};">
            {result.scheme or '—'}
          </div>
        </div>""", unsafe_allow_html=True)
        sc2.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Domain</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;
               font-weight:700;color:#e2e8f0;word-break:break-all;">
            {result.domain or '—'}
          </div>
        </div>""", unsafe_allow_html=True)
        sc3.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Path</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;
               color:#94a3b8;word-break:break-all;">
            {(result.path[:40] + '…') if len(result.path) > 40 else (result.path or '/')}
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Findings ──────────────────────────────────────────────────────────────
    st.markdown("#### Analysis Findings")
    sev_icon  = {"danger": "🚨", "warning": "⚠️", "info": "ℹ️"}
    sev_class = {"danger": "danger-box", "warning": "warn-box", "info": "info-box"}

    for finding in result.findings:
        box_cls  = sev_class.get(finding.severity, "info-box")
        icon_chr = sev_icon.get(finding.severity, "ℹ️")
        st.markdown(f"""
        <div class="{box_cls}" style="margin-bottom:0.5rem;">
          <strong>{icon_chr} {finding.title}</strong><br>
          <span style="font-size:0.80rem;">{finding.detail}</span>
        </div>""", unsafe_allow_html=True)

    # ── Education block ───────────────────────────────────────────────────────
    with st.expander("📚  What do these checks mean?", expanded=False):
        st.markdown("""
**Checks performed (all purely lexical — no network activity):**

| Check | Why it matters |
|---|---|
| HTTPS vs HTTP | HTTP exposes your data to interception on the same network |
| IP address as domain | Legitimate sites use domain names; IPs suggest evasion |
| Subdomain depth | `paypal.com.evil.com` is owned by `evil.com`, not PayPal |
| Suspicious TLDs | Free/anonymous TLDs are disproportionately used for phishing |
| URL shortener | Hides the real destination — expand before visiting |
| Phishing keywords | Brand names in domains mimic trusted services |
| Long URL / encoding | Obfuscation techniques to confuse preview tools |
| @ in URL | Everything before @ is treated as credentials by browsers |

**What this tool cannot check:**
- Whether the server at the URL actually serves malicious content
- Certificate validity or HSTS status (requires a network request)
- Threat-intelligence database membership (e.g. Google Safe Browsing)
- JavaScript redirects or content injected after page load
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def page_history():
    import plotly.graph_objects as go

    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">📈 &nbsp;Score Trends</div>
      <p class="hero-title" style="font-size:1.8rem;">Assessment History</p>
      <p class="hero-subtitle">Track your security improvement over time.</p>
    </div>""", unsafe_allow_html=True)

    # Save current assessment if not yet saved
    sr = st.session_state.score_result
    if sr and not st.session_state.assessment_saved:
        if st.button("💾  Save current assessment to history", key="btn_save_hist"):
            db.save_assessment(
                sr.overall, sr.cat_scores,
                st.session_state.answers,
            )
            st.session_state.assessment_saved = True
            st.success("Assessment saved.", icon="✅")
            st.rerun()

    history = db.load_assessments()

    if not history:
        st.markdown("""<div class="info-box">
          No saved assessments yet. Complete an assessment and save it to start tracking progress.
        </div>""", unsafe_allow_html=True)
        return

    # ── Trend line chart ──────────────────────────────────────────────────────
    df_data = {
        "Date":  [h["taken_at"][:10] for h in reversed(history)],
        "Score": [h["overall"]       for h in reversed(history)],
        "ID":    [h["id"]            for h in reversed(history)],
    }

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_data["Date"], y=df_data["Score"],
        mode="lines+markers",
        line=dict(color="#7c3aed", width=2.5),
        marker=dict(size=8, color="#a78bfa",
                    line=dict(color="#0a0e1a", width=2)),
        name="Overall Score",
        hovertemplate="Date: %{x}<br>Score: %{y:.1f}<extra></extra>",
    ))
    fig.add_hline(y=80, line=dict(color="#0ea5e9", dash="dot", width=1.5),
                  annotation_text="Target (80)",
                  annotation_font_color="#0ea5e9")
    fig.update_layout(
        **CHART_BASE, height=300,
        yaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,0.1)",
                   zerolinecolor="rgba(148,163,184,0.1)"),
        xaxis=dict(tickfont=dict(size=11)),
        title=dict(text="Overall Score Over Time", font=dict(color="#cbd5e1", size=13)),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Category trend ────────────────────────────────────────────────────────
    if len(history) >= 2:
        st.markdown("#### Category Score Trends")
        cat_fig = go.Figure()
        cat_colors_map = {
            "Account Security":   "#a78bfa",
            "Phishing Awareness": "#38bdf8",
            "Device Security":    "#2dd4bf",
            "Privacy":            "#f59e0b",
            "Backup Readiness":   "#fb923c",
        }
        dates = [h["taken_at"][:10] for h in reversed(history)]
        for cat in sc.CATEGORIES:
            vals = [h["cat_scores"].get(cat, 0) for h in reversed(history)]
            cat_fig.add_trace(go.Scatter(
                x=dates, y=vals, mode="lines+markers",
                name=cat,
                line=dict(color=cat_colors_map.get(cat, "#94a3b8"), width=2),
                marker=dict(size=6),
                hovertemplate=f"{cat}: %{{y:.1f}}<extra></extra>",
            ))
        cat_fig.update_layout(
            **CHART_BASE, height=320,
            yaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,0.1)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3,
                        xanchor="center", x=0.5, font=dict(size=10)),
        )
        st.plotly_chart(cat_fig, use_container_width=True,
                        config={"displayModeBar": False})

    # ── History table ─────────────────────────────────────────────────────────
    st.markdown("#### Saved Assessments")
    import pandas as pd
    rows = []
    for h in history:
        lvl, _, _ = sc.risk_level(h["overall"])
        rows.append({
            "Date / Time": h["taken_at"].replace("T", "  "),
            "Overall Score": f"{h['overall']:.1f}",
            "Risk Level": lvl,
            **{cat: f"{h['cat_scores'].get(cat, 0):.0f}"
               for cat in sc.CATEGORIES},
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: PDF REPORT
# ══════════════════════════════════════════════════════════════════════════════

def page_pdf_report():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">📄 &nbsp;Export</div>
      <p class="hero-title" style="font-size:1.8rem;">PDF Report</p>
      <p class="hero-subtitle">Download a full assessment report with scores,
      category breakdown, and prioritised recommendations.</p>
    </div>""", unsafe_allow_html=True)

    sr = st.session_state.score_result
    if sr is None:
        st.markdown("""<div class="warn-box">
          ⚠️ No assessment found. Complete the <strong>Assessment</strong> first.
        </div>""", unsafe_allow_html=True)
        return

    st.markdown("""
    <div class="info-box">
      The PDF contains your self-reported scores, category breakdown, risk level,
      and all personalised recommendations. It is generated entirely on this machine
      — no data is sent anywhere.
    </div>""", unsafe_allow_html=True)

    # Preview
    overall    = sr.overall
    cat_scores = sr.cat_scores
    recs       = st.session_state.recommendations
    lvl, badge_cls, color = sc.risk_level(overall)

    st.markdown("#### Report Preview")
    pc1, pc2 = st.columns([1, 2], gap="large")
    with pc1:
        st.markdown(f"""
        <div class="score-ring-wrap" style="padding:1.2rem;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:3.5rem;
               font-weight:700;color:{color};text-align:center;">{overall:.0f}</div>
          <div style="text-align:center;margin-top:0.3rem;">
            <span class="risk-badge {badge_cls}">{lvl} Risk</span>
          </div>
        </div>""", unsafe_allow_html=True)
    with pc2:
        for cat, score in cat_scores.items():
            icon = sc.CATEGORIES[cat]["icon"]
            render_score_bar(cat, score, icon)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**{len(recs)} recommendation(s)** will be included in the PDF.")

    if st.button("⬇️  Generate & Download PDF", key="btn_gen_pdf",
                 use_container_width=False):
        with st.spinner("Generating PDF…"):
            try:
                pdf_bytes = pdf_report.build_pdf(
                    overall=sr.overall,
                    cat_scores=sr.cat_scores,
                    recommendations=recs,
                )
                st.download_button(
                    label="📄  Download CyberScore_Report.pdf",
                    data=pdf_bytes,
                    file_name="CyberScore_Report.pdf",
                    mime="application/pdf",
                    key="btn_download_pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

    st.markdown("""
    <div class="info-box" style="margin-top:1rem;">
      ℹ️ The report includes a disclaimer that scores are based on self-reported answers,
      are not a technical audit, and do not guarantee security or predict breach probability.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

def page_settings():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">⚙️ &nbsp;Settings</div>
      <p class="hero-title" style="font-size:1.8rem;">Settings</p>
      <p class="hero-subtitle">Scoring methodology, data management, and privacy information.</p>
    </div>""", unsafe_allow_html=True)

    # ── Scoring Methodology ───────────────────────────────────────────────────
    st.markdown("### 📐 Scoring Methodology")
    st.markdown("""
    <div class="card">
    <p style="color:#94a3b8;font-size:0.88rem;line-height:1.75;margin:0;">
    CyberScore uses a <strong>weighted-average</strong> model across five categories.
    Each question maps every answer choice to an explicit point value between 0 and 100,
    reflecting the relative security improvement that answer represents.
    </p>
    </div>""", unsafe_allow_html=True)

    # Weights table
    import pandas as pd
    weights_df = pd.DataFrame([
        {"Category": f"{sc.CATEGORIES[c]['icon']} {c}",
         "Weight": f"{sc.CATEGORIES[c]['weight']*100:.0f}%",
         "Questions": sum(1 for q, _, _ in sc.QUESTIONS if q.startswith(pfx)),
         "Rationale": rationale}
        for (c, pfx, rationale) in [
            ("Account Security",   "acc_",  "Password reuse and missing MFA are the #1 and #2 causes of account compromise (Verizon DBIR 2024)"),
            ("Phishing Awareness", "phi_",  "Phishing is involved in >90% of breaches; human recognition is the primary defence"),
            ("Device Security",    "dev_",  "Unpatched devices and missing encryption are top exploit vectors per CISA KEV data"),
            ("Backup Readiness",   "bkp_",  "Ransomware recovery depends entirely on backup quality; 3-2-1 rule is the gold standard"),
            ("Privacy",            "priv_", "Privacy hygiene reduces social-engineering surface and data-broker exposure"),
        ]
    ])
    st.dataframe(weights_df, hide_index=True, use_container_width=True)

    st.markdown("""
    **Formula:**

    ```
    Category Score  = mean(question_points)          # each question: 0–100
    Overall Score   = Σ (category_score × weight)    # weighted average
    ```

    **Risk tiers:**

    | Score | Level | Description |
    |---|---|---|
    | 0 – 29 | 🔴 Critical | Significant exposure; immediate action required |
    | 30 – 49 | 🟠 High | Several important gaps; address promptly |
    | 50 – 64 | 🟡 Medium | Moderate practices; room for improvement |
    | 65 – 79 | 🟢 Low | Good foundation; a few areas to tighten |
    | 80 – 100 | 🟦 Minimal | Strong security posture; maintain and review |

    **References:** NIST SP 800-63B, CISA Known Exploited Vulnerabilities, Verizon DBIR 2024, CIS Controls v8.
    """)

    # ── Important disclaimers ─────────────────────────────────────────────────
    st.markdown("### ⚠️ Important Disclaimers")
    st.markdown("""
    <div class="warn-box">
      <strong>Self-reported only:</strong> All scores are based on your own answers.
      CyberScore does not scan your devices, access your accounts, read your files,
      or perform any technical verification. Results reflect your stated habits, not
      technically measured facts.
    </div>
    <div class="warn-box" style="margin-top:0.6rem;">
      <strong>No guarantee of safety:</strong> A high score indicates good security habits,
      but does not guarantee you will not experience a security incident. Cyber threats
      are constantly evolving and no self-assessment can predict exact risk probability.
    </div>
    <div class="info-box" style="margin-top:0.6rem;">
      <strong>Privacy:</strong> CyberScore never collects passwords, OTPs, recovery codes,
      or any other authentication credentials. No data is transmitted outside this machine.
      The SQLite database is stored locally at <code>cyberscore/cyberscore.db</code>.
    </div>""", unsafe_allow_html=True)

    # ── Data management ───────────────────────────────────────────────────────
    st.markdown("### 🗑️ Data Management")

    history = db.load_assessments()
    tasks   = db.load_tasks()
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;gap:2rem;">
        <div>
          <div class="metric-label">Saved Assessments</div>
          <div class="metric-value" style="color:#a78bfa;">{len(history)}</div>
        </div>
        <div>
          <div class="metric-label">Improvement Tasks</div>
          <div class="metric-value" style="color:#38bdf8;">{len(tasks)}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    col_da, col_dt = st.columns(2)

    with col_da:
        st.markdown("**Delete all assessment history**")
        confirm_da = st.checkbox(
            "I confirm I want to permanently delete all saved assessments.",
            key="confirm_del_assessments",
        )
        if st.button("🗑️  Delete Assessment History", key="btn_del_assessments",
                     disabled=not confirm_da):
            n = db.delete_all_assessments()
            st.success(f"Deleted {n} assessment(s).", icon="✅")
            st.rerun()

    with col_dt:
        st.markdown("**Delete all improvement tasks**")
        confirm_dt = st.checkbox(
            "I confirm I want to permanently delete all tasks.",
            key="confirm_del_tasks",
        )
        if st.button("🗑️  Delete All Tasks", key="btn_del_tasks",
                     disabled=not confirm_dt):
            n = db.delete_all_tasks()
            st.success(f"Deleted {n} task(s).", icon="✅")
            st.rerun()

    st.markdown("""
    <div class="footer">
      CyberScore v1.0 · Made with IBM Bob · Python · Streamlit · SQLite · Plotly · ReportLab
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════

PAGE_MAP = {
    "Dashboard":      page_dashboard,
    "Assessment":     page_assessment,
    "Risk Profile":   page_risk_profile,
    "Improvement Plan": page_improvement_plan,
    "URL Analyzer":   page_url_analyzer,
    "History":        page_history,
    "PDF Report":     page_pdf_report,
    "Settings":       page_settings,
}

current_page = st.session_state.get("page", "Dashboard")
render_fn = PAGE_MAP.get(current_page, page_dashboard)
render_fn()
