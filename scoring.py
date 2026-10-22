# -*- coding: utf-8 -*-
"""
CyberScore Scoring Engine
=========================

Five weighted categories:
  Account Security   25 %
  Phishing Awareness 20 %
  Device Security    20 %
  Privacy            15 %
  Backup Readiness   20 %

Each question maps its answer choices to explicit point values (0-100).
The category score is the *mean* of its questions' points.
The overall score is the weighted average of category scores.

Scoring tiers:
  0 – 29  Critical
 30 – 49  High
 50 – 64  Medium
 65 – 79  Low
 80 – 100 Minimal
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# ── Category metadata ──────────────────────────────────────────────────────

CATEGORIES: dict[str, dict] = {
    "Account Security":   {"weight": 0.25, "icon": "🔑"},
    "Phishing Awareness": {"weight": 0.20, "icon": "🎣"},
    "Device Security":    {"weight": 0.20, "icon": "💻"},
    "Privacy":            {"weight": 0.15, "icon": "🔒"},
    "Backup Readiness":   {"weight": 0.20, "icon": "💾"},
}

# ── Question definitions ───────────────────────────────────────────────────
# Each entry: (question_key, question_text, {answer_value: points})
# Points are always 0-100.

QUESTIONS: list[tuple[str, str, dict]] = [

    # ── Account Security (6 questions) ──────────────────────────────────────
    ("acc_unique_pw",
     "How often do you use a unique password for each account?",
     {"never": 0, "rarely": 15, "sometimes": 40, "mostly": 70, "always": 100}),

    ("acc_pw_manager",
     "Do you use a password manager?",
     {"no_never": 0, "sometimes_manually": 20, "partial": 45, "yes_all": 100}),

    ("acc_pw_strength",
     "How strong are your typical passwords?",
     {"simple_short": 0, "moderate": 30, "long_mixed": 70, "random_16plus": 100}),

    ("acc_mfa",
     "On how many accounts do you have multi-factor authentication (MFA) enabled?",
     {"none": 0, "banking_only": 20, "important": 55, "almost_all": 80, "all": 100}),

    ("acc_mfa_type",
     "What type of second factor do you primarily use?",
     {"none": 0, "sms": 30, "app_totp": 75, "hardware_key": 100}),

    ("acc_breach_check",
     "Have you checked if your accounts appear in known data breaches (e.g. HaveIBeenPwned)?",
     {"never": 0, "years_ago": 30, "once_recently": 65, "regularly": 100}),

    # ── Phishing Awareness (5 questions) ────────────────────────────────────
    ("phi_verify_links",
     "Before clicking a link in email/SMS, do you verify it?",
     {"never": 0, "rarely": 15, "sometimes": 45, "usually": 75, "always": 100}),

    ("phi_share_info",
     "How often do you share sensitive info (OTP, password, SSN) via email or text?",
     {"often": 0, "sometimes": 25, "rarely": 65, "never": 100}),

    ("phi_urgency",
     "Can you recognise urgency/pressure tactics commonly used in phishing?",
     {"no": 0, "sometimes": 40, "mostly": 75, "yes_confident": 100}),

    ("phi_training",
     "Have you completed cybersecurity or phishing awareness training?",
     {"never": 0, "once": 30, "few_times": 60, "regular": 85, "certified": 100}),

    ("phi_suspicious_email",
     "What do you do when you receive a suspicious email?",
     {"click_check": 0, "delete": 40, "report_it": 80, "report_and_warn": 100}),

    # ── Device Security (5 questions) ────────────────────────────────────────
    ("dev_updates",
     "How do you handle OS and app updates?",
     {"ignore": 0, "manual_rarely": 20, "manual_regularly": 60, "automatic": 100}),

    ("dev_lock",
     "How is your primary device locked when not in use?",
     {"no_lock": 0, "screen_saver": 15, "pin_password": 65, "biometric_pin": 100}),

    ("dev_encrypt",
     "Is full-disk encryption enabled on your devices?",
     {"no": 0, "unsure": 20, "some": 55, "yes_all": 100}),

    ("dev_antivirus",
     "How frequently do your devices run antivirus/anti-malware scans?",
     {"never": 0, "rarely": 20, "monthly": 55, "weekly": 80, "realtime": 100}),

    ("dev_public_wifi",
     "When using public Wi-Fi, what precautions do you take?",
     {"none": 0, "avoid_sensitive": 30, "vpn_sometimes": 60, "vpn_always": 100}),

    # ── Privacy (5 questions) ────────────────────────────────────────────────
    ("priv_social",
     "What are your social media privacy settings?",
     {"public_all": 0, "mostly_public": 20, "friends_only": 60, "strict": 85, "no_social": 100}),

    ("priv_app_perms",
     "How do you manage app permissions (location, camera, contacts)?",
     {"allow_all": 0, "allow_most": 20, "selective": 65, "minimal": 90, "deny_audit": 100}),

    ("priv_vpn",
     "Do you use a trusted VPN for privacy?",
     {"never": 0, "sometimes": 40, "frequently": 75, "always": 100}),

    ("priv_browser",
     "Do you use privacy-respecting browser settings or extensions?",
     {"no": 0, "basic": 35, "some_extensions": 65, "hardened": 100}),

    ("priv_data_share",
     "How careful are you about what personal data you share with apps/websites?",
     {"share_freely": 0, "mostly_casual": 20, "somewhat_careful": 55, "very_careful": 85, "strict": 100}),

    # ── Backup Readiness (4 questions) ──────────────────────────────────────
    ("bkp_frequency",
     "How often do you back up your important data?",
     {"never": 0, "rarely": 15, "monthly": 45, "weekly": 75, "daily_auto": 100}),

    ("bkp_location",
     "Where do you store your backups?",
     {"nowhere": 0, "same_device": 10, "external_only": 45,
      "cloud_only": 60, "both_offsite": 100}),

    ("bkp_test",
     "Have you ever tested restoring from your backup?",
     {"never": 0, "not_sure": 15, "once": 50, "regularly": 100}),

    ("bkp_ransomware",
     "Are your backups stored in a way that protects them from ransomware (e.g. offline/immutable)?",
     {"no": 0, "unsure": 20, "partially": 50, "yes": 100}),
]

# ── Map each question key to its category ─────────────────────────────────

_CAT_PREFIXES: dict[str, str] = {
    "acc_": "Account Security",
    "phi_": "Phishing Awareness",
    "dev_": "Device Security",
    "priv_": "Privacy",
    "bkp_": "Backup Readiness",
}


def _question_category(key: str) -> str:
    for prefix, cat in _CAT_PREFIXES.items():
        if key.startswith(prefix):
            return cat
    return "Other"


# ── Core scoring function ──────────────────────────────────────────────────

@dataclass
class ScoreResult:
    overall:    float
    cat_scores: dict[str, float]  # category -> 0-100
    cat_details: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    # cat_details: category -> [(question_text, points_earned)]


def compute_score(answers: dict[str, Any]) -> ScoreResult:
    """
    Compute scores from a dict of {question_key: answer_value}.
    Missing answers default to the worst-case option (0 points).
    """
    cat_question_points: dict[str, list[float]] = {c: [] for c in CATEGORIES}
    cat_details: dict[str, list[tuple[str, float]]] = {c: [] for c in CATEGORIES}

    for q_key, q_text, point_map in QUESTIONS:
        cat = _question_category(q_key)
        raw_answer = answers.get(q_key)
        pts = float(point_map.get(raw_answer, 0))
        cat_question_points[cat].append(pts)
        cat_details[cat].append((q_text, pts))

    # Category score = mean of question points
    cat_scores: dict[str, float] = {}
    for cat, pts_list in cat_question_points.items():
        cat_scores[cat] = round(sum(pts_list) / len(pts_list), 1) if pts_list else 0.0

    # Overall = weighted average
    overall = sum(
        cat_scores[cat] * CATEGORIES[cat]["weight"]
        for cat in CATEGORIES
    )

    return ScoreResult(
        overall=round(overall, 1),
        cat_scores=cat_scores,
        cat_details=cat_details,
    )


# ── Risk classification ────────────────────────────────────────────────────

def risk_level(score: float) -> tuple[str, str, str]:
    """Returns (label, css_class, hex_color)."""
    if score < 30:  return "Critical", "risk-critical", "#ef4444"
    if score < 50:  return "High",     "risk-high",     "#f97316"
    if score < 65:  return "Medium",   "risk-medium",   "#eab308"
    if score < 80:  return "Low",      "risk-low",      "#22c55e"
    return                  "Minimal", "risk-minimal",  "#14b8a6"


def score_color(score: float) -> str:
    return risk_level(score)[2]


# ── Recommendation engine ─────────────────────────────────────────────────

_RECS: list[dict] = [
    # Account Security
    dict(key="acc_unique_pw",   threshold=50,  priority="critical", category="Account Security", icon="🔑",
         title="Stop Reusing Passwords",
         body="Password reuse is the #1 cause of account takeovers. Use a password manager to generate and store unique passwords for every account."),
    dict(key="acc_pw_manager",  threshold=50,  priority="critical", category="Account Security", icon="🗝️",
         title="Adopt a Password Manager",
         body="Tools like Bitwarden (free, open-source) or 1Password generate and store strong unique passwords so you never have to remember them."),
    dict(key="acc_pw_strength", threshold=50,  priority="high",     category="Account Security", icon="💪",
         title="Strengthen Your Passwords",
         body="Use passwords of 16+ random characters. A password manager makes this effortless — you only need to remember one master password."),
    dict(key="acc_mfa",         threshold=55,  priority="critical", category="Account Security", icon="📱",
         title="Enable MFA on All Critical Accounts",
         body="Multi-factor authentication blocks 99.9% of automated attacks. Enable it on email, banking, and social media accounts first."),
    dict(key="acc_mfa_type",    threshold=50,  priority="high",     category="Account Security", icon="🔐",
         title="Upgrade from SMS to an Authenticator App",
         body="SMS codes are vulnerable to SIM-swap attacks. Switch to an authenticator app (Authy, Aegis) or a hardware key (YubiKey)."),
    dict(key="acc_breach_check",threshold=50,  priority="medium",   category="Account Security", icon="🔎",
         title="Check Your Accounts on HaveIBeenPwned",
         body="Visit haveibeenpwned.com to see if your email or passwords have appeared in known data breaches, then change compromised credentials immediately."),

    # Phishing
    dict(key="phi_verify_links", threshold=50, priority="high",    category="Phishing Awareness", icon="🎣",
         title="Verify Links Before Clicking",
         body="Hover over links to preview the real URL. Look for misspelled domains, unexpected redirects, and HTTP (not HTTPS) on sensitive pages."),
    dict(key="phi_share_info",   threshold=65, priority="critical", category="Phishing Awareness", icon="🚫",
         title="Never Share Sensitive Info via Email/Text",
         body="Legitimate services never ask for passwords or OTPs via email or SMS. Treat any such request as a phishing attempt regardless of how official it looks."),
    dict(key="phi_training",     threshold=60, priority="medium",  category="Phishing Awareness", icon="🎓",
         title="Complete Phishing Awareness Training",
         body="Free courses from KnowBe4, Proofpoint, or CISA's CDM programme teach you to recognise phishing at a glance. Revisit annually."),

    # Device Security
    dict(key="dev_updates",    threshold=60,  priority="high",     category="Device Security", icon="🔄",
         title="Enable Automatic Updates",
         body="Unpatched software is the most exploited attack vector. Enable automatic OS, browser, and app updates across all your devices."),
    dict(key="dev_lock",       threshold=65,  priority="high",     category="Device Security", icon="🔏",
         title="Set a Strong Device Lock Screen",
         body="Use a PIN/password of 6+ digits or biometric unlock with auto-lock after 60 seconds. An unlocked device is a gold mine for attackers."),
    dict(key="dev_encrypt",    threshold=55,  priority="high",     category="Device Security", icon="🛡️",
         title="Enable Full-Disk Encryption",
         body="Turn on BitLocker (Windows), FileVault (macOS), or ensure encryption is active on your phone. This protects all data if the device is stolen."),
    dict(key="dev_antivirus",  threshold=55,  priority="medium",   category="Device Security", icon="🦠",
         title="Run Regular Malware Scans",
         body="Install a reputable antivirus with real-time protection (e.g. Windows Defender, Malwarebytes). Schedule weekly full-system scans."),
    dict(key="dev_public_wifi",threshold=60,  priority="high",     category="Device Security", icon="📶",
         title="Use a VPN on Public Wi-Fi",
         body="Public Wi-Fi exposes you to man-in-the-middle attacks. Use a trusted VPN (Mullvad, ProtonVPN) whenever connecting to any network you don't control."),

    # Privacy
    dict(key="priv_social",    threshold=60,  priority="medium",   category="Privacy", icon="👁️",
         title="Tighten Social Media Privacy",
         body="Set profiles to 'Friends Only' or stricter. Oversharing fuels targeted phishing and social engineering attacks against you."),
    dict(key="priv_app_perms", threshold=65,  priority="medium",   category="Privacy", icon="📋",
         title="Audit App Permissions",
         body="Review and revoke permissions apps don't legitimately need. A flashlight app has no business accessing your contacts or location."),
    dict(key="priv_vpn",       threshold=40,  priority="low",      category="Privacy", icon="🕵️",
         title="Use a Privacy VPN",
         body="A VPN hides your traffic from your ISP and reduces tracking. Choose a no-logs provider (Mullvad, ProtonVPN) with an independent audit."),

    # Backup
    dict(key="bkp_frequency",  threshold=45,  priority="high",     category="Backup Readiness", icon="💾",
         title="Implement Automated Backups",
         body="Enable automatic daily or weekly backups. Use the 3-2-1 rule: 3 copies, 2 different media types, 1 offsite (cloud)."),
    dict(key="bkp_location",   threshold=60,  priority="high",     category="Backup Readiness", icon="☁️",
         title="Store Backups Offsite",
         body="Backups on the same device are lost in a ransomware attack or hardware failure. Use both a local external drive AND a cloud backup service."),
    dict(key="bkp_test",       threshold=50,  priority="medium",   category="Backup Readiness", icon="🧪",
         title="Test Your Backup Restoration",
         body="An untested backup is not a backup. Do a full restore to a test device at least once a year to confirm your backups actually work."),
    dict(key="bkp_ransomware", threshold=50,  priority="high",     category="Backup Readiness", icon="🔗",
         title="Protect Backups from Ransomware",
         body="Store at least one backup offline or on immutable cloud storage (versioned S3, Backblaze B2). Ransomware can encrypt network-connected drives too."),
]


def generate_recommendations(answers: dict, cat_scores: dict) -> list[dict]:
    """
    Return a list of recommendation dicts sorted by priority,
    only for questions where the user's score is below the threshold.
    """
    recs = []
    _q_score_map: dict[str, float] = {}
    for q_key, _, point_map in QUESTIONS:
        raw = answers.get(q_key)
        _q_score_map[q_key] = float(point_map.get(raw, 0))

    for rec in _RECS:
        q_score = _q_score_map.get(rec["key"], 0)
        if q_score < rec["threshold"]:
            recs.append(rec)

    _order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recs.sort(key=lambda r: _order.get(r["priority"], 9))

    if not recs:
        recs.append(dict(
            priority="low", icon="🏆", category="General",
            title="Excellent Security Posture!",
            body="Your cybersecurity habits are exemplary. Stay updated on emerging threats via Krebs on Security and run annual security audits.",
        ))
    return recs


# ── Strengths & Weaknesses ────────────────────────────────────────────────

def strengths_weaknesses(cat_scores: dict) -> tuple[list[str], list[str]]:
    """Return (strengths, weaknesses) as lists of category names."""
    strong = sorted([c for c, s in cat_scores.items() if s >= 70],
                    key=lambda c: -cat_scores[c])
    weak   = sorted([c for c, s in cat_scores.items() if s < 50],
                    key=lambda c: cat_scores[c])
    return strong, weak
