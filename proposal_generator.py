# proposal_generator.py
# East Coast Window Films — Proposal Generator
# Generates a branded, customer-facing PDF proposal from ECWF Estimator output data.

import io
import base64
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ─────────────────────────────────────────────
# Brand Colors
# ─────────────────────────────────────────────
BLACK = colors.HexColor("#000000")
WHITE = colors.HexColor("#FFFFFF")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY = colors.HexColor("#CCCCCC")
DARK_GRAY = colors.HexColor("#555555")
ACCENT_GRAY = colors.HexColor("#888888")

# ─────────────────────────────────────────────
# Film Description Map (customer-friendly names)
# ─────────────────────────────────────────────
FILM_DESCRIPTIONS = {
    "UltraView 5":      "Solar Control Film — 5% VLT (Very Dark)",
    "UltraView 15":     "Solar Control Film — 15% VLT (Dark)",
    "UltraView 20":     "Solar Control Film — 20% VLT (Medium-Dark)",
    "UltraView 25":     "Solar Control Film — 25% VLT (Medium)",
    "UltraView 35":     "Solar Control Film — 35% VLT (Light)",
    "Edge Reform":      "Spectrally Selective Film — High Heat Rejection, High Clarity",
    "Edge Coal Alloy":  "Solar Control Film — Neutral Charcoal Tone",
    "Edge Silver":      "Solar Control Film — Reflective Silver",
    "Edge Bronze":      "Solar Control Film — Bronze Tone",
    "Guardian 8mil":    "Safety & Security Film — 8mil, Clear",
    "Guardian 12mil":   "Safety & Security Film — 12mil, Clear",
    "CS 8mil":          "Safety & Security Film — 8mil, Clear",
    "CS 14mil":         "Safety & Security Film — 14mil, Clear",
    "UltraSafe 8mil":   "Safety & Security Film — 8mil, Clear",
    "UltraSafe White Matte": "Safety & Security Film — White Matte, Privacy",
    "Huper ClearShield 8mil":  "Huper Optik Safety Film — 8mil, Clear",
    "Huper ClearShield 14mil": "Huper Optik Safety Film — 14mil, Clear",
    "Huper Shield 35 Neutral 8mil": "Huper Optik Safety Film — 35% VLT, Neutral",
}

def get_film_description(film_name: str) -> str:
    """Return a customer-friendly description for a film, or a generic fallback."""
    for key, desc in FILM_DESCRIPTIONS.items():
        if key.lower() in film_name.lower():
            return desc
    if "decorative" in film_name.lower() or "sxf" in film_name.lower():
        return "Decorative / Privacy Film"
    if "ceramic" in film_name.lower():
        return "Ceramic Solar Control Film — High Performance"
    if "safety" in film_name.lower() or "security" in film_name.lower() or "shield" in film_name.lower():
        return "Safety & Security Film"
    return "Professional Window Film"


