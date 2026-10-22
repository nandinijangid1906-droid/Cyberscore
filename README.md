# 🛡️ CyberScore — Personal Cyber Risk Assessment

A complete, modular **Streamlit** web application that assesses your personal cybersecurity posture across five weighted domains, generates interactive visualisations, tracks your improvement over time, analyses URLs for suspicious patterns, and exports PDF reports — all running locally with no external API dependencies.

---

## Quick Start

```bash
# 1. Install dependencies
pip install streamlit plotly pandas reportlab

# 2. Launch the app
python -m streamlit run cyberscore/app.py

# 3. Run the automated test suite
python cyberscore/tests.py
```

The app opens at **http://localhost:8501** by default.

---

## Project Structure

```
cyberscore/
├── app.py            # Main Streamlit entry point — all 8 page views
├── scoring.py        # Scoring engine: questions, weights, recommendations
├── db.py             # SQLite persistence (assessments + tasks)
├── url_analyzer.py   # Static URL pattern analysis (no network requests)
├── pdf_report.py     # ReportLab PDF report generator
├── styles.py         # Centralised CSS injected at startup
├── tests.py          # 53-test automated suite (unittest)
├── requirements.txt  # Pinned dependencies
└── cyberscore.db     # SQLite database (auto-created on first run)
```

---

## Features

### 📋 Security Assessment
- **25 questions** across 5 weighted categories
- Every answer choice maps to an **explicit point value (0–100)**
- Answers persist in session state and are restored if you revisit the form
- No passwords, OTPs, or recovery codes are collected at any point

### 🏠 Dashboard
- Overall Digital Safety Score gauge (0–100)
- Category score cards with colour-coded risk levels
- Radar chart vs. 80-point target baseline
- Top critical/high recommendations surfaced immediately

### 📊 Risk Profile
- Strengths (≥ 70) and weaknesses (< 50) highlighted
- Per-category question-level score breakdown in expandable panels
- Full prioritised recommendation list (Critical → High → Medium → Low)
- "Add all to Improvement Plan" button

### ✅ Improvement Plan
- Task tracker backed by SQLite
- Auto-seeded from assessment recommendations (no duplicates)
- Add custom tasks with title, description, priority, and category
- Toggle done/undone, filter by status or priority, delete tasks
- Live progress bar and completion metrics

### 🔗 URL Safety Analyzer
Performs **12 static lexical checks** — no network requests made:

| Check | What it catches |
|---|---|
| HTTPS vs HTTP | Unencrypted connections |
| IP address as domain | Evasion of domain-name visibility |
| Subdomain depth | `paypal.com.evil.com` style tricks |
| Brand in subdomain | Trusted names hidden above the real domain |
| Suspicious TLD | Freenom and abuse-prone registries |
| URL shortener | Hidden destination links |
| Phishing keywords | Brand names embedded in domain strings |
| Long URL | Obfuscation via length |
| Heavy encoding | Percent-encoding evasion |
| `@` in URL | Credential-prefix phishing technique |
| Double slash in path | Parser-confusion evasion |
| Non-HTTP scheme | `javascript:`, `data:`, `ftp:` etc. |

### 📈 Assessment History
- Save completed assessments to SQLite with one click
- Overall score trend line chart (Plotly)
- Per-category trend lines across multiple assessments
- Full history table with risk level per assessment

### 📄 PDF Reports
- Generated entirely on-device via ReportLab (no cloud service)
- Includes: cover page, overall score, category bar chart, score bars, all recommendations
- Disclaimer printed on every report (self-reported, not a technical audit)
- Download via Streamlit's native download button

### ⚙️ Settings
- Full scoring methodology documentation with formula and weight rationale
- Risk tier table with descriptions
- Aligned with NIST SP 800-63B, CISA KEV, Verizon DBIR 2024, CIS Controls v8
- Confirmed data deletion for assessments and tasks (checkbox gate required)

---

## Scoring Methodology

```
Category Score  = mean(question_points_in_category)     # 0–100 per question
Overall Score   = Σ (category_score × category_weight)  # weighted average
```

| Category | Weight | Rationale |
|---|---|---|
| Account Security | **25%** | Password reuse + missing MFA = #1 and #2 breach causes (DBIR 2024) |
| Phishing Awareness | **20%** | Phishing involved in >90% of breaches; human recognition is primary defence |
| Device Security | **20%** | Unpatched software = top CISA KEV exploit vector |
| Backup Readiness | **20%** | Ransomware recovery depends entirely on backup quality |
| Privacy | **15%** | Reduces social-engineering surface and data-broker exposure |

**Risk tiers:**

| Score | Level |
|---|---|
| 0 – 29 | 🔴 Critical |
| 30 – 49 | 🟠 High |
| 50 – 64 | 🟡 Medium |
| 65 – 79 | 🟢 Low |
| 80 – 100 | 🟦 Minimal |

---

## Security & Privacy Design

- **No credentials collected.** The app never asks for or stores passwords, OTPs, PINs, or recovery codes.
- **All data is local.** SQLite database is written to `cyberscore/cyberscore.db` on your own machine. No data is transmitted anywhere.
- **Parameterised SQL queries.** All database writes use `?` placeholders — SQL injection is not possible.
- **Self-reported only.** Scores reflect stated habits, not technically verified system state. This is clearly labelled throughout the UI and in every PDF report.
- **URL analyzer is passive.** No network requests are made. The socket is verified in tests.

---

## Running Tests

```bash
python cyberscore/tests.py
```

53 tests across 5 suites:

| Suite | Tests | Covers |
|---|---|---|
| `TestScoringEngine` | 20 | Score bounds, formula, weights, risk levels, recommendations, strengths/weaknesses |
| `TestDatabase` | 11 | CRUD for assessments and tasks, ordering, deduplication, SQL injection safety |
| `TestUrlAnalyzer` | 14 | Every check flag, verdict logic, no-network guarantee |
| `TestPdfReport` | 7 | PDF bytes, valid header, non-empty, all priority levels, edge scores |
| `TestIntegration` | 1 | Full end-to-end: score → save → reload → tasks → PDF → URL → cleanup |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| streamlit | ≥ 1.35 | Web UI framework |
| plotly | ≥ 5.22 | Interactive charts (gauge, radar, bar, line) |
| pandas | ≥ 2.2 | History table display |
| reportlab | ≥ 4.0 | PDF report generation |

All dependencies work offline. No paid APIs or external services required.

---

## Known Limitations

1. **Self-reported only.** CyberScore cannot verify your actual system configuration. A user can achieve a high score by answering dishonestly.
2. **URL analyzer is static.** It cannot detect malware served by an otherwise clean-looking domain, certificate spoofing, or JavaScript-based redirects. It does not query threat-intelligence databases.
3. **No user accounts.** All data is local to the machine and Streamlit session. There is no cloud sync or multi-device support.
4. **Score is not a guarantee.** A high score indicates good self-reported habits but does not predict or prevent security incidents. Cyber threats evolve continuously.
5. **Single-user.** The app is designed for individual personal use. It has no authentication layer.

---

## Licence

MIT — for educational and personal use. Not intended for use as a commercial security audit tool.

---

*Made with IBM Bob · Python · Streamlit · SQLite · Plotly · ReportLab*
