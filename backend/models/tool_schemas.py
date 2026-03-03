"""
Pydantic schemas for the Vapi tool webhook endpoint.

Vapi wraps every function tool call in a message envelope:
  {
    "message": {
      "type": "tool-calls",
      "toolCallList": [
        {
          "id": "call_abc",
          "type": "function",
          "function": {
            "name": "send_quote_and_slots",
            "arguments": { ...our actual params... }
          }
        }
      ]
    }
  }

Our endpoint unpacks this envelope, runs the logic, then returns
in the format Vapi expects:
  {
    "results": [
      { "toolCallId": "call_abc", "result": "..." }
    ]
  }
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel

from models.lead import Lead
from models.service_info import ServiceInfo
from models.quote import Quote, TimeSlot, PreferredWindow


# ── Inner arguments (what the agent passes) ──────────────────────────────────

class SendQuoteArgs(BaseModel):
    lead: Lead
    service: ServiceInfo
    preferredWindow: PreferredWindow
    durationMinutes: int | None = None
    quote: Quote | None = None
    availableSlots: list[TimeSlot] | None = None
    bookedSlot: TimeSlot | None = None


# ── Vapi webhook envelope models ─────────────────────────────────────────────

class VapiFunctionCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class VapiToolCall(BaseModel):
    id: str
    type: str = "function"
    function: VapiFunctionCall


class VapiMessage(BaseModel):
    type: str
    toolCallList: list[VapiToolCall] | None = None
    # Vapi also sends call metadata here; we only need what's above
    model_config = {"extra": "allow"}


class VapiWebhookPayload(BaseModel):
    message: VapiMessage
    model_config = {"extra": "allow"}


# ── Vapi response format ──────────────────────────────────────────────────────

class ToolCallResult(BaseModel):
    toolCallId: str
    result: str


class VapiToolResponse(BaseModel):
    results: list[ToolCallResult]


# ── Legacy direct-call schema (used for local testing via curl/Postman) ───────

class SendQuoteRequest(SendQuoteArgs):
    """Flat schema used when calling the endpoint directly (not via Vapi)."""
    pass
