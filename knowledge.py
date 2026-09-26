"""Facts about UX BRIDGE IMPORT & EXPORT used by the WhatsApp agent's replies.

Tone: professional, short WhatsApp-style messages (1-3 short texts per reply).
No founder titles. Brand written exactly as: UX BRIDGE IMPORT & EXPORT
"""

BRAND = "UX BRIDGE IMPORT & EXPORT"

SERVICES = [
    "Vehicle import & shipping",
    "Cargo & freight",
    "Construction",
    "Solar energy",
]

CONTACT_NIGERIA = "09066666633"
CONTACT_UK = "+447721503468"
ADDRESS = "Eastern Bypass, Kano, Nigeria"

DHL_TRACK_URL = "https://www.dhl.com"
FISH_LOGISTICS_TRACK_URL = "https://www.fish-logistics.com"

GREETING_TEXT = (
    f"Hello! Welcome to {BRAND}. \U0001f60a\n"
    "How can we help you today?\n\n"
    "Reply with:\n"
    "1 \u2013 Our services\n"
    "2 \u2013 Get a quote\n"
    "3 \u2013 Track a shipment\n"
    "4 \u2013 Contact us"
)

SERVICES_TEXT = (
    "Here are our services:\n"
    "\u2022 Vehicle import & shipping \u2013 we source and ship cars to you\n"
    "\u2022 Cargo & freight \u2013 general goods, container handling\n"
    "\u2022 Construction \u2013 building projects and materials\n"
    "\u2022 Solar energy \u2013 panels, inverters and installations\n\n"
    "Want a quote? Just reply QUOTE."
)

TRACKING_TEXT = (
    "You can track your shipment here:\n"
    f"\U0001f69a DHL: {DHL_TRACK_URL}\n"
    f"\U0001f6a2 Fish Logistics: {FISH_LOGISTICS_TRACK_URL}\n"
    "Enter your tracking number on their site."
)

CONTACT_TEXT = (
    "Reach us anytime:\n"
    f"\U0001f4de Nigeria: {CONTACT_NIGERIA}\n"
    f"\U0001f4de UK: {CONTACT_UK}\n"
    f"\U0001f4cd {ADDRESS}"
)

HUMAN_TEXT = (
    "No problem \u2014 I've flagged your chat and someone from our team "
    "will respond to you here shortly."
)

FALLBACK_TEXT = (
    "Sorry, I didn't quite get that. \U0001f64f\n"
    "Reply with a number:\n"
    "1 \u2013 Our services\n"
    "2 \u2013 Get a quote\n"
    "3 \u2013 Track a shipment\n"
    "4 \u2013 Contact us\n"
    "or type HUMAN to speak to a person."
)
