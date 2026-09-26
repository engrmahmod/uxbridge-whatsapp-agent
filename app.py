"""UX Bridge WhatsApp AI agent — Flask webhook for the WhatsApp Business Cloud API.

Endpoints:
  GET  /          health check
  GET  /webhook   Meta verification (hub.mode / hub.verify_token / hub.challenge)
  POST /webhook   incoming Cloud API events -> brain replies -> Graph API send
  GET  /admin     simple page listing recent conversations and quote requests

Secrets come ONLY from environment variables:
  VERIFY_TOKEN     token you chose when subscribing the webhook in Meta
  WHATSAPP_TOKEN   permanent access token for the WhatsApp Business app
  PHONE_NUMBER_ID  the WhatsApp test number's phone_number_id

SQLite database lives under the Flask instance folder (instance/agent.db).
"""

import json
import os
import sqlite3
import time
from html import escape

import requests
from flask import Flask, Response, g, request

from brain import get_reply

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
GRAPH_VERSION = "v21.0"

app = Flask(__name__, instance_relative_config=True)
os.makedirs(app.instance_path, exist_ok=True)
DB_PATH = os.path.join(app.instance_path, "agent.db")


# ---------------- database ----------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """CREATE TABLE IF NOT EXISTS conversations (
               phone TEXT PRIMARY KEY,
               profile_name TEXT DEFAULT '',
               quote_state TEXT,
               quote_data TEXT DEFAULT '{}',
               needs_human INTEGER DEFAULT 0,
               last_seen INTEGER DEFAULT 0
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS messages (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               phone TEXT NOT NULL,
               direction TEXT NOT NULL,
               text TEXT DEFAULT '',
               created_at INTEGER DEFAULT 0
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS quotes (
               reference TEXT PRIMARY KEY,
               phone TEXT NOT NULL,
               name TEXT DEFAULT '',
               service TEXT DEFAULT '',
               description TEXT DEFAULT '',
               created_at INTEGER DEFAULT 0
           )"""
    )
    db.commit()
    db.close()


init_db()


# ---------------- helpers ----------------

def log_message(phone, direction, text):
    db = get_db()
    db.execute(
        "INSERT INTO messages (phone, direction, text, created_at) VALUES (?, ?, ?, ?)",
        (phone, direction, text or "", int(time.time())),
    )
    db.commit()


def send_whatsapp(to_phone, text):
    """Send one text message via the Cloud API. Returns True on success.

    Silently skips when tokens are not configured (local testing).
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        app.logger.info("WHATSAPP_TOKEN/PHONE_NUMBER_ID not set; skipped send to %s", to_phone)
        return False
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 - log and continue
        app.logger.error("send failed to %s: %s", to_phone, exc)
        return False


def handle_message(sender, profile_name, body):
    db = get_db()
    now = int(time.time())
    row = db.execute(
        "SELECT quote_state, quote_data FROM conversations WHERE phone = ?",
        (sender,),
    ).fetchone()
    state = row["quote_state"] if row else None
    try:
        state_data = json.loads(row["quote_data"]) if row and row["quote_data"] else {}
    except (json.JSONDecodeError, TypeError):
        state_data = {}

    replies, new_state, actions, quote_record = get_reply(
        sender, profile_name or "", body, state, state_data
    )

    db.execute(
        """INSERT INTO conversations (phone, profile_name, quote_state, quote_data, last_seen)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(phone) DO UPDATE SET
             profile_name=excluded.profile_name,
             quote_state=excluded.quote_state,
             quote_data=excluded.quote_data,
             last_seen=excluded.last_seen""",
        (sender, profile_name or "", new_state, json.dumps(state_data), now),
    )
    if actions.get("needs_human"):
        db.execute("UPDATE conversations SET needs_human = 1 WHERE phone = ?", (sender,))
    if quote_record:
        db.execute(
            """INSERT OR IGNORE INTO quotes
               (reference, phone, name, service, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (quote_record["reference"], sender, quote_record["name"],
             quote_record["service"], quote_record["description"], now),
        )
        db.execute("UPDATE conversations SET needs_human = 0 WHERE phone = ?", (sender,))
    db.commit()

    log_message(sender, "in", body)
    for reply in replies:
        log_message(sender, "out", reply)
        send_whatsapp(sender, reply)


# ---------------- routes ----------------

@app.get("/")
def health():
    return {"status": "ok", "service": "uxbridge-whatsapp-agent"}


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token and token == VERIFY_TOKEN:
        return Response(challenge or "", status=200, mimetype="text/plain")
    return Response("Verification failed", status=403)


@app.post("/webhook")
def incoming_webhook():
    data = request.get_json(force=True, silent=True) or {}
    if data.get("object") != "whatsapp_business_account":
        return Response("EVENT_RECEIVED", status=200)
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {
                c.get("wa_id"): (c.get("profile") or {}).get("name", "")
                for c in value.get("contacts", [])
            }
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                sender = msg.get("from")
                body = (msg.get("text") or {}).get("body", "")
                if sender and body:
                    handle_message(sender, contacts.get(sender, ""), body)
    return Response("EVENT_RECEIVED", status=200)


@app.get("/admin")
def admin():
    db = get_db()
    convos = db.execute(
        """SELECT phone, profile_name, quote_state, needs_human,
                  datetime(last_seen, 'unixepoch') AS seen
           FROM conversations ORDER BY last_seen DESC LIMIT 50"""
    ).fetchall()
    quotes = db.execute(
        """SELECT reference, phone, name, service, description,
                  datetime(created_at, 'unixepoch') AS created_at
           FROM quotes ORDER BY created_at DESC LIMIT 50"""
    ).fetchall()

    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (escape(c["phone"]), escape(c["profile_name"] or ""),
           escape(c["quote_state"] or "—"),
           "YES" if c["needs_human"] else "no", escape(c["seen"] or ""))
        for c in convos
    )
    qrows = "".join(
        "<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (escape(q["reference"]), escape(q["phone"]), escape(q["name"]),
           escape(q["service"]), escape(q["description"] or "")[:80],
           escape(q["created_at"] or ""))
        for q in quotes
    )
    return (
        "<!doctype html><html><head><meta charset=utf-8><meta name=viewport "
        "content='width=device-width,initial-scale=1'>"
        "<title>UX Bridge WhatsApp Agent — Admin</title>"
        "<style>body{font-family:system-ui;padding:16px}table{border-collapse:collapse;"
        "width:100%;margin-bottom:32px}td,th{border:1px solid #ccc;padding:6px 8px;"
        "font-size:13px}th{background:#0b5fa5;color:#fff}</style></head><body>"
        "<h2>UX Bridge WhatsApp Agent — Admin</h2>"
        "<p><b>Note:</b> this page is currently open. Protect it (password or "
        "IP allow-list) before pointing real traffic here.</p>"
        "<h3>Conversations</h3>"
        "<table><tr><th>Phone</th><th>Name</th><th>Quote state</th>"
        "<th>Needs human</th><th>Last seen</th></tr>" + rows + "</table>"
        "<h3>Quote requests</h3>"
        "<table><tr><th>Ref</th><th>Phone</th><th>Name</th><th>Service</th>"
        "<th>Details</th><th>Created</th></tr>" + qrows + "</table>"
        "</body></html>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
