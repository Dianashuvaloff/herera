import base64
import io
import json
import logging
import re

import anthropic
from PIL import Image, ImageEnhance, ImageFilter

from config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------

PROFILE_SYSTEM = (
    "You are an expert OCR system for handwritten Ukrainian guest cards from HER ERA events. "
    "You read cursive Ukrainian handwriting with high accuracy. "
    "Return ONLY valid JSON — no explanations, no markdown fences."
)

PROFILE_PROMPT = """Розпізнай заповнений бланк гості вечора HER ERA.

СТРУКТУРА БЛАНКУ (картка повернута на 90° — текст йде зверху вниз):
Картка містить ТОЧНО такі поля у фіксованому порядку:

1. № ___  (номер гості, цифра 1-24)
2. Ім'я ___  (ім'я, кирилиця)
3. Вік: ___  (число)
4. Чим займаюсь: ___  (професія/робота)
5. Хобі: ___  (захоплення)
6. Моя краща риса: ___
7. Моя найгірша риса: ___
8. Я шукаю: (чекбокси — відмічені галочкою ✓ або будь-якою позначкою)
   □ подругу
   □ нові знайомства в Києві
   □ нещодавно переїхала / MATCH
   □ колаборацію / знімати контент разом
   □ партнера по роботі / бізнесу
   □ романтичні стосунки
   □ Tinder-вечір
   □ свій варіант (може бути текст поруч)

ПРАВИЛА РОЗПІЗНАВАННЯ:
- Текст написаний від руки українською (іноді — російською, суржиком)
- Якщо поле порожнє або не заповнене — поверни null
- Якщо почерк нечіткий — опиши які літери бачиш у полі "raw_chars", НЕ вгадуй
- Для чекбоксів: будь-яка позначка (✓, ✗, галочка, крестик, лінія) = true
- Чекбокс без позначки = false

Поверни JSON:
{
  "number": <int 1-24 або null>,
  "name": "<ім'я або null>",
  "name_confidence": "<high/medium/low>",
  "age": "<число або null>",
  "occupation": "<текст або null>",
  "occupation_confidence": "<high/medium/low>",
  "hobbies": "<текст або null>",
  "best_trait": "<текст або null>",
  "worst_trait": "<текст або null>",
  "seeking": {
    "подругу": <true/false>,
    "знайомства": <true/false>,
    "переїхала_match": <true/false>,
    "колаборацію": <true/false>,
    "бізнес": <true/false>,
    "романтика": <true/false>,
    "tinder": <true/false>
  },
  "seeking_custom": "<текст або null>",
  "unclear_fields": [
    {"field": "<назва поля>", "raw_chars": "<що бачу>", "possible_readings": ["варіант1", "варіант2", "варіант3"]}
  ]
}

Поле "unclear_fields" — масив полів де почерк нечіткий. Для кожного нечіткого поля дай 3 можливих варіанти прочитання.
Якщо всі поля чіткі — "unclear_fields": []
"""

MATCH_GRID_SYSTEM = (
    "You are an expert OCR system reading a match grid from a HER ERA event card. "
    "The grid contains handwritten single letters in numbered cells. "
    "Return ONLY valid JSON — no explanations, no markdown fences."
)

MATCH_GRID_PROMPT = """Розпізнай матч-сітку з бланку гості вечора HER ERA.

СТРУКТУРА СІТКИ:
Таблиця 4 колонки × 6 рядків = 24 пронумерованих слоти.
Розташування (зліва направо, зверху вниз):

| 19 | 13 | 7  | 1 |
| 20 | 14 | 8  | 2 |
| 21 | 15 | 9  | 3 |
| 22 | 16 | 10 | 4 |
| 23 | 17 | 11 | 5 |
| 24 | 18 | 12 | 6 |

МОЖЛИВІ КОДИ (написані від руки в клітинці):
- П = подруга
- К = колаборація
- Б = бізнес
- + = хочу більше спілкуватись
- ? = свій варіант
- ПОРОЖНЬО = нічого

ПРАВИЛА:
- Кожна клітинка містить ОДНУ літеру або порожня
- Увага: "П" і "Б" схожі у рукописному — П має верхню горизонтальну лінію, Б має нижню петлю
- Увага: "К" може виглядати як "Н" — перевіряй що це саме К (дозволені тільки П/К/Б/+/?)
- Якщо в клітинці щось написано але незрозуміло — поверни "?" і додай в unclear
- Порожня клітинка = null

Поверни JSON:
{
  "slots": {
    "1": "<П|К|Б|+|?|null>",
    "2": "<П|К|Б|+|?|null>",
    "3": "<П|К|Б|+|?|null>",
    "4": "<П|К|Б|+|?|null>",
    "5": "<П|К|Б|+|?|null>",
    "6": "<П|К|Б|+|?|null>",
    "7": "<П|К|Б|+|?|null>",
    "8": "<П|К|Б|+|?|null>",
    "9": "<П|К|Б|+|?|null>",
    "10": "<П|К|Б|+|?|null>",
    "11": "<П|К|Б|+|?|null>",
    "12": "<П|К|Б|+|?|null>",
    "13": "<П|К|Б|+|?|null>",
    "14": "<П|К|Б|+|?|null>",
    "15": "<П|К|Б|+|?|null>",
    "16": "<П|К|Б|+|?|null>",
    "17": "<П|К|Б|+|?|null>",
    "18": "<П|К|Б|+|?|null>",
    "19": "<П|К|Б|+|?|null>",
    "20": "<П|К|Б|+|?|null>",
    "21": "<П|К|Б|+|?|null>",
    "22": "<П|К|Б|+|?|null>",
    "23": "<П|К|Б|+|?|null>",
    "24": "<П|К|Б|+|?|null>"
  },
  "unclear_slots": [
    {"slot": <number>, "raw_chars": "<що бачу>", "possible_codes": ["П", "Б"]}
  ]
}
"""

