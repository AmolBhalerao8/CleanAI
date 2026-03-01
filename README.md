# Cleannest AI Voice Receptionist

An AI-powered voice receptionist and booking assistant for Cleannest, built with:

- **Vapi** — AI voice agent (handles calls, collects info, calls tools live)
- **Vapi Native Google Calendar** — Availability checking and booking via OAuth (no service account needed)
- **FastAPI** — Backend for pricing engine, PDF generation, and email
- **ReportLab** — PDF quote generation
- **SendGrid** — Email delivery with PDF attachment

---

## How It Works

1. A customer calls the Vapi phone number
2. The AI agent collects all required booking details (address, service type, home size, contact info, preferred time)
3. Vapi's native `checkAvailability` tool queries Google Calendar live and the agent reads back 2–3 open slots
4. Our `send_quote_and_slots` backend endpoint runs the pricing engine, generates a PDF quote, and emails it — all during the call
5. If the caller wants to book, Vapi's native `createEvent` tool creates the Google Calendar event instantly
6. Our `send_quote_and_slots` is called a second time with the confirmed booking — an updated PDF with the booked time is emailed immediately

---

## Project Structure

```
cleanai/
├── backend/
│   ├── main.py                   # FastAPI app entrypoint
│   ├── routes/
│   │   ├── tools.py              # Vapi tool webhook endpoints
│   │   └── health.py             # Health check
│   ├── services/
│   │   ├── pricing.py            # Pricing engine
│   │   ├── calendar_service.py   # Google Calendar integration
│   │   ├── pdf_service.py        # PDF quote generator
│   │   └── email_service.py      # SendGrid email sender
│   ├── models/
│   │   ├── lead.py
│   │   ├── service_info.py
│   │   └── quote.py
│   ├── .env.example
│   └── requirements.txt
├── vapi/
│   ├── agent_config.json         # Full Vapi agent definition
│   └── README_vapi_setup.md      # Step-by-step Vapi setup guide
└── README.md
```

---

## Quick Start

### 1. Set up the backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env — only SendGrid keys and company info needed
```

### 3. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.

### 5. Expose locally with ngrok (for Vapi to reach your backend)

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok.io` URL and set it as `BASE_URL` in your `.env`.

### 6. Set up the Vapi agent

See [vapi/README_vapi_setup.md](vapi/README_vapi_setup.md) for full step-by-step instructions.

---

## Environment Variables

Google Calendar credentials are **not** needed — Vapi handles the calendar via OAuth.

| Variable | Description |
|---|---|
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Verified sender email |
| `SENDGRID_FROM_NAME` | Sender display name |
| `COMPANY_NAME` | Company name for PDF/email branding |
| `COMPANY_PHONE` | Company phone for PDF footer |
| `COMPANY_EMAIL` | Company email for PDF footer |
| `COMPANY_WEBSITE` | Company website for PDF footer |
| `BASE_URL` | Public URL of this backend (for Vapi webhooks) |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/tools/send_quote_and_slots` | Generate quote, check calendar, email PDF |
| `POST` | `/tools/book_confirmed_slot` | Book a confirmed slot on Google Calendar |

---

## Pricing

Pricing is calculated server-side by the pricing engine (`services/pricing.py`). Rates can be adjusted directly in that file.

| Service Type | Base Rate |
|---|---|
| Standard | $120 |
| Deep Clean | $200 |
| Move-in/Move-out | $250 |
| Airbnb Turnover | $150 |

Frequency discounts: Weekly −20%, Biweekly −15%, Monthly −10%

Add-ons: Inside fridge ($45), Inside oven ($35), Interior windows ($50), Laundry ($40), Cabinets ($60)
