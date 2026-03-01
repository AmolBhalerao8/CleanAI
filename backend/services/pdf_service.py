"""
PDF quote generator for Cleannest.

Produces a branded, professional PDF quote using ReportLab.
Returns PDF content as bytes so it can be attached to an email.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

import pytz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from models.lead import Lead
from models.service_info import ServiceInfo, SERVICE_TYPE_LABELS, FREQUENCY_LABELS
from models.quote import Quote, TimeSlot


# ── Brand colours ─────────────────────────────────────────────────────────────
BRAND_TEAL = colors.HexColor("#1A8F7A")
BRAND_DARK = colors.HexColor("#1C2B36")
BRAND_LIGHT = colors.HexColor("#F0FAF8")
BRAND_GREY = colors.HexColor("#6B7280")
WHITE = colors.white

# ── Company info (from env) ────────────────────────────────────────────────────
COMPANY_NAME = os.getenv("COMPANY_NAME", "Cleannest")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "(530) 555-0100")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "hello@cleannest.com")
COMPANY_WEBSITE = os.getenv("COMPANY_WEBSITE", "www.cleannest.com")
COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "Chico, CA")


def _fmt_slot(slot: TimeSlot) -> str:
    """Format a TimeSlot for display: e.g. 'Tuesday, March 4, 2025 at 10:00 AM (PST)'"""
    try:
        tz = pytz.timezone(slot.timezone)
        dt = datetime.fromisoformat(slot.startISO.replace("Z", "+00:00")).astimezone(tz)
        return dt.strftime("%A, %B %-d, %Y at %-I:%M %p") + f" ({dt.strftime('%Z')})"
    except Exception:
        return slot.startISO


def _fmt_available_slot(slot: TimeSlot) -> str:
    """Format like: 'Tue Mar 4 · 10:00 AM – 12:00 PM'"""
    try:
        tz = pytz.timezone(slot.timezone)
        start = datetime.fromisoformat(slot.startISO.replace("Z", "+00:00")).astimezone(tz)
        end = datetime.fromisoformat(slot.endISO.replace("Z", "+00:00")).astimezone(tz)
        return start.strftime("%a %b %-d · %-I:%M %p") + " – " + end.strftime("%-I:%M %p")
    except Exception:
        return slot.startISO


def generate_quote_pdf(
    lead: Lead,
    service: ServiceInfo,
    quote: Quote,
    available_slots: list[TimeSlot] | None = None,
    booked_slot: TimeSlot | None = None,
) -> bytes:
    """
    Generate a Cleannest quote PDF.

    Args:
        lead: Customer contact info.
        service: Service details.
        quote: Computed quote with line items.
        available_slots: Suggested times (shown when not yet booked).
        booked_slot: Confirmed booking slot (shown prominently when present).

    Returns:
        PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_title = ParagraphStyle(
        "BrandTitle",
        fontSize=26,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    brand_sub = ParagraphStyle(
        "BrandSub",
        fontSize=10,
        fontName="Helvetica",
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    section_header = ParagraphStyle(
        "SectionHeader",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=BRAND_TEAL,
        spaceBefore=14,
        spaceAfter=4,
    )
    body_label = ParagraphStyle(
        "BodyLabel",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=BRAND_DARK,
    )
    body_value = ParagraphStyle(
        "BodyValue",
        fontSize=9,
        fontName="Helvetica",
        textColor=BRAND_DARK,
    )
    footer_style = ParagraphStyle(
        "Footer",
        fontSize=8,
        fontName="Helvetica",
        textColor=BRAND_GREY,
        alignment=TA_CENTER,
    )
    booked_label = ParagraphStyle(
        "BookedLabel",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    booked_value = ParagraphStyle(
        "BookedValue",
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    avail_slot_style = ParagraphStyle(
        "AvailSlot",
        fontSize=9,
        fontName="Helvetica",
        textColor=BRAND_DARK,
        leftIndent=8,
        spaceAfter=3,
    )

    # ── Build content ──────────────────────────────────────────────────────────
    story = []
    page_width = letter[0] - 1.3 * inch  # usable width

    # HEADER TABLE (dark background)
    today_str = datetime.now().strftime("%B %-d, %Y")
    header_data = [
        [Paragraph(COMPANY_NAME, brand_title)],
        [Paragraph("Professional Home Cleaning Services", brand_sub)],
        [Paragraph(f"{COMPANY_WEBSITE}  ·  {COMPANY_PHONE}  ·  {COMPANY_EMAIL}", brand_sub)],
    ]
    header_table = Table(header_data, colWidths=[page_width])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("ROWPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 18),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Quote reference line
    quote_ref = Paragraph(
        f"<font color='#6B7280'>Quote Date:</font> {today_str}",
        ParagraphStyle("QRef", fontSize=8, fontName="Helvetica", textColor=BRAND_GREY, alignment=TA_RIGHT),
    )
    story.append(quote_ref)
    story.append(Spacer(1, 6))

    # ── BOOKED SLOT BANNER ─────────────────────────────────────────────────────
    if booked_slot:
        booked_str = _fmt_slot(booked_slot)
        banner_data = [
            [Paragraph("APPOINTMENT CONFIRMED", booked_label)],
            [Paragraph(booked_str, booked_value)],
            [Paragraph("Please save this to your calendar. We'll see you then!", brand_sub)],
        ]
        banner = Table(banner_data, colWidths=[page_width])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_TEAL),
            ("ROWPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        story.append(banner)
        story.append(Spacer(1, 10))

    # ── CUSTOMER INFO ──────────────────────────────────────────────────────────
    story.append(Paragraph("Customer Information", section_header))
    story.append(HRFlowable(width=page_width, thickness=1, color=BRAND_TEAL, spaceAfter=6))

    def info_row(label: str, value: str) -> list:
        return [
            Paragraph(label, body_label),
            Paragraph(value, body_value),
        ]

    beds_baths = (
        f"{service.beds} bed / {service.baths} bath"
        if service.beds is not None
        else (f"{service.sqft:,} sqft" if service.sqft else "Not specified")
    )
    addons_str = (
        ", ".join(a.replace("_", " ").title() for a in service.addons)
        if service.addons
        else "None"
    )
    freq_label = FREQUENCY_LABELS.get(service.frequency, service.frequency)
    svc_label = SERVICE_TYPE_LABELS.get(service.serviceType, service.serviceType)

    customer_data = [
        info_row("Name", lead.fullName),
        info_row("Phone", lead.phone),
        info_row("Email", lead.email or "—"),
        info_row("Address", f"{lead.address}, {lead.zip}"),
    ]
    customer_table = Table(customer_data, colWidths=[1.5 * inch, page_width - 1.5 * inch])
    customer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
    ]))
    story.append(customer_table)

    # ── SERVICE DETAILS ────────────────────────────────────────────────────────
    story.append(Paragraph("Service Details", section_header))
    story.append(HRFlowable(width=page_width, thickness=1, color=BRAND_TEAL, spaceAfter=6))

    service_data = [
        info_row("Service Type", svc_label),
        info_row("Home Size", beds_baths),
        info_row("Frequency", freq_label),
        info_row("Add-ons", addons_str),
    ]
    if service.notes:
        service_data.append(info_row("Notes", service.notes))

    service_table = Table(service_data, colWidths=[1.5 * inch, page_width - 1.5 * inch])
    service_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, BRAND_LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
    ]))
    story.append(service_table)

    # ── QUOTE LINE ITEMS ───────────────────────────────────────────────────────
    story.append(Paragraph("Quote Summary", section_header))
    story.append(HRFlowable(width=page_width, thickness=1, color=BRAND_TEAL, spaceAfter=6))

    li_header = [
        Paragraph("Description", body_label),
        Paragraph("Amount", ParagraphStyle("RH", fontSize=9, fontName="Helvetica-Bold",
                                           textColor=BRAND_DARK, alignment=TA_RIGHT)),
    ]
    li_rows = [li_header]
    for item in quote.lineItems:
        amount_str = f"-${abs(item.amount):,.2f}" if item.amount < 0 else f"${item.amount:,.2f}"
        li_rows.append([
            Paragraph(item.description, body_value),
            Paragraph(amount_str, ParagraphStyle("Amt", fontSize=9, fontName="Helvetica",
                                                  textColor=BRAND_DARK, alignment=TA_RIGHT)),
        ])

    # Total row
    li_rows.append([
        Paragraph("TOTAL", ParagraphStyle("Tot", fontSize=11, fontName="Helvetica-Bold",
                                           textColor=WHITE)),
        Paragraph(f"${quote.total:,.2f} {quote.currency}",
                  ParagraphStyle("TotAmt", fontSize=11, fontName="Helvetica-Bold",
                                  textColor=WHITE, alignment=TA_RIGHT)),
    ])

    li_table = Table(li_rows, colWidths=[page_width - 1.2 * inch, 1.2 * inch])
    li_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, BRAND_LIGHT]),
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_TEAL),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, -1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(li_table)
    story.append(Spacer(1, 10))

    # ── AVAILABLE SLOTS (if no booking yet) ───────────────────────────────────
    if not booked_slot and available_slots:
        story.append(Paragraph("Available Times", section_header))
        story.append(HRFlowable(width=page_width, thickness=1, color=BRAND_TEAL, spaceAfter=6))
        for i, slot in enumerate(available_slots[:5], start=1):
            story.append(Paragraph(f"{i}.  {_fmt_available_slot(slot)}", avail_slot_style))
        story.append(Spacer(1, 4))
        call_us = Paragraph(
            f"To book any of these times, call us at <b>{COMPANY_PHONE}</b> or reply to this email.",
            ParagraphStyle("CallUs", fontSize=9, fontName="Helvetica", textColor=BRAND_GREY),
        )
        story.append(call_us)

    story.append(Spacer(1, 16))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=page_width, thickness=0.5, color=BRAND_GREY, spaceAfter=6))
    story.append(Paragraph(
        f"{COMPANY_NAME}  ·  {COMPANY_ADDRESS}  ·  {COMPANY_PHONE}  ·  {COMPANY_EMAIL}  ·  {COMPANY_WEBSITE}",
        footer_style,
    ))
    story.append(Paragraph(
        "This quote is valid for 7 days. Prices may vary based on actual home condition.",
        footer_style,
    ))

    doc.build(story)
    return buffer.getvalue()
