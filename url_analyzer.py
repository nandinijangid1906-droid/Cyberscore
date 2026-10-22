# -*- coding: utf-8 -*-
"""
URL Safety Analyzer
===================
Performs static pattern analysis on a submitted URL string.
Does NOT make network requests, visit the URL, or interact with the target.
All checks are purely lexical / structural.

Limitations are clearly disclosed to the user in the UI.
"""

from __future__ import annotations
import re
import urllib.parse
from dataclasses import dataclass, field


# ── Known suspicious TLDs and keywords ────────────────────────────────────

_SUSPICIOUS_TLDS = {
    ".tk", ".ml", ".ga", ".cf", ".gq",   # Freenom abuse-prone TLDs
    ".xyz", ".top", ".click", ".loan",
    ".work", ".date", ".racing", ".stream",
    ".download", ".party", ".review",
}

_PHISHING_KEYWORDS = [
    "login", "signin", "verify", "update", "account",
    "secure", "banking", "paypal", "amazon", "google",
    "apple", "microsoft", "netflix", "confirm", "password",
    "credential", "suspended", "limited", "unlock", "billing",
    "invoice", "support", "helpdesk", "webscr", "checkout",
]

_URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "buff.ly", "rebrand.ly", "is.gd", "cutt.ly", "clck.ru",
    "shorturl.at", "tiny.cc", "bl.ink",
}

_SAFE_SCHEMES = {"https", "http"}


@dataclass
class UrlFinding:
    severity: str        # "danger" | "warning" | "info"
    code: str            # machine-readable tag
    title: str
    detail: str


@dataclass
class UrlAnalysisResult:
    raw_url: str
    valid: bool
    scheme: str = ""
    domain: str = ""
    path: str = ""
    findings: list[UrlFinding] = field(default_factory=list)
    verdict: str = "unknown"   # "safe" | "suspicious" | "dangerous" | "unknown"
    verdict_color: str = "#64748b"
    score: int = 0             # 0=most dangerous, 100=cleanest

    @property
    def danger_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "danger")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")


