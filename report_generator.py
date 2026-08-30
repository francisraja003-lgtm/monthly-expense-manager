"""
report_generator.py — PDF report generation for Expense & Budget Manager.

Uses ReportLab to produce a professionally aligned, print-ready PDF.

Public API
----------
    generate_pdf_report(expenses, budgets, filepath,
                        report_title="Expense Report", period_label="")
        -> int   (number of expense records included)

All PDF logic is isolated here; GUI code only calls the function above.
"""

from __future__ import annotations

import io
import calendar as _cal
from datetime import datetime
from typing import List, Optional

# ── ReportLab imports ────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── App modules ───────────────────────────────────────────────────────────────
from models import Expense, Budget
from analytics import (
    monthly_summary,
    budget_status,
    pie_chart_data,
    bar_chart_data,
    spending_by_category,
)
from utils import format_currency


# ─────────────────────────────────────────────────────────────────────────────
# Brand colours  (mirror the app palette)
# ─────────────────────────────────────────────────────────────────────────────
_NAVY       = colors.HexColor("#1E293B")
_ACCENT     = colors.HexColor("#3B82F6")
_SUCCESS    = colors.HexColor("#10B981")
_DANGER     = colors.HexColor("#EF4444")
_WARNING    = colors.HexColor("#F59E0B")
_ROW_ALT    = colors.HexColor("#F8FAFC")
_BORDER     = colors.HexColor("#E2E8F0")
_TEXT_PRI   = colors.HexColor("#0F172A")
_TEXT_SEC   = colors.HexColor("#64748B")
_DANGER_BG  = colors.HexColor("#FEF2F2")

# Page geometry
_PAGE_W, _PAGE_H = A4
_M_L  = 14 * mm     # left margin
_M_R  = 14 * mm     # right margin
_M_T  = 14 * mm     # top margin (body; header stripe is above this)
_M_B  = 14 * mm     # bottom margin
_CW   = _PAGE_W - _M_L - _M_R        # usable content width
_STRIPE_H = 13 * mm                   # height of top navy stripe
_FOOT_H   =  8 * mm                   # height reserved for footer


# ─────────────────────────────────────────────────────────────────────────────
# Paragraph styles
# ─────────────────────────────────────────────────────────────────────────────

def _s(name: str, **kw) -> ParagraphStyle:
    # Only set Helvetica as default if caller didn't supply their own fontName
    if "fontName" not in kw:
        kw["fontName"] = "Helvetica"
    return ParagraphStyle(name, **kw)


_STYLES: dict[str, ParagraphStyle] = {
    "app_name":    _s("app_name",    fontSize=10, textColor=_TEXT_SEC,   leading=13),
    "rpt_title":   _s("rpt_title",   fontSize=20, fontName="Helvetica-Bold",
                       textColor=_NAVY, alignment=TA_CENTER, leading=26),
    "gen_time":    _s("gen_time",    fontSize=8,  textColor=_TEXT_SEC,
                       alignment=TA_RIGHT, leading=11),
    "section":     _s("section",     fontSize=13, fontName="Helvetica-Bold",
                       textColor=_NAVY, leading=18, spaceAfter=3),
    "sum_lbl":     _s("sum_lbl",     fontSize=9,  textColor=_TEXT_SEC,   leading=13),
    "sum_val":     _s("sum_val",     fontSize=11, fontName="Helvetica-Bold",
                       textColor=_TEXT_PRI, leading=15),
    "sum_val_ok":  _s("sum_val_ok",  fontSize=11, fontName="Helvetica-Bold",
                       textColor=_SUCCESS,  leading=15),
    "sum_val_bad": _s("sum_val_bad", fontSize=11, fontName="Helvetica-Bold",
                       textColor=_DANGER,   leading=15),
    "th":          _s("th",   fontSize=10, fontName="Helvetica-Bold",
                       textColor=colors.white, leading=13),
    "td":          _s("td",   fontSize=9,  textColor=_TEXT_PRI,  leading=12),
    "td_r":        _s("td_r", fontSize=9,  textColor=_TEXT_PRI,
                       alignment=TA_RIGHT, leading=12),
    "td_c":        _s("td_c", fontSize=9,  textColor=_TEXT_PRI,
                       alignment=TA_CENTER, leading=12),
    "td_danger":   _s("td_danger",   fontSize=9, fontName="Helvetica-Bold",
                       textColor=_DANGER, leading=12),
    "td_danger_r": _s("td_danger_r", fontSize=9, fontName="Helvetica-Bold",
                       textColor=_DANGER, alignment=TA_RIGHT, leading=12),
    "no_data":     _s("no_data", fontSize=10, textColor=_TEXT_SEC,
                       alignment=TA_CENTER, leading=14),
}


