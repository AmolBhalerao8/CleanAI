"""
Email service for CleanAI using the Gmail API (HTTP-based OAuth).

Gmail SMTP (port 465/587) is blocked on Render's free tier.
The Gmail API sends over HTTPS (port 443) — no restrictions.

Required env vars:
  GMAIL_USER          — your Gmail address (amols.emailid@gmail.com)
  GMAIL_CLIENT_ID     — from Google Cloud Console OAuth credentials
  GMAIL_CLIENT_SECRET — from Google Cloud Console OAuth credentials
  GMAIL_REFRESH_TOKEN — generated once via tools/get_refresh_token.py

To get your refresh token, run this once on your local machine:
  cd backend && python tools/get_refresh_token.py
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.lead import Lead
from models.quote import Quote, TimeSlot

logger = logging.getLogger(__name__)

COMPANY_NAME = os.getenv("COMPANY_NAME", "CleanAI")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "(530) 508-3355")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "amols.emailid@gmail.com")
COMPANY_WEBSITE = os.getenv("COMPANY_WEBSITE", "www.cleanai.com")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN", "")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_gmail_service():
    """Build an authenticated Gmail API service using the stored refresh token."""
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=GMAIL_SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _fmt_slot_human(slot: TimeSlot) -> str:
    try:
        tz = pytz.timezone(slot.timezone)
        dt = datetime.fromisoformat(slot.startISO.replace("Z", "+00:00")).astimezone(tz)
        return dt.strftime("%A, %B %d, %Y at %I:%M %p") + f" ({dt.strftime('%Z')})"
    except Exception:
        return slot.startISO


def _fmt_slot_short(slot: TimeSlot) -> str:
    try:
        tz = pytz.timezone(slot.timezone)
        start = datetime.fromisoformat(slot.startISO.replace("Z", "+00:00")).astimezone(tz)
        end = datetime.fromisoformat(slot.endISO.replace("Z", "+00:00")).astimezone(tz)
        return start.strftime("%a %b %d · %I:%M %p") + " – " + end.strftime("%I:%M %p")
    except Exception:
        return slot.startISO


def _build_subject(lead: Lead, booked_slot: TimeSlot | None) -> str:
    first = lead.fullName.split()[0]
    if booked_slot:
        return f"{COMPANY_NAME} – Your Booking is Confirmed, {first}!"
    return f"{COMPANY_NAME} – Your Cleaning Quote is Ready, {first}!"


def _build_html(
    lead: Lead,
    quote: Quote,
    available_slots: list[TimeSlot] | None,
    booked_slot: TimeSlot | None,
) -> str:
    first_name = lead.fullName.split()[0]

    if booked_slot:
        banner = f"""
        <div style="background:#1A8F7A;border-radius:8px;padding:18px 24px;text-align:center;margin-bottom:24px;">
          <p style="color:#fff;font-size:13px;margin:0 0 4px 0;font-weight:600;letter-spacing:1px;">APPOINTMENT CONFIRMED</p>
          <p style="color:#fff;font-size:18px;font-weight:700;margin:0 0 6px 0;">{_fmt_slot_human(booked_slot)}</p>
          <p style="color:#cef7ef;font-size:12px;margin:0;">Please save this to your calendar. We look forward to seeing you!</p>
        </div>"""
        intro = f"<p>Hi {first_name},</p><p>You're all set! Your cleaning appointment has been confirmed. Here's a summary of your quote and booking.</p>"
    else:
        banner = ""
        intro = f"<p>Hi {first_name},</p><p>Thanks for reaching out to {COMPANY_NAME}. Your personalised quote is attached as a PDF. Here's a quick summary:</p>"

    li_rows = ""
    for item in quote.lineItems:
        color = "#C0392B" if item.amount < 0 else "#1C2B36"
        amount_str = f"-${abs(item.amount):,.2f}" if item.amount < 0 else f"${item.amount:,.2f}"
        li_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#374151;">{item.description}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;color:{color};text-align:right;">{amount_str}</td>
        </tr>"""

    slots_section = ""
    if not booked_slot and available_slots:
        slot_items = "".join(
            f'<li style="margin-bottom:6px;font-size:13px;color:#374151;">{_fmt_slot_short(s)}</li>'
            for s in available_slots[:5]
        )
        slots_section = f"""
        <h3 style="color:#1A8F7A;font-size:14px;margin:24px 0 8px;">Available Times</h3>
        <ul style="padding-left:18px;margin:0 0 16px 0;">{slot_items}</ul>
        <p style="font-size:13px;color:#6B7280;">
          Call us at <a href="tel:{COMPANY_PHONE}" style="color:#1A8F7A;">{COMPANY_PHONE}</a>
          or reply to this email to lock in a time.
        </p>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:#1C2B36;padding:28px 32px;text-align:center;">
            <h1 style="color:#ffffff;margin:0;font-size:28px;font-weight:800;">{COMPANY_NAME}</h1>
            <p style="color:#94A3B8;margin:4px 0 0;font-size:13px;">Professional Home Cleaning Services</p>
          </td>
        </tr>
        <tr><td style="padding:32px;">
          {banner}
          {intro}
          <h3 style="color:#1A8F7A;font-size:14px;margin:20px 0 8px;">Quote Summary</h3>
          <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #E5E7EB;">
            <thead>
              <tr style="background:#1C2B36;">
                <th style="padding:10px 12px;text-align:left;font-size:12px;color:#fff;">Description</th>
                <th style="padding:10px 12px;text-align:right;font-size:12px;color:#fff;">Amount</th>
              </tr>
            </thead>
            <tbody>{li_rows}
              <tr style="background:#1A8F7A;">
                <td style="padding:12px;font-size:14px;font-weight:700;color:#fff;">TOTAL</td>
                <td style="padding:12px;font-size:14px;font-weight:700;color:#fff;text-align:right;">${quote.total:,.2f} {quote.currency}</td>
              </tr>
            </tbody>
          </table>
          {slots_section}
          <p style="margin-top:28px;font-size:13px;color:#374151;">Your full quote PDF is attached. If you have any questions, feel free to reach out!</p>
          <p style="font-size:13px;color:#374151;">— The {COMPANY_NAME} Team</p>
        </td></tr>
        <tr>
          <td style="background:#F9FAFB;padding:16px 32px;text-align:center;border-top:1px solid #E5E7EB;">
            <p style="margin:0;font-size:11px;color:#9CA3AF;">
              {COMPANY_NAME} &nbsp;·&nbsp; {COMPANY_PHONE} &nbsp;·&nbsp;
              <a href="mailto:{COMPANY_EMAIL}" style="color:#1A8F7A;">{COMPANY_EMAIL}</a> &nbsp;·&nbsp;
              <a href="https://{COMPANY_WEBSITE}" style="color:#1A8F7A;">{COMPANY_WEBSITE}</a>
            </p>
            <p style="margin:4px 0 0;font-size:10px;color:#D1D5DB;">This quote is valid for 7 days.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_quote_email(
    lead: Lead,
    quote: Quote,
    pdf_bytes: bytes,
    available_slots: list[TimeSlot] | None = None,
    booked_slot: TimeSlot | None = None,
) -> None:
    """
    Send a quote email with attached PDF via the Gmail API.

    Raises:
        ValueError: If no email address is present on the lead.
        RuntimeError: If Gmail credentials are missing or the API call fails.
    """
    if not lead.email:
        raise ValueError("Cannot send email: no email address on lead.")

    missing = [k for k, v in {
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_CLIENT_ID": GMAIL_CLIENT_ID,
        "GMAIL_CLIENT_SECRET": GMAIL_CLIENT_SECRET,
        "GMAIL_REFRESH_TOKEN": GMAIL_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing Gmail API credentials: {', '.join(missing)}. "
            "Run backend/tools/get_refresh_token.py to set them up."
        )

    subject = _build_subject(lead, booked_slot)
    html_content = _build_html(lead, quote, available_slots, booked_slot)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{COMPANY_NAME} <{GMAIL_USER}>"
    msg["To"] = lead.email

    msg.attach(MIMEText(html_content, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename="cleanai_quote.pdf")
    msg.attach(pdf_part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    try:
        service = _get_gmail_service()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info("Quote email sent via Gmail API — message_id=%s to=%s", result.get("id"), lead.email)
    except HttpError as exc:
        logger.error("Gmail API HTTP error: %s", exc)
        raise RuntimeError(f"Gmail API error: {exc}") from exc
    except Exception as exc:
        logger.error("Gmail API error: %s", exc)
        raise RuntimeError(f"Failed to send email: {exc}") from exc
