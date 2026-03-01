"""
Cleannest AI Receptionist — FastAPI Backend

Entry point. Run with:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env before anything else
load_dotenv()

# Ensure backend/ is on sys.path when running directly
sys.path.insert(0, os.path.dirname(__file__))

from routes.health import router as health_router
from routes.tools import router as tools_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Cleannest AI Receptionist",
    description=(
        "Backend for the Cleannest AI voice receptionist. "
        "Provides Vapi tool webhook endpoints for quote generation, "
        "Google Calendar availability checking, and live booking."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Vapi sends webhooks from their servers; allow all origins for tool endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(tools_router)

# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "errorCode": "server_error",
            "error": "An unexpected server error occurred.",
        },
    )


# ── Startup / shutdown events ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "(not set)")
    logger.info("=" * 60)
    logger.info("Cleannest AI Receptionist backend starting up")
    logger.info("  BASE_URL      : %s", base_url)
    logger.info("  SENDGRID_FROM : %s", from_email)
    logger.info("  Tool endpoint : POST %s/tools/send_quote_and_slots", base_url)
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Cleannest backend shutting down.")