# ─────────────────────────────────────────────────────────────────────────────
# Page header + footer  (drawn on canvas every page)
# ─────────────────────────────────────────────────────────────────────────────

class _PageDecor:
    """
    Canvas callback that draws the navy header stripe and footer line
    on every page.  *total_pages* is updated after a dry-run pass so the
    'Page X of N' string is always correct.
    """

    def __init__(self) -> None:
        self.total_pages: int = 1

    def __call__(self, canvas, doc) -> None:
        canvas.saveState()
        w, h = A4

        # ── Top navy stripe ──────────────────────────────────────────
        canvas.setFillColor(_NAVY)
        canvas.rect(0, h - _STRIPE_H, w, _STRIPE_H, fill=1, stroke=0)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(_M_L, h - 9 * mm, "Expense & Budget Manager")

        page_str = f"Page {doc.page} of {self.total_pages}"
        canvas.drawRightString(w - _M_R, h - 9 * mm, page_str)

        # ── Bottom footer line ───────────────────────────────────────
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(_M_L, _M_B + 4 * mm, w - _M_R, _M_B + 4 * mm)

        canvas.setFillColor(_TEXT_SEC)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(_M_L, _M_B + 1.5 * mm,
                          "Generated by Expense & Budget Manager")
        canvas.drawRightString(w - _M_R, _M_B + 1.5 * mm,
                               datetime.now().strftime("%d %b %Y  %H:%M"))

        canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Chart image helper
# ─────────────────────────────────────────────────────────────────────────────

_CHART_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
    "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
]


