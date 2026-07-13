import logging
import httpx
import anthropic

from config import ANTHROPIC_API_KEY, MANYCHAT_API_KEY, ADMIN_CHAT_ID
from sheets import get_upcoming_events

log = logging.getLogger(__name__)

MANYCHAT_API = "https://api.manychat.com/fb"

SYSTEM_PROMPT = """\
Ти — менеджер жіночого клубу HER ERA (Київ). Спілкуєшся в Instagram Direct з дівчатами, які цікавляться нашими подіями.

ПРАВИЛА:
- Мова: тільки українська, жива, без канцеляризмів
- Тон: тепла подруга, не бот і не менеджер з продажу
- Використовуй ♡ замість емодзі сердечок, мінімум емодзі загалом
- Не пиши більше 3-4 коротких абзаців за раз
- Завжди відповідай по суті — якщо питають ціну, називай ціну
- Ніколи не вигадуй інформацію, якої немає в контексті

ЦІНИ ТА ЗНИЖКИ:
- Якщо йде з подругою — обом -10%
- Реферальний код (HER_ІМ'Я) — знижка 10%
- Блогерський промокод — знижка 15%
- Безкоштовний вхід — не можемо, але можемо запропонувати знижку 30%
- Інших знижок НЕМАЄ. Якщо просять — вежливо відмов і розкажи про програму лояльності

ПРОГРАМА ЛОЯЛЬНОСТІ:
- +100 балів за відвідування
- +50 за запрошену подругу (обом)
- +25 за відмітку в сторіс
- 500 балів → HER ERA Girl (статус)
- 1000 балів → ERA Regular (знижка 200 грн)
- 2000 балів → ERA VIP (безкоштовний вхід раз на сезон)

БРОНЮВАННЯ:
- По передоплаті 1000 грн
- За 7 днів — повернення 100%
- За 5 днів — повернення 50%
- За 2 дні і менше — переноситься на наступну подію

ФОРМАТ ПОДІЙ:
- Speed dating для дівчат: спілкуєшся по колу з кожною
- Бланк: відмічаєш з ким хотілось би продовжити (бізнес, дружба, подорожі, спільні ідеї)
- Фотограф, особистий час для кожної, атмосферна локація, бранч
- До 20 дівчат на вечір

ЗАПЕРЕЧЕННЯ:
- «Дорого» → в ціну входить все (фотосесія, реквізит, локація, бранч, знайомства). Як вечір у барі, але з профі-фото і новими знайомствами
- «Подумаю» → тримаю бронь по поточній ціні максимум до завтра 18:00, далі ціна зросте
- «Небезпечно/незнайомі» → локація перевірена, фотограф весь вечір, все прозоро і камерно
- «Не знайду компанію» → формат побудований так що спілкуєшся з кожною, не будеш сама

ЕСКАЛАЦІЯ — передай діалог живому менеджеру якщо:
- Жалоба на ивент/обслуговування
- Запит на повернення грошей
- Спір по балах
- Будь-що пов'язане з оплатою напряму (крім звичайної покупки)
- Не зрозуміла запит після 2 спроб уточнити

СПІВПРАЦЯ З БЛОГЕРАМИ:
- Попроси статистику за останній місяць (охоплення, залученість)
- Скільки % дівчат/жінок з Києва серед підписників

Якщо не відповідає:
- Через кілька годин: «Не хочу щоб через зайняту голову ти пропустила вечір ♡»
- Через день: «Місце ще тримаю, але довго не зможу»
- Через 2-3 дні: «Розумію що можливо не на часі ♡ Місце передам, але напишу перед наступною подією»

ПОТОЧНІ ПОДІЇ:
{events_context}

Посилання на бронювання: https://www.herera.com/booking
"""


def _build_events_context() -> str:
    try:
        events = get_upcoming_events()
        if not events:
            return "Наразі немає запланованих подій."
        lines = []
        for ev in events[:3]:
            name = ev.get("Назва івенту", "")
            date = ev.get("Дата івенту", "")[:10]
            location = ev.get("Локація", "")
            price = ev.get("Ціна", "")
            dress = ev.get("Дрес-код", "")
            line = f"- {name}, {date}"
            if location:
                line += f", {location}"
            if price:
                line += f", ціна {price} грн"
            if dress:
                line += f", дрес-код: {dress}"
            lines.append(line)
        return "\n".join(lines)
    except Exception as e:
        log.error("Error building events context: %s", e)
        return "Помилка завантаження подій."


async def process_dm(subscriber_id: str, message_text: str, user_name: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY not set")
        return ""

    events_context = _build_events_context()
    system = SYSTEM_PROMPT.format(events_context=events_context)

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system,
            messages=[
                {"role": "user", "content": f"[Дівчина {user_name or 'без імені'} пише в Instagram Direct]\n\n{message_text}"}
            ],
        )
        return response.content[0].text
    except Exception as e:
        log.error("Claude API error in DM: %s", e)
        return ""


async def send_manychat_message(subscriber_id: str, text: str) -> bool:
    if not MANYCHAT_API_KEY:
        log.error("MANYCHAT_API_KEY not set")
        return False

    url = f"{MANYCHAT_API}/sending/sendContent"
    headers = {
        "Authorization": f"Bearer {MANYCHAT_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "subscriber_id": int(subscriber_id),
        "data": {
            "version": "v2",
            "content": {
                "type": "instagram",
                "messages": [
                    {"type": "text", "text": text}
                ],
            },
        },
        "message_tag": "HUMAN_AGENT",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return True
            log.error("ManyChat send error %s: %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            log.error("ManyChat send exception: %s", e)
            return False


async def escalate_to_admin(subscriber_id: str, user_name: str, message_text: str, bot=None):
    if not bot:
        return
    text = (
        f"🔴 <b>Ескалація з Instagram DM</b>\n\n"
        f"👤 {user_name}\n"
        f"💬 {message_text[:500]}\n\n"
        f"ID: {subscriber_id}"
    )
    try:
        await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error("Escalation error: %s", e)
