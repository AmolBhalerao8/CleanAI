"""
Vapi tool webhook endpoint.

Vapi sends function-tool calls wrapped in a message envelope:
  POST /tools/send_quote_and_slots
  Body: { "message": { "type": "tool-calls", "toolCallList": [...] } }

We unpack the envelope, run pricing + PDF + email, then respond in
the format Vapi expects:
  { "results": [{ "toolCallId": "...", "result": "..." }] }

If the body is NOT a Vapi envelope (e.g. a direct curl test), we fall
back to treating the body as flat SendQuoteArgs.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models.tool_schemas import (
    SendQuoteArgs,
    VapiWebhookPayload,
    VapiToolResponse,
    ToolCallResult,
)
from services.pricing import calculate_quote
from services.pdf_service import generate_quote_pdf
from services.email_service import send_quote_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


def _vapi_error(tool_call_id: str, code: str, message: str) -> JSONResponse:
    """Return an error in Vapi's expected results format (always HTTP 200)."""
    payload = json.dumps({"ok": False, "errorCode": code, "error": message})
    return JSONResponse(
        status_code=200,
        content={"results": [{"toolCallId": tool_call_id, "result": payload}]},
    )


def _vapi_ok(tool_call_id: str, data: dict) -> JSONResponse:
    """Return a success in Vapi's expected results format."""
    return JSONResponse(
        status_code=200,
        content={"results": [{"toolCallId": tool_call_id, "result": json.dumps(data)}]},
    )


async def _process_args(args: SendQuoteArgs, tool_call_id: str) -> JSONResponse:
    """Core logic: pricing → PDF → email → respond."""
    lead = args.lead

    if not lead.email:
        return _vapi_error(
            tool_call_id,
            "missing_email",
            "I need an email address to send you the quote. Could you share it with me?",
        )

    try:
        quote = args.quote if args.quote else calculate_quote(args.service)

        pdf_bytes = generate_quote_pdf(
            lead=lead,
            service=args.service,
            quote=quote,
            available_slots=args.availableSlots,
            booked_slot=args.bookedSlot,
        )

        try:
            send_quote_email(
                lead=lead,
                quote=quote,
                pdf_bytes=pdf_bytes,
                available_slots=args.availableSlots,
                booked_slot=args.bookedSlot,
            )
        except ValueError:
            return _vapi_error(
                tool_call_id,
                "invalid_email",
                "That email address doesn't look right. Could you spell it out for me?",
            )
        except RuntimeError as exc:
            logger.error("Email delivery failed: %s", exc)
            return _vapi_error(
                tool_call_id,
                "email_failed",
                "I had trouble sending the email. Could you double-check your email address?",
            )

        return _vapi_ok(
            tool_call_id,
            {
                "ok": True,
                "quoteTotal": quote.total,
                "quoteCurrency": quote.currency,
                "emailedTo": lead.email,
                "bookedSlot": args.bookedSlot.model_dump() if args.bookedSlot else None,
            },
        )

    except Exception as exc:
        logger.exception("Unexpected error in send_quote_and_slots: %s", exc)
        return _vapi_error(
            tool_call_id,
            "server_error",
            "Something went wrong on my end. Please try again in a moment.",
        )


@router.post("/send_quote_and_slots", response_model=None)
async def send_quote_and_slots(request: Request) -> JSONResponse:
    """
    Handles both Vapi envelope calls and direct test calls.

    Vapi format (production):
      { "message": { "type": "tool-calls", "toolCallList": [...] } }

    Direct format (testing):
      { "lead": {...}, "service": {...}, "preferredWindow": {...} }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    logger.info("Received POST /tools/send_quote_and_slots — body keys: %s", list(body.keys()))

    # ── Vapi envelope format ──────────────────────────────────────────────────
    if "message" in body:
        try:
            payload = VapiWebhookPayload.model_validate(body)
        except Exception as exc:
            logger.error("Failed to parse Vapi envelope: %s", exc)
            return JSONResponse(status_code=422, content={"error": str(exc)})

        tool_calls = payload.message.toolCallList or []
        if not tool_calls:
            logger.warning("Vapi payload had no toolCallList entries")
            return JSONResponse(status_code=200, content={"results": []})

        # Process first tool call (Vapi always sends one per request to this URL)
        tc = tool_calls[0]
        tool_call_id = tc.id
        raw_args = tc.function.arguments
        logger.info("Tool call id=%s  name=%s", tool_call_id, tc.function.name)
        logger.info("Tool arguments: %s", json.dumps(raw_args, default=str))

        try:
            args = SendQuoteArgs.model_validate(raw_args)
        except Exception as exc:
            logger.error("Invalid tool arguments: %s", exc)
            return _vapi_error(tool_call_id, "invalid_args", f"Invalid arguments: {exc}")

        return await _process_args(args, tool_call_id)

    # ── Direct / test format (no envelope) ───────────────────────────────────
    else:
        logger.info("Direct call (no Vapi envelope) — treating as flat SendQuoteArgs")
        try:
            args = SendQuoteArgs.model_validate(body)
        except Exception as exc:
            logger.error("Invalid direct-call body: %s", exc)
            return JSONResponse(status_code=422, content={"error": str(exc)})

        return await _process_args(args, tool_call_id="direct-test")
