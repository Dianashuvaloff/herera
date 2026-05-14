import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8563723668:AAH5ZLKufXqNdVJXAEpQLxBGGvjLLpNL2Po")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "959203791"))

SPREADSHEET_ID = "1-wE2i0gLv_tgMjRaW_i1Y99QYMMA1b3Cbf8wIdRuE8Q"
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "her-era-crm-d1b87ac0d0c9.json")

POINTS = {
    "event_visit": 50,
    "referral_new": 100,
    "referral_repeat": 30,
    "story_mention": 30,
    "review": 20,
    "birthday": 200,
    "used_refcode": 50,
}

STATUSES = [
    (0, "Гостя"),
    (500, "Постійна"),
    (2000, "VIP"),
]

FREE_TICKET_COST = 1000
REFCODE_DISCOUNT_PCT = 10
REFCODE_BONUS = 100

MONO_TOKEN = os.getenv("MONO_TOKEN", "m3gHPtB1EvmRdtC2xUHPu7g")
API_PORT = int(os.getenv("API_PORT", "8085"))
API_BASE_URL = os.getenv("API_BASE_URL", "https://herera.demo.autopilot-smm.info")
