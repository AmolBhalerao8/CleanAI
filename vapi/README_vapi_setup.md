# Vapi + Cleannest AI Receptionist — Setup Guide

Complete setup in 3 steps: SendGrid → FastAPI backend → Vapi.
No Google Cloud console, no service accounts, no API keys for calendar.

---

## Step 1 — SendGrid: Create API Key + Verify Sender

1. Sign up or log in at [sendgrid.com](https://sendgrid.com).
2. Go to **Settings → API Keys → Create API Key**.
   - Name: `cleannest-quotes`
   - Permission: **Restricted Access → Mail Send: Full Access**
   - Click **Create & View** and copy the key immediately (shown once).
3. Go to **Settings → Sender Authentication**.
   - For quick start: **Single Sender Verification** — verify your email address.
   - For production: **Domain Authentication** — add DNS records for your domain.
4. Note the verified sender email you'll use as `SENDGRID_FROM_EMAIL`.

---

## Step 2 — Run the Backend

### Install dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### Configure environment variables

```bash
copy .env.example .env
```

Edit `.env` with your real values:

```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=quotes@yourdomain.com
SENDGRID_FROM_NAME=Cleannest Quotes

COMPANY_NAME=Cleannest
COMPANY_PHONE=(530) 555-0100
COMPANY_EMAIL=hello@cleannest.com
COMPANY_WEBSITE=www.cleannest.com
COMPANY_ADDRESS=Chico, CA

BASE_URL=https://xxxx.ngrok.io
```

### Start the server

```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to confirm it's running.

### Expose locally with ngrok

Vapi needs a public HTTPS URL to call your tool webhook during live calls.

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok.io` URL and update `BASE_URL` in your `.env`, then restart the backend.

> **For production:** Deploy to [Railway](https://railway.app) or [Render](https://render.com). Set your env vars in their dashboard. Your `BASE_URL` becomes your permanent deployment URL — no ngrok needed.

---

## Step 3 — Set Up the Vapi Assistant

### 3a. Connect Google Calendar (one click)

1. Log in to [vapi.ai](https://vapi.ai).
2. Go to **Integrations → Tools Provider → Google Calendar**.
3. Click **Connect** and authorise with the Google account whose calendar you want to use for bookings.
4. Vapi will have access to create and read events on that calendar.

That's it — no service account, no Google Cloud console.

### 3b. Create the assistant

1. Go to **Assistants → + Create Assistant** → choose **Blank**.
2. Switch to the **JSON editor** (toggle top-right).
3. Paste the full contents of `vapi/agent_config.json`.
4. Replace `{{BASE_URL}}` with your real backend URL:
   ```
   "url": "https://xxxx.ngrok.io/tools/send_quote_and_slots"
   ```
5. Click **Save**.

### 3c. Verify tools are attached

In the assistant's **Tools** tab, you should see three tools:
- `checkAvailability` — Google Calendar (native)
- `createEvent` — Google Calendar (native)
- `send_quote_and_slots` — Custom (your backend)

### 3d. Attach a phone number

1. Go to **Phone Numbers → + Buy Number** and purchase a US number.
2. In number settings, set **Assistant** to your Cleannest AI Receptionist.
3. Click **Save**.

Call the number. The agent will greet you immediately.

---

## How the Three Tools Work Together

```
Caller confirms preferred window
        ↓
checkAvailability  →  Vapi native → reads free slots from your Google Calendar
        ↓
Agent reads 2-3 slots to caller + calls send_quote_and_slots
        ↓
send_quote_and_slots  →  Your backend → pricing + PDF + SendGrid email
        ↓
Caller picks a slot and says "book it"
        ↓
createEvent  →  Vapi native → creates event on your Google Calendar
        ↓
send_quote_and_slots (again, with bookedSlot)  →  Your backend → sends updated PDF
```

---

## Testing Checklist

- [ ] `GET https://your-backend/health` returns `{ "status": "ok" }`
- [ ] Call the Vapi number — agent greets you
- [ ] Agent collects all required fields correctly
- [ ] After all fields collected, agent calls `checkAvailability` and reads slots aloud
- [ ] `send_quote_and_slots` is called — quote email + PDF arrives in inbox
- [ ] PDF shows correct pricing (service type, beds/baths, add-ons, frequency discount)
- [ ] Say "book the first one" — agent calls `createEvent` — event appears on Google Calendar live
- [ ] Second `send_quote_and_slots` is called — updated email arrives with booking confirmed
- [ ] PDF shows the confirmed booking prominently
- [ ] Missing email scenario — agent asks for email, spells it back, retries

---

## Pricing Adjustments

Edit `backend/services/pricing.py` to change any rate:

| Constant | Controls |
|---|---|
| `BASE_RATES` | Base price per service type |
| `BED_RATE` | Extra per bedroom above 1 |
| `BATH_RATE` | Extra per bathroom above 1 |
| `SQFT_TIERS` | Per-sqft pricing tiers |
| `FREQUENCY_DISCOUNTS` | Discount % by frequency |
| `ADDON_RATES` | Flat fee per add-on |

---

## Troubleshooting

**Backend won't start**
- Confirm Python 3.11+ with `python --version`
- Confirm venv is activated before running `pip install`

**Email not sending**
- Check `SENDGRID_API_KEY` has no extra spaces
- Confirm the sender email is verified in SendGrid dashboard
- Check backend logs for the exact SendGrid error message

**Vapi not calling the tool**
- Confirm the `send_quote_and_slots` server URL in the agent config is HTTPS and reachable
- Test it directly with Postman: `POST https://your-backend/tools/send_quote_and_slots`
- Vapi times out if the endpoint takes more than ~20 seconds

**Google Calendar not showing events**
- Confirm you authorised the correct Google account in Vapi Integrations
- Check Vapi Dashboard logs for the `createEvent` call response

**ngrok URL expired**
- Free ngrok sessions expire after a few hours. Re-run `ngrok http 8000`, update `BASE_URL` in `.env` and the `send_quote_and_slots` server URL in the Vapi agent config.
