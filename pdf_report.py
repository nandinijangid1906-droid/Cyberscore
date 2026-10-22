# -*- coding: utf-8 -*-
"""
PDF Report Generator using ReportLab.
Produces a self-contained PDF with overall score, category breakdown,
risk classification, and prioritised recommendations.
"""

from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, HRFlowable,
    KeepTogether,
)
from reportlab.platypus import SimpleDocTemplate

# ── Colour palette (matches dark UI, printed as lighter equivalents) ────────

C_PURPLE   = colors.HexColor("#7c3aed")
C_TEAL     = colors.HexColor("#0ea5e9")
C_DARK     = colors.HexColor("#0f172a")
C_MID      = colors.HexColor("#1e293b")
C_LIGHT    = colors.HexColor("#f8fafc")
C_TEXT     = colors.HexColor("#1e293b")
C_MUTED    = colors.HexColor("#64748b")
C_BORDER   = colors.HexColor("#e2e8f0")

C_CRITICAL = colors.HexColor("#ef4444")
C_HIGH     = colors.HexColor("#f97316")
C_MEDIUM   = colors.HexColor("#eab308")
C_LOW      = colors.HexColor("#22c55e")
C_MINIMAL  = colors.HexColor("#14b8a6")


def _risk_color(score: float) -> colors.Color:
    if score < 30: return C_CRITICAL
    if score < 50: return C_HIGH
    if score < 65: return C_MEDIUM
    if score < 80: return C_LOW
    return C_MINIMAL


def _risk_label(score: float) -> str:
    if score < 30: return "Critical"
    if score < 50: return "High"
    if score < 65: return "Medium"
    if score < 80: return "Low"
    return "Minimal"


def _priority_color(priority: str) -> colors.Color:
    return {
        "critical": C_CRITICAL,
        "high":     C_HIGH,
        "medium":   C_MEDIUM,
        "low":      C_LOW,
    }.get(priority, C_MUTED)


# ── Style helpers ───────────────────────────────────────────────────────────

