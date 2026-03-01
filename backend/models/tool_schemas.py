"""
Pydantic schemas for the Vapi tool webhook endpoint.

Only one custom endpoint remains:
  POST /tools/send_quote_and_slots

Calendar availability checking and event creation are handled
natively by Vapi's built-in Google Calendar tools
(google.calendar.availability.check and google.calendar.event.create).
The agent passes the slots it already retrieved from the native tool
into this endpoint so they can be included in the PDF and email.
"""
from __future__ import annotations
from pydantic import BaseModel

from models.lead import Lead
from models.service_info import ServiceInfo
from models.quote import Quote, TimeSlot, PreferredWindow


# ── Inbound request payload from Vapi ────────────────────────────────────────

class SendQuoteRequest(BaseModel):
    lead: Lead
    service: ServiceInfo
    preferredWindow: PreferredWindow
    durationMinutes: int | None = None
    # Quote is optional: if omitted the pricing engine calculates it server-side
    quote: Quote | None = None
    # Slots already retrieved by Vapi's native checkAvailability tool
    availableSlots: list[TimeSlot] | None = None
    # Included only on the second call, after Vapi's createEvent tool succeeds
    bookedSlot: TimeSlot | None = None


# ── Outbound response payload returned to Vapi ───────────────────────────────

class SendQuoteResponse(BaseModel):
    ok: bool
    quoteTotal: float | None = None
    quoteCurrency: str | None = None
    emailedTo: str | None = None
    error: str | None = None
    errorCode: str | None = None
