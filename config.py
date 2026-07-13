import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8563723668:AAH5ZLKufXqNdVJXAEpQLxBGGvjLLpNL2Po")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "959203791"))
ADMIN_CHAT_IDS = {ADMIN_CHAT_ID, 723873254}

SPREADSHEET_ID = "1-wE2i0gLv_tgMjRaW_i1Y99QYMMA1b3Cbf8wIdRuE8Q"
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "her-era-crm-d1b87ac0d0c9.json")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MANYCHAT_API_KEY = os.getenv("MANYCHAT_API_KEY", "")

POINTS = {
    "event_visit": 100,
    "referral": 50,
    "story_tag": 25,
    "birthday": 200,
}

STATUSES = [
    (0, "Гостя"),
    (500, "HER ERA Girl"),
    (1000, "ERA Regular"),
    (2000, "ERA VIP"),
]

STATUS_PERKS = {
    "HER ERA Girl": "пріоритетний доступ",
    "ERA Regular": "знижка 200 грн",
    "ERA VIP": "безкоштовний вечір раз на сезон",
}

FREE_TICKET_COST = 1000
REFCODE_DISCOUNT_PCT = 10
REFCODE_BONUS = 50

MONO_TOKEN = os.getenv("MONO_TOKEN", "m3gHPtB1EvmRdtC2xUHPu7g")
API_PORT = int(os.getenv("API_PORT", "8085"))
API_BASE_URL = os.getenv("API_BASE_URL", "https://herera.devroy.net")

DM_LINK = "https://ig.me/m/her.era.kyiv"

REELS_LINKS = {
    "rb event": "https://www.instagram.com/s/aGlnaGxpZ2h0OjE4MDUxNzE4NTkyNzYwMzgz?story_media_id=3898869966547988265&igsh=MWFuZXFicWJmdWM4aw==",
    "401": "https://www.instagram.com/s/aGlnaGxpZ2h0OjE4MDY1MzE0OTQ2MDY4MjM4?story_media_id=3622210105784830389&igsh=ZHA2MzJ6dWVpMXRw",
    "flora hub": "https://www.instagram.com/s/aGlnaGxpZ2h0OjE3OTk4MjU5NTc1NTM0OTg5?story_media_id=3846875109340977559&igsh=MXBod211Y3Fpd3JmNA==",
}


def get_reels_link(location: str) -> str:
    loc = location.lower().strip()
    for key, link in REELS_LINKS.items():
        if key in loc:
            return link
    return ""