def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("cs_title",
            fontSize=26, leading=32, textColor=C_DARK,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("cs_subtitle",
            fontSize=11, leading=16, textColor=C_MUTED,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=12),
        "h2": ParagraphStyle("cs_h2",
            fontSize=13, leading=18, textColor=C_PURPLE,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("cs_h3",
            fontSize=11, leading=15, textColor=C_DARK,
            fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("cs_body",
            fontSize=9.5, leading=14, textColor=C_TEXT,
            fontName="Helvetica", spaceAfter=4),
        "small": ParagraphStyle("cs_small",
            fontSize=8, leading=12, textColor=C_MUTED,
            fontName="Helvetica", spaceAfter=3),
        "score_big": ParagraphStyle("cs_score",
            fontSize=48, leading=54, textColor=C_PURPLE,
            fontName="Helvetica-Bold", alignment=TA_CENTER),
        "score_label": ParagraphStyle("cs_score_label",
            fontSize=10, leading=14, textColor=C_MUTED,
            fontName="Helvetica", alignment=TA_CENTER),
        "disclaimer": ParagraphStyle("cs_disclaimer",
            fontSize=7.5, leading=11, textColor=C_MUTED,
            fontName="Helvetica-Oblique"),
    }


# ── Score bar helper ────────────────────────────────────────────────────────

def _score_bar_table(score: float, width: float = 12 * cm) -> Table:
    """Return a Table that renders as a coloured progress bar."""
    filled  = max(0.0, min(1.0, score / 100.0))
    bar_col = _risk_color(score)
    t = Table(
        [["", ""]],
        colWidths=[width * filled, width * (1 - filled)],
        rowHeights=[7],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), bar_col),
        ("BACKGROUND", (1, 0), (1, 0), C_BORDER),
        ("LINEABOVE",    (0, 0), (-1, 0), 0, colors.white),
        ("LINEBELOW",    (0, 0), (-1, 0), 0, colors.white),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    return t


# ── Main builder ────────────────────────────────────────────────────────────

def build_pdf(
    overall: float,
    cat_scores: dict[str, float],
    recommendations: list[dict],
    taken_at: str | None = None,
) -> bytes:
    """
    Build and return PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="CyberScore — Personal Cyber Risk Assessment Report",
        author="CyberScore",
    )

    S = _styles()
    W = doc.width  # usable width
    story = []

    # ── Cover block ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("CyberScore", S["title"]))
    story.append(Paragraph("Personal Cyber Risk Assessment Report", S["subtitle"]))
    ts = taken_at or datetime.now().strftime("%d %B %Y, %H:%M")
    story.append(Paragraph(f"Generated: {ts}", S["small"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=12))

    # ── Overall score panel ──────────────────────────────────────────────────
    risk_lbl   = _risk_label(overall)
    risk_col   = _risk_color(overall)

    score_data = [
        [Paragraph(f"{overall:.0f}", S["score_big"])],
        [Paragraph("Overall Digital Safety Score (0 – 100)", S["score_label"])],
        [Paragraph(f"Risk Level: {risk_lbl}", ParagraphStyle(
            "rl", fontSize=13, leading=18, fontName="Helvetica-Bold",
            textColor=risk_col, alignment=TA_CENTER))],
    ]
    score_tbl = Table(score_data, colWidths=[W])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), C_LIGHT),
        ("BOX",        (0, 0), (0, -1), 1, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        "<i>This score reflects your self-reported cybersecurity practices. "
        "It is an educational indicator, not a technical audit or guarantee of safety.</i>",
        S["disclaimer"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # ── Category breakdown ───────────────────────────────────────────────────
    story.append(Paragraph("Category Breakdown", S["h2"]))

    CATEGORY_WEIGHTS = {
        "Account Security":   0.25,
        "Phishing Awareness": 0.20,
        "Device Security":    0.20,
        "Privacy":            0.15,
        "Backup Readiness":   0.20,
    }

    cat_rows = [["Category", "Score", "Weight", "Risk Level"]]
    for cat, score in cat_scores.items():
        weight = CATEGORY_WEIGHTS.get(cat, 0)
        cat_rows.append([
            Paragraph(cat, S["body"]),
            Paragraph(f"{score:.0f} / 100", S["body"]),
            Paragraph(f"{weight*100:.0f}%", S["body"]),
            Paragraph(_risk_label(score), ParagraphStyle(
                "rl2", fontSize=9.5, fontName="Helvetica-Bold",
                textColor=_risk_color(score))),
        ])

    cat_tbl = Table(cat_rows, colWidths=[W * 0.40, W * 0.18, W * 0.14, W * 0.28])
    cat_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  C_PURPLE),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("BACKGROUND",   (0, 1), (-1, -1), C_LIGHT),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cat_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # ── Per-category score bars ──────────────────────────────────────────────
    story.append(Paragraph("Score Visualisation", S["h2"]))
    bar_w = W * 0.55
    for cat, score in cat_scores.items():
        row = Table(
            [[Paragraph(cat, S["body"]),
              _score_bar_table(score, bar_w),
              Paragraph(f"{score:.0f}", ParagraphStyle(
                  "sv", fontSize=9.5, fontName="Helvetica-Bold",
                  textColor=_risk_color(score), alignment=TA_RIGHT))]],
            colWidths=[W * 0.30, bar_w, W * 0.10],
            rowHeights=[16],
        )
        row.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(row)

    story.append(Spacer(1, 0.5 * cm))

    # ── Recommendations ──────────────────────────────────────────────────────
    story.append(Paragraph("Prioritised Recommendations", S["h2"]))
    story.append(Paragraph(
        "The following actions are ordered by priority. Address Critical items first.",
        S["small"],
    ))
    story.append(Spacer(1, 0.2 * cm))

    _priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_recs = sorted(recommendations,
                         key=lambda r: _priority_order.get(r.get("priority", "low"), 9))

    def _xml(text: str) -> str:
        """Escape text for use inside ReportLab XML paragraphs."""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

    for i, rec in enumerate(sorted_recs, 1):
        pri    = rec.get("priority", "low")
        p_col  = _priority_color(pri)
        # hexval() returns "0xRRGGBB" — strip the "0x" prefix to get "RRGGBB"
        hex_str = p_col.hexval()[2:]
        p_lbl  = pri.upper()
        title  = _xml(rec.get("title", ""))
        body   = _xml(rec.get("body", ""))

        block = KeepTogether([
            Table(
                [[Paragraph(f"{i}.", ParagraphStyle("rn", fontSize=9, fontName="Helvetica-Bold",
                    textColor=C_MUTED)),
                  Paragraph(
                    f'<font color="#{hex_str}" size="8"><b>[{p_lbl}]</b></font>  '
                    f'<b>{title}</b>',
                    S["body"]),
                ]],
                colWidths=[0.6*cm, W - 0.6*cm],
            ),
            Table(
                [[Spacer(0.6*cm, 1),
                  Paragraph(body, S["small"])]],
                colWidths=[0.6*cm, W - 0.6*cm],
            ),
            Spacer(1, 0.2*cm),
        ])
        story.append(block)

    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 0.2 * cm))

    # ── Footer disclaimer ────────────────────────────────────────────────────
    story.append(Paragraph(
        "DISCLAIMER: CyberScore is an educational self-assessment tool based on self-reported answers. "
        "It does not perform technical scans, does not access your systems or accounts, and cannot "
        "guarantee your security or predict the likelihood of any specific cyber incident. "
        "Recommendations are aligned with NIST SP 800-63B, CISA guidelines, and CIS Controls v8. "
        "Consult a qualified cybersecurity professional for a formal security audit.",
        S["disclaimer"],
    ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        f"CyberScore v1.0  ·  Made with IBM Bob  ·  {datetime.now().strftime('%Y')}",
        ParagraphStyle("footer", fontSize=7, textColor=C_MUTED,
                       fontName="Helvetica", alignment=TA_CENTER),
    ))

    doc.build(story)
    return buf.getvalue()