def _make_chart_image(
    expenses: List[Expense],
    budgets: List[Budget],
    width_mm: float = 160.0,
    height_mm: float = 72.0,
) -> Optional[Image]:
    """
    Render a grouped bar chart (Spent vs Budget) to an in-memory PNG
    and return a ReportLab Image flowable.  Returns None if no data.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cats, spent_vals, limit_vals = bar_chart_data(expenses, budgets)
    # Also handle expenses that have no budget
    spend_map = spending_by_category(expenses)
    budgeted = {b.category for b in budgets}
    for cat in spend_map:
        if cat not in budgeted:
            cats = list(cats) + [cat]
            spent_vals = list(spent_vals) + [spend_map[cat]]
            limit_vals = list(limit_vals) + [0.0]

    if not cats:
        return None

    fig_w = max(width_mm / 25.4, 4.0)
    fig_h = max(height_mm / 25.4, 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#F8FAFC")

    x  = range(len(cats))
    bw = 0.35
    ax.bar([i - bw / 2 for i in x], spent_vals, bw,
           label="Spent",  color="#3B82F6", alpha=0.92)
    ax.bar([i + bw / 2 for i in x], limit_vals, bw,
           label="Budget", color="#10B981", alpha=0.70)

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [c[:13] + "\u2026" if len(c) > 13 else c for c in cats],
        rotation=28, ha="right", fontsize=6,
    )
    ax.tick_params(axis="y", labelsize=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CBD5E1")
    ax.set_ylabel("Amount (\u20b9)", fontsize=7, color="#64748B")
    ax.legend(fontsize=7, frameon=False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#E2E8F0")
    ax.set_axisbelow(True)

    fig.tight_layout(pad=0.8)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)

    img = Image(buf, width=width_mm * mm, height=height_mm * mm)
    img.hAlign = "CENTER"
    return img


# ─────────────────────────────────────────────────────────────────────────────
# Section builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary_table(
    expenses: List[Expense],
    budgets: List[Budget],
    period_label: str,
) -> Table:
    """2-column summary grid with shaded header row."""
    s = _STYLES
    summary = monthly_summary(expenses, budgets)
    ts  = summary["total_spent"]
    tb  = summary["total_budget"]
    rem = summary["remaining"]

    def lbl(t: str) -> Paragraph:
        return Paragraph(t, s["sum_lbl"])

    def val(t: str, good: Optional[bool] = None) -> Paragraph:
        if good is True:
            return Paragraph(t, s["sum_val_ok"])
        if good is False:
            return Paragraph(t, s["sum_val_bad"])
        return Paragraph(t, s["sum_val"])

    data = [
        # Row 0 — header
        [Paragraph("<b>Report Summary</b>",
                   ParagraphStyle("sh2", fontName="Helvetica-Bold",
                                  fontSize=10, textColor=colors.white,
                                  leading=14)),
         ""],
        # Row 1 — labels
        [lbl("Total Expenses"),         lbl("Total Budget")],
        # Row 2 — values
        [val(format_currency(ts)),      val(format_currency(tb))],
        # Row 3 — labels
        [lbl("Remaining Budget"),       lbl("Report Period")],
        # Row 4 — values
        [val(format_currency(rem), good=rem >= 0),
         val(period_label)],
    ]

    half = _CW / 2
    tbl = Table(data, colWidths=[half, half], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _NAVY),
        ("SPAN",          (0, 0), (-1, 0)),
        ("TOPPADDING",    (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("LEFTPADDING",   (0, 0), (-1, 0), 10),
        ("BACKGROUND",    (0, 1), (-1, -1), _ROW_ALT),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BORDER),
        ("INNERGRID",     (0, 1), (-1, -1), 0.5, _BORDER),
        ("TOPPADDING",    (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING",   (0, 1), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 1), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _build_category_table(
    expenses: List[Expense],
    budgets: List[Budget],
) -> Table:
    """Category-wise breakdown: Budget | Spent | Remaining | % Used."""
    s = _STYLES

    header = [
        Paragraph("Category",            s["th"]),
        Paragraph("Budget (\u20b9)",      s["th"]),
        Paragraph("Spent (\u20b9)",       s["th"]),
        Paragraph("Remaining (\u20b9)",   s["th"]),
        Paragraph("% Used",              s["th"]),
    ]

    statuses = budget_status(expenses, budgets)
    spend_map = spending_by_category(expenses)
    budgeted_cats = {b.category for b in budgets}

    # Add categories that have spend but no budget
    extra = [
        {
            "category":   c,
            "limit":      0.0,
            "spent":      spend_map[c],
            "remaining":  -spend_map[c],
            "over_budget": True,
            "pct_used":   100.0,
        }
        for c in spend_map if c not in budgeted_cats
    ]
    all_rows = list(statuses) + extra

    rows = [header]
    per_row_styles: list[tuple] = []

    for i, entry in enumerate(all_rows):
        over = entry["over_budget"]
        bg   = _DANGER_BG if over else (_ROW_ALT if i % 2 else colors.white)
        td   = s["td_danger"]   if over else s["td"]
        tdr  = s["td_danger_r"] if over else s["td_r"]

        rows.append([
            Paragraph(entry["category"],                   td),
            Paragraph(format_currency(entry["limit"]),     tdr),
            Paragraph(format_currency(entry["spent"]),     tdr),
            Paragraph(format_currency(entry["remaining"]), tdr),
            Paragraph(f"{entry['pct_used']:.1f}%",         tdr),
        ])
        ri = len(rows) - 1
        per_row_styles.append(("BACKGROUND", (0, ri), (-1, ri), bg))

    if len(rows) == 1:
        rows.append([Paragraph("No budget data.", s["no_data"]),
                     "", "", "", ""])

    cw = _CW
    col_widths = [cw*0.32, cw*0.17, cw*0.17, cw*0.19, cw*0.15]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

    base = [
        ("BACKGROUND",    (0, 0), (-1, 0), _NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, _BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ]
    tbl.setStyle(TableStyle(base + per_row_styles))
    return tbl


def _build_expenses_table(expenses: List[Expense]) -> Table:
    """Full detailed expense list: ID | Date | Category | Amount | Description."""
    s = _STYLES

    header = [
        Paragraph("ID",               s["th"]),
        Paragraph("Date",             s["th"]),
        Paragraph("Category",         s["th"]),
        Paragraph("Amount (\u20b9)",  s["th"]),
        Paragraph("Description",      s["th"]),
    ]

    rows = [header]
    for exp in expenses:
        rows.append([
            Paragraph(str(exp.id),                  s["td_c"]),
            Paragraph(exp.date,                     s["td_c"]),
            Paragraph(exp.category,                 s["td"]),
            Paragraph(format_currency(exp.amount),  s["td_r"]),
            Paragraph(exp.description or "\u2014",  s["td"]),
        ])

    if len(rows) == 1:
        rows.append([Paragraph("No records.", s["no_data"]),
                     "", "", "", ""])

    cw = _CW
    col_widths = [cw*0.07, cw*0.12, cw*0.20, cw*0.14, cw*0.47]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (0, 0), (2, 0),  "CENTER"),
        ("ALIGN",         (3, 0), (3, 0),  "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _ROW_ALT]),
        ("BOX",           (0, 0), (-1, -1), 0.8, _BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, _BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# Document builder helper
# ─────────────────────────────────────────────────────────────────────────────

def _make_doc(dest, decor: _PageDecor) -> BaseDocTemplate:
    """Create a BaseDocTemplate with correct margins and page callback."""
    body_top    = _M_T + _STRIPE_H          # below the stripe
    body_bottom = _M_B + _FOOT_H            # above the footer
    frame_h = _PAGE_H - body_top - body_bottom

    doc = BaseDocTemplate(
        dest,
        pagesize=A4,
        leftMargin=_M_L,
        rightMargin=_M_R,
        topMargin=body_top,
        bottomMargin=body_bottom,
    )
    frame = Frame(_M_L, body_bottom, _CW, frame_h, id="main")
    doc.addPageTemplates([
        PageTemplate(id="main", frames=[frame], onPage=decor)
    ])
    return doc


def _build_story(
    expenses: List[Expense],
    budgets: List[Budget],
    report_title: str,
    period_label: str,
    now_str: str,
) -> list:
    """Build and return the ReportLab story (list of flowables)."""
    s = _STYLES
    story = []

    # ── Title row ───────────────────────────────────────────────────
    story.append(Spacer(1, 3 * mm))

    title_data = [[
        Paragraph("Expense &amp; Budget Manager", s["app_name"]),
        Paragraph(report_title,                    s["rpt_title"]),
        Paragraph(f"Generated: {now_str}",         s["gen_time"]),
    ]]
    title_tbl = Table(
        title_data,
        colWidths=[_CW * 0.28, _CW * 0.44, _CW * 0.28],
    )
    title_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=_ACCENT, spaceAfter=5 * mm))

    # ── Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("Summary", s["section"]))
    story.append(_build_summary_table(expenses, budgets, period_label))
    story.append(Spacer(1, 6 * mm))

    # ── Chart ───────────────────────────────────────────────────────
    story.append(Paragraph("Spending Overview", s["section"]))
    chart = _make_chart_image(expenses, budgets,
                               width_mm=_CW / mm, height_mm=72)
    if chart:
        story.append(chart)
    else:
        story.append(Paragraph("No chart data available.", s["no_data"]))
    story.append(Spacer(1, 6 * mm))

    # ── Category breakdown ──────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("Category-wise Breakdown", s["section"]),
        _build_category_table(expenses, budgets),
    ]))
    story.append(Spacer(1, 6 * mm))

    # ── Detailed expenses ───────────────────────────────────────────
    story.append(Paragraph("Detailed Expenses", s["section"]))
    story.append(_build_expenses_table(expenses))
    story.append(Spacer(1, 4 * mm))

    return story


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_report(
    expenses: List[Expense],
    budgets: List[Budget],
    filepath: str,
    report_title: str = "Expense Report",
    period_label: str = "",
) -> int:
    """
    Generate a professional PDF report and save it to *filepath*.

    Args:
        expenses:     Expense records to include.
        budgets:      Budget records for context.
        filepath:     Destination file path (must end in .pdf).
        report_title: Centred title shown in the report header.
        period_label: Human-readable period (e.g. "August 2026").

    Returns:
        Number of expense records written.

    Raises:
        ValueError:      If *expenses* is empty.
        PermissionError: If the file cannot be written.
        Exception:       Re-raised on any ReportLab error.
    """
    if not expenses:
        raise ValueError("No expense data to include in the report.")

    now_str = datetime.now().strftime("%d %b %Y  %H:%M")

    if not period_label:
        dates = [e.date for e in expenses]
        period_label = f"{min(dates)}  to  {max(dates)}"

    decor = _PageDecor()

    story = _build_story(expenses, budgets, report_title, period_label, now_str)

    # ── Pass 1: dry-run into a BytesIO sink to count pages ──────────
    buf = io.BytesIO()
    dry_doc = _make_doc(buf, decor)
    dry_doc.build(story)
    decor.total_pages = dry_doc.page   # page counter after build

    # ── Pass 2: real build to file with correct total-page number ───
    story = _build_story(expenses, budgets, report_title, period_label, now_str)
    real_doc = _make_doc(filepath, decor)
    real_doc.build(story)

    return len(expenses)
