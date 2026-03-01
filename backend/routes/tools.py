"""
Vapi tool webhook endpoint.

Calendar availability checking and booking are handled natively by
Vapi's built-in Google Calendar tools. This file contains only the
one custom endpoint our backend needs to own:

  POST /tools/send_quote_and_slots
    - Runs the pricing engine (or uses a pre-computed quote)
    - Generates a branded PDF quote
    - Emails it to the customer via SendGrid
    - Returns ok:true so the agent can confirm on the call

The agent calls this endpoint:
  (A) After checkAvailability returns slots  → passes availableSlots in
  (B) After createEvent confirms a booking   → passes bookedSlot in
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.tool_schemas import SendQuoteRequest
from services.pricing import calculate_quote
from services.pdf_service import generate_quote_pdf
from services.email_service import send_quote_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


def _error(code: str, message: str) -> JSONResponse:
    """Structured error the Vapi agent can act on. Always HTTP 200 so Vapi reads the body."""
    return JSONResponse(
        status_code=200,
        content={"ok": False, "errorCode": code, "error": message},
    )


@router.post("/send_quote_and_slots", response_model=None)
async def send_quote_and_slots(payload: SendQuoteRequest) -> JSONResponse:
    """
    Pricing + PDF + Email endpoint.

    Called by the Vapi agent in two scenarios:
      1. After native checkAvailability — to email the quote + available times.
      2. After native createEvent — to email the updated quote + confirmed booking.

    The agent passes `availableSlots` (from scenario 1) and/or
    `bookedSlot` (from scenario 2) so both can appear in the PDF.
    """
    lead = payload.lead

    # Email is required to send anything
    if not lead.email:
        return _error(
            "missing_email",
            "I need an email address to send you the quote. Could you share it with me?",
        )

    try:
        # Compute quote server-side if agent didn't supply one
        quote = payload.quote if payload.quote else calculate_quote(payload.service)

        # Generate branded PDF
        pdf_bytes = generate_quote_pdf(
            lead=lead,
            service=payload.service,
            quote=quote,
            available_slots=payload.availableSlots,
            booked_slot=payload.bookedSlot,
        )

        # Send email with PDF attachment
        try:
            send_quote_email(
                lead=lead,
                quote=quote,
                pdf_bytes=pdf_bytes,
                available_slots=payload.availableSlots,
                booked_slot=payload.bookedSlot,
            )
        except ValueError:
            return _error(
                "invalid_email",
                "That email address doesn't look right. Could you spell it out for me?",
            )
        except RuntimeError as exc:
            logger.error("Email delivery failed: %s", exc)
            return _error(
                "email_failed",
                "I had trouble sending the email. Could you double-check your email address?",
            )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "quoteTotal": quote.total,
                "quoteCurrency": quote.currency,
                "emailedTo": lead.email,
                "bookedSlot": payload.bookedSlot.model_dump() if payload.bookedSlot else None,
            },
        )

    except Exception as exc:
        logger.exception("Unexpected error in send_quote_and_slots: %s", exc)
        return _error(
            "server_error",
            "Something went wrong on my end. Please try again in a moment.",
        )
