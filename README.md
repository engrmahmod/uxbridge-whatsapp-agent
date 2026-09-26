# UX Bridge WhatsApp AI Agent

A WhatsApp chatbot for **UX BRIDGE IMPORT & EXPORT** (import/export business).
Built on the **WhatsApp Business Cloud API (Meta)**. It answers customer
questions, guides a quote flow (generating `UB-XXXXXX` references), shares
shipment-tracking links (DHL + Fish Logistics), and flags chats that need a
human — 24/7.

This is a **test agent for a new/fresh WhatsApp number**, separate from the
main business line.

No AI model / no API keys are needed for the replies: matching is
keyword-based (`brain.py`), so the agent is free to run.

## What it does

- Auto-replies: greeting, services list, vehicle shipping, cargo & freight,
  construction, solar, tracking help, contact info, fallback
- Quote flow: name → service → description → reference `UB-XXXXXX` stored in
  SQLite (`Type QUOTE` to start, `CANCEL` anytime)
- "Speak to human" detection: flags the conversation and asks the team to reply
- Admin page (`/admin`) listing recent conversations and quote requests
  (currently open — protect it before real traffic, see below)

## Environment variables (never commit these)

| Variable          | What it is                                              |
|-------------------|---------------------------------------------------------|
| `VERIFY_TOKEN`    | Token you choose when subscribing the webhook in Meta   |
| `WHATSAPP_TOKEN`  | Permanent access token for your WhatsApp Business app   |
| `PHONE_NUMBER_ID` | The WhatsApp number's `phone_number_id` from Meta       |

## Deploy on Render (free tier)

1. Push this repo to GitHub.
2. In Render: **New → Web Service → from this repo**.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add the three environment variables above.
6. Note your public URL, e.g. `https://uxbridge-whatsapp-agent.onrender.com`.

`render.yaml` is included for one-click blueprint deploys.

## Connect to WhatsApp (Meta setup)

1. Create an app at [developers.facebook.com](https://developers.facebook.com)
   → add the **WhatsApp** product.
2. Get a test WhatsApp number in the WhatsApp dashboard (or add your own
   number later). Copy its `phone_number_id` and generate a permanent
   access token.
3. Subscribe the webhook: callback URL `https://YOUR-RENDER-URL/webhook`,
   verify token = your `VERIFY_TOKEN`, and subscribe to the `messages` field.
4. Meta will call `GET /webhook` with `hub.mode`, `hub.verify_token` and
   `hub.challenge` — the app answers with the challenge when the token
   matches.
5. Send a test message to the WhatsApp test number; the agent replies and
   conversations appear on `/admin`.

Follow Meta's official docs for exact steps (they change over time):
[developers.facebook.com/docs/whatsapp/cloud-api](https://developers.facebook.com/docs/whatsapp/cloud-api)

## Local test

```bash
pip install -r requirements.txt
VERIFY_TOKEN=test123 python app.py
# then visit http://localhost:5000 and /admin
```

## Protect the admin page

`/admin` has no password yet (by design for easy testing). Before real
customers use the agent, add one of: HTTP basic auth, a secret query token,
or Render IP allow-listing — then remove this note.