def generate_proposal_pdf(
    client: dict,
    section_results: dict,
    active_job_sell: float,
    caulking_lf: float,
    caulking_cost: float,
    equipment_rental: float,
    proposal_number: str,
    valid_days: int,
    scope_notes: str,
    terms_notes: str,
    logo_path: str = None,
) -> bytes:
    """
    Generate a branded PDF proposal and return it as bytes.

    Parameters
    ----------
    client          : dict with keys name, phone, email, address
    section_results : dict of section_name -> result dict from the estimator
    active_job_sell : float, total recommended sell price for active sections
    caulking_lf     : float, linear feet of caulking
    caulking_cost   : float, cost of caulking
    equipment_rental: float, equipment rental cost
    proposal_number : str, e.g. "ECWF-2026-001"
    valid_days      : int, number of days proposal is valid
    scope_notes     : str, additional scope/notes from the user
    terms_notes     : str, terms and conditions text
    logo_path       : str, path to the logo image file
    """

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()

    # ── Custom Styles ──────────────────────────
    style_company = ParagraphStyle(
        "CompanyName",
        parent=styles["Normal"],
        fontSize=22,
        fontName="Helvetica-Bold",
        textColor=BLACK,
        leading=26,
        spaceAfter=2,
    )
    style_tagline = ParagraphStyle(
        "Tagline",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=ACCENT_GRAY,
        leading=12,
        spaceAfter=0,
    )
    style_section_header = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        leading=14,
        spaceAfter=0,
    )
    style_body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=BLACK,
        leading=13,
        spaceAfter=4,
    )
    style_body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=BLACK,
        leading=13,
        spaceAfter=4,
    )
    style_label = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica",
        textColor=ACCENT_GRAY,
        leading=11,
        spaceAfter=1,
    )
    style_small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=7.5,
        fontName="Helvetica",
        textColor=DARK_GRAY,
        leading=10,
        spaceAfter=2,
    )
    style_total_label = ParagraphStyle(
        "TotalLabel",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        leading=16,
        alignment=TA_RIGHT,
    )
    style_total_value = ParagraphStyle(
        "TotalValue",
        parent=styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        leading=18,
        alignment=TA_RIGHT,
    )
    style_footer = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7.5,
        fontName="Helvetica",
        textColor=ACCENT_GRAY,
        leading=10,
        alignment=TA_CENTER,
    )
    style_terms = ParagraphStyle(
        "Terms",
        parent=styles["Normal"],
        fontSize=7.5,
        fontName="Helvetica",
        textColor=DARK_GRAY,
        leading=11,
        spaceAfter=2,
    )
    style_proposal_title = ParagraphStyle(
        "ProposalTitle",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=BLACK,
        leading=14,
        alignment=TA_RIGHT,
    )

    story = []

    # ── HEADER ────────────────────────────────
    today = datetime.today()
    expiry = today + timedelta(days=valid_days)

    header_left = []
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=2.2 * inch, height=0.9 * inch)
            img.hAlign = "LEFT"
            header_left.append(img)
        except Exception:
            header_left.append(Paragraph("EAST COAST WINDOW FILMS", style_company))
    else:
        header_left.append(Paragraph("EAST COAST WINDOW FILMS", style_company))

    header_left.append(Spacer(1, 4))
    header_left.append(Paragraph("Professional Window Film Installation", style_tagline))
    header_left.append(Paragraph("www.ecwfilms.com  |  856.687.5682", style_tagline))

    header_right = [
        Paragraph("PROPOSAL", style_proposal_title),
        Spacer(1, 4),
        Paragraph(f"<b>#{proposal_number}</b>", ParagraphStyle("pnum", parent=style_body, alignment=TA_RIGHT)),
        Paragraph(
            f"Date: {today.strftime('%B %d, %Y')}",
            ParagraphStyle("date", parent=style_label, alignment=TA_RIGHT)
        ),
        Paragraph(
            f"Valid Until: {expiry.strftime('%B %d, %Y')}",
            ParagraphStyle("valid", parent=style_label, alignment=TA_RIGHT)
        ),
    ]

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[4.0 * inch, 3.1 * inch],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLACK, spaceAfter=10))

    # ── CLIENT INFO ───────────────────────────
    client_name = client.get("name", "")
    client_phone = client.get("phone", "")
    client_email = client.get("email", "")
    client_address = client.get("address", "")

    client_left = [
        Paragraph("PREPARED FOR", style_label),
        Paragraph(f"<b>{client_name}</b>" if client_name else "<b>—</b>", style_body_bold),
    ]
    if client_address:
        client_left.append(Paragraph(client_address, style_body))
    if client_phone:
        client_left.append(Paragraph(client_phone, style_body))
    if client_email:
        client_left.append(Paragraph(client_email, style_body))

    client_right = [
        Paragraph("PREPARED BY", style_label),
        Paragraph("<b>East Coast Window Films</b>", style_body_bold),
        Paragraph("www.ecwfilms.com", style_body),
        Paragraph("856.687.5682", style_body),
        Paragraph("info@ecwfilms.com", style_body),
    ]

    client_table = Table(
        [[client_left, client_right]],
        colWidths=[3.6 * inch, 3.5 * inch],
    )
    client_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 12))

    # ── SCOPE NOTES ───────────────────────────
    if scope_notes and scope_notes.strip():
        story.append(Paragraph("PROJECT SCOPE", style_label))
        story.append(Paragraph(scope_notes.strip(), style_body))
        story.append(Spacer(1, 8))

    # ── LINE ITEMS TABLE ──────────────────────
    story.append(Paragraph("PROPOSAL DETAILS", style_label))
    story.append(Spacer(1, 4))

    # Table header row
    table_data = [[
        Paragraph("AREA / ROOM", style_section_header),
        Paragraph("FILM PRODUCT", style_section_header),
        Paragraph("DESCRIPTION", style_section_header),
        Paragraph("SQ FT", ParagraphStyle("th_r", parent=style_section_header, alignment=TA_RIGHT)),
        Paragraph("PRICE", ParagraphStyle("th_r2", parent=style_section_header, alignment=TA_RIGHT)),
    ]]

    row_fill = False
    for section_name, res in section_results.items():
        if res.get("error") or not res.get("is_active"):
            continue

        film_name = res.get("film", "")
        sqft = res.get("sqft", 0)
        sell_price = res.get("recommended_sell", 0.0)
        film_desc = get_film_description(film_name)

        bg = LIGHT_GRAY if row_fill else WHITE
        row_fill = not row_fill

        table_data.append([
            Paragraph(section_name, style_body_bold),
            Paragraph(film_name, style_body),
            Paragraph(film_desc, style_small),
            Paragraph(f"{sqft}", ParagraphStyle("sqft_r", parent=style_body, alignment=TA_RIGHT)),
            Paragraph(f"${sell_price:,.2f}", ParagraphStyle("price_r", parent=style_body_bold, alignment=TA_RIGHT)),
        ])

    # Caulking line item
    if caulking_lf > 0 and caulking_cost > 0:
        table_data.append([
            Paragraph("Perimeter Caulking", style_body_bold),
            Paragraph("Safety Film Perimeter Seal", style_body),
            Paragraph(f"Required for 8mil+ safety films — {caulking_lf:.0f} LF", style_small),
            Paragraph("—", ParagraphStyle("dash", parent=style_body, alignment=TA_RIGHT)),
            Paragraph(f"${caulking_cost:,.2f}", ParagraphStyle("price_r2", parent=style_body_bold, alignment=TA_RIGHT)),
        ])

    # Equipment rental line item
    if equipment_rental > 0:
        table_data.append([
            Paragraph("Equipment Rental", style_body_bold),
            Paragraph("Lift / Scaffold / Specialty Equipment", style_body),
            Paragraph("Required for high or difficult-access windows", style_small),
            Paragraph("—", ParagraphStyle("dash2", parent=style_body, alignment=TA_RIGHT)),
            Paragraph(f"${equipment_rental:,.2f}", ParagraphStyle("price_r3", parent=style_body_bold, alignment=TA_RIGHT)),
        ])

    col_widths = [1.5 * inch, 1.4 * inch, 2.1 * inch, 0.65 * inch, 0.85 * inch]
    line_items_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Build alternating row styles
    table_style_cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BLACK),
    ]

    # Alternating row backgrounds
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
        else:
            table_style_cmds.append(("BACKGROUND", (0, i), (-1, i), WHITE))

    line_items_table.setStyle(TableStyle(table_style_cmds))
    story.append(line_items_table)
    story.append(Spacer(1, 8))

    # ── TOTAL ─────────────────────────────────
    total_display = active_job_sell
    if caulking_cost > 0:
        total_display += caulking_cost
    if equipment_rental > 0:
        total_display += equipment_rental

    total_table = Table(
        [[
            Paragraph("TOTAL INVESTMENT", style_total_label),
            Paragraph(f"${total_display:,.2f}", style_total_value),
        ]],
        colWidths=[5.0 * inch, 2.1 * inch],
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLACK),
        ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 14))

    # ── ACCEPTANCE / SIGNATURE BLOCK ──────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=8))

    sig_table = Table(
        [[
            [
                Paragraph("ACCEPTANCE", style_label),
                Spacer(1, 20),
                HRFlowable(width=2.8 * inch, thickness=0.5, color=BLACK),
                Paragraph("Customer Signature", style_small),
                Spacer(1, 8),
                HRFlowable(width=2.8 * inch, thickness=0.5, color=BLACK),
                Paragraph("Printed Name", style_small),
            ],
            [
                Paragraph("DATE", style_label),
                Spacer(1, 20),
                HRFlowable(width=1.4 * inch, thickness=0.5, color=BLACK),
                Paragraph("Date", style_small),
            ],
        ]],
        colWidths=[3.5 * inch, 3.6 * inch],
    )
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 12))

    # ── TERMS & CONDITIONS ────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=6))
    story.append(Paragraph("TERMS & CONDITIONS", style_label))
    story.append(Spacer(1, 3))

    default_terms = (
        "A 50% deposit is required to schedule your installation. The remaining balance is due upon completion. "
        "All film installations carry the manufacturer's limited warranty against defects in materials and workmanship. "
        "Labor is warranted for one (1) year from the date of installation. "
        "This proposal is valid for the number of days indicated above. Prices are subject to change after expiration. "
        "East Coast Window Films is fully licensed and insured."
    )
    final_terms = terms_notes.strip() if terms_notes and terms_notes.strip() else default_terms
    story.append(Paragraph(final_terms, style_terms))
    story.append(Spacer(1, 10))

    # ── FOOTER ────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=4))
    story.append(Paragraph(
        "East Coast Window Films  |  www.ecwfilms.com  |  856.687.5682  |  info@ecwfilms.com  |  Sorry, we don't do cars.",
        style_footer
    ))

    # ── BUILD ─────────────────────────────────
    doc.build(story)
    return buffer.getvalue()