def analyze_url(raw: str) -> UrlAnalysisResult:
    """
    Analyze a URL string using static pattern checks only.
    No network requests are made.
    """
    raw = raw.strip()
    result = UrlAnalysisResult(raw_url=raw, valid=False)

    if not raw:
        result.findings.append(UrlFinding("danger", "empty", "Empty input", "No URL was provided."))
        result.verdict = "unknown"
        return result

    # Normalise: add scheme if missing so urllib can parse it
    normalised = raw if "://" in raw else "https://" + raw

    try:
        parsed = urllib.parse.urlparse(normalised)
        result.valid  = True
        result.scheme = parsed.scheme.lower()
        result.domain = parsed.netloc.lower()
        result.path   = parsed.path
    except Exception:
        result.findings.append(UrlFinding("danger", "parse_fail",
            "Could not parse URL", "The input does not appear to be a valid URL structure."))
        result.verdict, result.verdict_color = "dangerous", "#ef4444"
        return result

    # Strip port from domain for matching
    domain_no_port = result.domain.split(":")[0]

    # ── Check 1: scheme ────────────────────────────────────────────────────
    if result.scheme not in _SAFE_SCHEMES:
        result.findings.append(UrlFinding("danger", "bad_scheme",
            f"Unusual scheme: {result.scheme!r}",
            "Only http and https are normal web schemes. Others (ftp, javascript, data) "
            "can indicate malicious content."))

    # ── Check 2: HTTPS vs HTTP ─────────────────────────────────────────────
    if result.scheme == "http":
        result.findings.append(UrlFinding("warning", "no_https",
            "No HTTPS encryption",
            "The URL uses plain HTTP. Any data exchanged is unencrypted and visible "
            "to anyone on the same network. Avoid entering credentials on HTTP sites."))

    # ── Check 3: IP address instead of domain ─────────────────────────────
    ip_pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    if ip_pattern.match(domain_no_port):
        result.findings.append(UrlFinding("danger", "ip_address",
            "IP address used instead of domain name",
            "Legitimate websites use domain names, not raw IP addresses. "
            "IP-based URLs are a common phishing and malware delivery technique."))

    # ── Check 4: excessive subdomains ─────────────────────────────────────
    parts = domain_no_port.split(".")
    if len(parts) > 4:
        result.findings.append(UrlFinding("warning", "many_subdomains",
            f"Unusual number of subdomains ({len(parts) - 2})",
            "Phishing sites often use deep subdomains like "
            "'paypal.com.verify.evil.com' to create the illusion of a trusted brand."))

    # ── Check 5: brand name in subdomain (homograph-style) ────────────────
    trusted_brands = ["paypal", "google", "amazon", "apple", "microsoft",
                      "facebook", "instagram", "netflix", "bankofamerica", "chase"]
    if len(parts) >= 3:
        subdomain = ".".join(parts[:-2]).lower()
        for brand in trusted_brands:
            if brand in subdomain:
                result.findings.append(UrlFinding("danger", "brand_in_subdomain",
                    f"Trusted brand '{brand}' appears in subdomain, not root domain",
                    f"The actual registered domain is '{'.'.join(parts[-2:])}'. "
                    f"Having '{brand}' only in the subdomain is a classic phishing trick."))
                break

    # ── Check 6: suspicious TLD ───────────────────────────────────────────
    tld = "." + parts[-1] if parts else ""
    if tld in _SUSPICIOUS_TLDS:
        result.findings.append(UrlFinding("warning", "suspicious_tld",
            f"Suspicious top-level domain: {tld}",
            "This TLD is frequently abused for phishing and spam due to free/anonymous registration."))

    # ── Check 7: URL shortener ────────────────────────────────────────────
    if domain_no_port in _URL_SHORTENERS:
        result.findings.append(UrlFinding("warning", "url_shortener",
            "URL shortener detected",
            "Short URLs hide the true destination. They are commonly used in phishing emails "
            "and spam campaigns to obscure malicious links. Expand it before visiting."))

    # ── Check 8: phishing keywords in domain ──────────────────────────────
    domain_str = domain_no_port.replace("-", "").replace(".", "")
    matched_kw = [kw for kw in _PHISHING_KEYWORDS if kw in domain_str]
    if matched_kw:
        kw_list = ", ".join(matched_kw[:3])
        result.findings.append(UrlFinding("warning", "phishing_keywords",
            f"Phishing-related keywords in domain: {kw_list}",
            "Attackers embed trusted brand names or action words in domains to seem legitimate. "
            "Verify the exact registered domain independently."))

    # ── Check 9: very long URL ────────────────────────────────────────────
    if len(raw) > 200:
        result.findings.append(UrlFinding("warning", "long_url",
            f"Unusually long URL ({len(raw)} characters)",
            "Very long URLs may be used to hide the real destination or overflow URL preview displays."))

    # ── Check 10: encoded characters / obfuscation ────────────────────────
    encoded_pct = raw.count("%")
    if encoded_pct > 5:
        result.findings.append(UrlFinding("warning", "heavy_encoding",
            f"Heavy URL encoding ({encoded_pct} encoded sequences)",
            "Excessive percent-encoding is used to obfuscate malicious URLs "
            "and bypass naive content filters."))

    # ── Check 11: multiple @ symbols (URL credential abuse) ───────────────
    if raw.count("@") > 0:
        result.findings.append(UrlFinding("danger", "at_in_url",
            "@ symbol in URL",
            "A URL like 'https://paypal.com@evil.com' actually navigates to evil.com. "
            "The part before @ is treated as credentials, not the domain."))

    # ── Check 12: double slashes in path (evasion) ────────────────────────
    if "//" in result.path:
        result.findings.append(UrlFinding("warning", "double_slash_path",
            "Double slash in URL path",
            "Double slashes in the path can be used to confuse URL parsers and security filters."))

    # ── Derive verdict ────────────────────────────────────────────────────
    d = result.danger_count
    w = result.warning_count

    if d >= 2:
        result.verdict, result.verdict_color, result.score = "dangerous",  "#ef4444", max(0, 10 - d*5)
    elif d == 1:
        result.verdict, result.verdict_color, result.score = "suspicious", "#f97316", 25
    elif w >= 3:
        result.verdict, result.verdict_color, result.score = "suspicious", "#f97316", 35
    elif w >= 1:
        result.verdict, result.verdict_color, result.score = "caution",    "#eab308", 55 + (3-w)*10
    else:
        result.verdict, result.verdict_color, result.score = "clean",      "#22c55e", 95

    if not result.findings:
        result.findings.append(UrlFinding("info", "no_issues",
            "No suspicious patterns detected",
            "Static analysis found no red flags. This does not guarantee the URL is safe — "
            "always verify destinations you do not recognise before entering credentials."))

    return result
