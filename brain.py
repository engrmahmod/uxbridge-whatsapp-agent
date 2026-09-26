"""Responder for the UX Bridge WhatsApp agent.

No LLM calls — pure keyword/intent matching so the agent stays free and keyless.
get_reply(phone, profile_name, text, state) -> (reply_texts, new_state, actions)

states: None | "awaiting_name" | "awaiting_service" | "awaiting_description"
actions: dict, may contain {"needs_human": True}
"""

import random

import knowledge as K


# ---------- intent detection ----------

def _has(text, *keywords):
    return any(k in text for k in keywords)


def detect_intent(text):
    t = text.lower().strip()
    if t in {"1", "services"}:
        return "services"
    if t in {"2", "quote"}:
        return "quote"
    if t in {"3", "track", "tracking"}:
        return "tracking"
    if t in {"4", "contact"}:
        return "contact"
    if _has(t, "human", "agent please", "speak to", "talk to", "real person",
            "somebody", "someone", "call me"):
        return "human"
    if _has(t, "track", "tracking", "dhl", "fish logistics", "shipment",
            "parcel", "where is my"):
        return "tracking"
    if _has(t, "quote", "quotation", "price", "cost", "how much", "rate",
            "charge", "estimate"):
        return "quote"
    if _has(t, "vehicle", "car", "cars", "ship", "shipping", "import",
            "auto", "clearing"):
        return "vehicle"
    if _has(t, "cargo", "freight", "goods", "container", "haulage"):
        return "cargo"
    if _has(t, "construction", "building", "build", "renovat"):
        return "construction"
    if _has(t, "solar", "panel", "inverter", "battery", "light"):
        return "solar"
    if _has(t, "service", "what do you do", "what do you offer", "offer"):
        return "services"
    if _has(t, "contact", "address", "phone", "number", "whatsapp",
            "location", "where are you", "office"):
        return "contact"
    if _has(t, "hello", "hi", "hey", "good morning", "good afternoon",
            "good evening", "salam", "assalam"):
        return "greeting"
    return "fallback"


# ---------- quote flow ----------

SERVICE_ALIASES = {
    "vehicle": "Vehicle import & shipping",
    "car": "Vehicle import & shipping",
    "shipping": "Vehicle import & shipping",
    "cargo": "Cargo & freight",
    "freight": "Cargo & freight",
    "construction": "Construction",
    "solar": "Solar energy",
}

SERVICE_MENU = (
    "Which service do you need a quote for?\n"
    "1 \u2013 Vehicle import & shipping\n"
    "2 \u2013 Cargo & freight\n"
    "3 \u2013 Construction\n"
    "4 \u2013 Solar energy"
)


def resolve_service(text):
    t = text.lower().strip()
    if t in {"1", "vehicle", "car", "vehicle import & shipping"}:
        return "Vehicle import & shipping"
    if t in {"2", "cargo", "freight", "cargo & freight"}:
        return "Cargo & freight"
    if t in {"3", "construction"}:
        return "Construction"
    if t in {"4", "solar", "solar energy"}:
        return "Solar energy"
    for key, val in SERVICE_ALIASES.items():
        if key in t:
            return val
    return None


def make_reference():
    return "UB-%06d" % random.randint(0, 999999)


def quote_start():
    return (["Great! Let's get you a quote. What's your name?"],
            "awaiting_name")


def quote_step(text, state, state_data):
    """One step of the quote state machine.
    Returns (replies, new_state, quote_record_or_None).
    """
    text = text.strip()
    if text.lower() in {"cancel", "stop", "quit"}:
        return (["No problem \u2014 quote cancelled. Type QUOTE anytime to start again."],
                None, None)

    if state == "awaiting_name":
        state_data["name"] = text[:80]
        return ([f"Thanks {text[:80]}! \U0001f60a", SERVICE_MENU], "awaiting_service", None)

    if state == "awaiting_service":
        service = resolve_service(text)
        if not service:
            return (["Please pick a service by number or name:", SERVICE_MENU],
                    "awaiting_service", None)
        state_data["service"] = service
        return ([f"Got it \u2013 {service}.",
                 "Now tell me briefly what you need "
                 "(e.g. 'Toyota Camry 2019 from UK to Kano')."],
                "awaiting_description", None)

    if state == "awaiting_description":
        if len(text) < 3:
            return (["Please describe what you need so we can quote accurately."],
                    "awaiting_description", None)
        ref = make_reference()
        record = {
            "reference": ref,
            "name": state_data.get("name", ""),
            "service": state_data.get("service", ""),
            "description": text[:500],
        }
        replies = [
            "\u2705 Quote request received!",
            f"Reference: {ref}\n"
            f"Name: {record['name']}\n"
            f"Service: {record['service']}\n"
            f"Details: {record['description']}",
            "Our team will review and send you a price shortly. Thank you!",
        ]
        return (replies, None, record)

    return ([K.FALLBACK_TEXT], None, None)


# ---------- main entry ----------

def get_reply(phone, profile_name, text, state, state_data=None):
    """Return (reply_texts, new_state, actions, quote_record)."""
    state_data = state_data if state_data is not None else {}
    actions = {}

    # cancel works in any quote state
    if state and text.strip().lower() in {"cancel", "stop", "quit"}:
        replies, new_state, _ = quote_step(text, state, state_data)
        return replies, new_state, actions, None

    # mid-quote: continue the flow
    if state in ("awaiting_name", "awaiting_service", "awaiting_description"):
        replies, new_state, record = quote_step(text, state, state_data)
        return replies, new_state, actions, record

    intent = detect_intent(text)

    if intent == "greeting":
        return [K.GREETING_TEXT], None, actions, None
    if intent == "services":
        return [K.SERVICES_TEXT], None, actions, None
    if intent == "vehicle":
        return (["For vehicle import & shipping, we source and ship cars to Nigeria. "
                 "Type QUOTE and we'll prepare your price."],
                None, actions, None)
    if intent == "cargo":
        return (["For cargo & freight, we handle general goods and containers. "
                 "Type QUOTE and we'll prepare your price."],
                None, actions, None)
    if intent == "construction":
        return (["For construction, we take on building projects and materials. "
                 "Type QUOTE and we'll prepare your price."],
                None, actions, None)
    if intent == "solar":
        return (["For solar energy, we supply panels, inverters and installations. "
                 "Type QUOTE and we'll prepare your price."],
                None, actions, None)
    if intent == "tracking":
        return [K.TRACKING_TEXT], None, actions, None
    if intent == "contact":
        return [K.CONTACT_TEXT], None, actions, None
    if intent == "human":
        actions["needs_human"] = True
        return [K.HUMAN_TEXT], None, actions, None
    if intent == "quote":
        replies, new_state = quote_start()
        return replies, new_state, actions, None

    return [K.FALLBACK_TEXT], None, actions, None