# ---------------------------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------------------------

def preprocess_image(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Ensure minimum resolution (upscale if needed)
    min_side = min(img.size)
    if min_side < 1200:
        scale = 1200 / min_side
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Convert to grayscale for enhancement
    gray = img.convert("L")

    # CLAHE-like contrast enhancement via adaptive histogram
    # Pillow doesn't have CLAHE, so we use autocontrast + sharpening
    from PIL import ImageOps
    gray = ImageOps.autocontrast(gray, cutoff=1)

    # Sharpen to make handwriting edges clearer
    gray = gray.filter(ImageFilter.SHARPEN)

    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(1.5)

    # Back to RGB (Claude handles both, but consistency)
    result = gray.convert("RGB")

    buf = io.BytesIO()
    result.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def _get_client():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


async def _call_claude(image_bytes: bytes, system: str, prompt: str,
                       media_type: str = "image/png") -> dict:
    client = _get_client()
    b64 = base64.b64encode(image_bytes).decode()

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )

    return _extract_json(response.content[0].text)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_CYRILLIC_RE = re.compile(r"^[\sА-Яа-яЄєІіЇїҐґЬьʼ'\-]+$")
VALID_MATCH_CODES = {"П", "К", "Б", "+", "?"}


def validate_profile(data: dict) -> dict:
    errors = []

    # Age: 18-60
    age = data.get("age")
    if age is not None:
        try:
            age_int = int(str(age).strip())
            if not 16 <= age_int <= 65:
                errors.append(f"Вік {age_int} поза межами 16-65")
                data["age"] = None
            else:
                data["age"] = str(age_int)
        except (ValueError, TypeError):
            errors.append(f"Вік '{age}' — не число")
            data["age"] = None

    # Name: cyrillic only
    name = data.get("name")
    if name and not _CYRILLIC_RE.match(name.strip()):
        errors.append(f"Ім'я '{name}' містить не-кириличні символи")
        if data.get("name_confidence") != "high":
            data.setdefault("unclear_fields", []).append({
                "field": "name",
                "raw_chars": name,
                "possible_readings": [name],
            })

    # Number: 1-24
    number = data.get("number")
    if number is not None:
        try:
            num = int(number)
            if not 1 <= num <= 24:
                errors.append(f"Номер {num} поза межами 1-24")
                data["number"] = None
            else:
                data["number"] = num
        except (ValueError, TypeError):
            errors.append(f"Номер '{number}' — не число")
            data["number"] = None

    data["_validation_errors"] = errors
    return data


def validate_match_grid(data: dict) -> dict:
    errors = []
    slots = data.get("slots", {})
    cleaned = {}

    for i in range(1, 25):
        val = slots.get(str(i))
        if val is None or val == "null" or val == "":
            cleaned[str(i)] = None
        elif val in VALID_MATCH_CODES:
            cleaned[str(i)] = val
        else:
            errors.append(f"Слот {i}: невідомий код '{val}'")
            cleaned[str(i)] = "?"
            data.setdefault("unclear_slots", []).append({
                "slot": i, "raw_chars": val, "possible_codes": list(VALID_MATCH_CODES),
            })

    data["slots"] = cleaned
    data["_validation_errors"] = errors
    return data


# ---------------------------------------------------------------------------
# Second pass — re-read unclear fields with zoomed crops
# ---------------------------------------------------------------------------

REREAD_PROMPT_TEMPLATE = """Уважно прочитай цей фрагмент рукописного тексту з бланку гості HER ERA.

Це поле "{field_label}" з картки гості.
На першому проході я прочитав: "{first_reading}"
Впевненість: {confidence}

Прочитай ще раз дуже уважно. Текст написаний від руки українською.
Дай 3 можливих варіанти прочитання від найбільш до найменш ймовірного.

Поверни JSON:
{{
  "best_reading": "<найбільш ймовірне>",
  "alternatives": ["<варіант 2>", "<варіант 3>"],
  "confidence": "<high/medium/low>"
}}
"""


async def _reread_unclear_fields(image_bytes: bytes, profile: dict) -> dict:
    unclear = profile.get("unclear_fields", [])
    if not unclear:
        return profile

    low_confidence_fields = []
    for field_name in ("name", "occupation", "hobbies", "best_trait", "worst_trait"):
        conf_key = f"{field_name}_confidence"
        if profile.get(conf_key) == "low":
            low_confidence_fields.append(field_name)

    fields_to_reread = [f["field"] for f in unclear] + low_confidence_fields
    fields_to_reread = list(set(fields_to_reread))

    if not fields_to_reread:
        return profile

    field_labels = {
        "name": "Ім'я",
        "age": "Вік",
        "occupation": "Чим займаюсь",
        "hobbies": "Хобі",
        "best_trait": "Моя краща риса",
        "worst_trait": "Моя найгірша риса",
    }

    # Send the full image again with a focused prompt for unclear fields
    fields_desc = "\n".join(
        f"- {field_labels.get(f, f)}: прочитано як \"{profile.get(f, '?')}\""
        for f in fields_to_reread
    )

    reread_prompt = f"""Повторне читання нечітких полів бланку HER ERA.

Ці поля були прочитані з низькою впевненістю:
{fields_desc}

Прочитай ці поля ще раз ДУЖЕ уважно. Зверни увагу на:
- Українські літери що схожі: и/н, т/г, ш/щ, з/е, р/д
- Вертикальні штрихи — порахуй їх точно
- Петлі та хвостики літер

Поверни JSON з виправленими значеннями:
{{
  {', '.join(f'"{f}": "<виправлене значення або null>"' for f in fields_to_reread)}
}}
"""

    try:
        result = await _call_claude(image_bytes, PROFILE_SYSTEM, reread_prompt)
        for field in fields_to_reread:
            if field in result and result[field]:
                profile[field] = result[field]
                log.info("Reread %s: %s → %s", field, profile.get(field), result[field])
    except Exception as e:
        log.warning("Reread failed: %s", e)

    return profile


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def recognize_profile(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    processed = preprocess_image(image_bytes)

    # Pass 1: full recognition
    profile = await _call_claude(processed, PROFILE_SYSTEM, PROFILE_PROMPT)

    # Validate
    profile = validate_profile(profile)

    # Pass 2: re-read unclear fields
    has_unclear = bool(profile.get("unclear_fields"))
    has_low_conf = any(
        profile.get(f"{f}_confidence") == "low"
        for f in ("name", "occupation", "hobbies", "best_trait", "worst_trait")
    )
    if has_unclear or has_low_conf:
        log.info("Running second pass for unclear fields...")
        profile = await _reread_unclear_fields(processed, profile)
        profile = validate_profile(profile)

    return profile


async def recognize_match_grid(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    processed = preprocess_image(image_bytes)

    # Pass 1: full recognition
    grid = await _call_claude(processed, MATCH_GRID_SYSTEM, MATCH_GRID_PROMPT)

    # Validate
    grid = validate_match_grid(grid)

    # Pass 2: re-read unclear slots
    unclear_slots = grid.get("unclear_slots", [])
    if unclear_slots:
        log.info("Running second pass for %d unclear slots...", len(unclear_slots))
        slot_desc = ", ".join(f"слот {s['slot']}: бачу '{s['raw_chars']}'" for s in unclear_slots)
        reread_prompt = f"""Повторне читання нечітких слотів матч-сітки HER ERA.

Нечіткі слоти: {slot_desc}

Дозволені коди: П (подруга), К (колаборація), Б (бізнес), + (хочу спілкуватись), ? (свій варіант).

Увага на відмінності:
- П має верхню горизонтальну планку
- Б має нижню петлю/закруглення
- К має діагональні лінії від вертикальної
- + це просто хрестик

Прочитай ці слоти ще раз. Поверни JSON:
{{
  {', '.join(f'"{s["slot"]}": "<П|К|Б|+|?|null>"' for s in unclear_slots)}
}}
"""
        try:
            result = await _call_claude(processed, MATCH_GRID_SYSTEM, reread_prompt)
            for s in unclear_slots:
                slot_key = str(s["slot"])
                if slot_key in result:
                    val = result[slot_key]
                    if val in VALID_MATCH_CODES:
                        grid["slots"][slot_key] = val
                        log.info("Reread slot %s: %s → %s", slot_key, s["raw_chars"], val)
        except Exception as e:
            log.warning("Match grid reread failed: %s", e)

        grid = validate_match_grid(grid)

    return grid
