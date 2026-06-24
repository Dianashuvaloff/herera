import json
import logging
import os
import random
import string
from datetime import datetime
from pathlib import Path

import gspread

from config import CREDENTIALS_FILE, FREE_TICKET_COST, SPREADSHEET_ID, STATUSES

log = logging.getLogger(__name__)

_creds_env = os.getenv("GOOGLE_CREDENTIALS_JSON")
if _creds_env:
    creds_dict = json.loads(_creds_env)
    gc = gspread.service_account_from_dict(creds_dict)
else:
    _creds_path = Path(__file__).parent / CREDENTIALS_FILE
    if not _creds_path.exists():
        _creds_path = Path(__file__).parent.parent / CREDENTIALS_FILE
    gc = gspread.service_account(filename=str(_creds_path))

sh = gc.open_by_key(SPREADSHEET_ID)

ws_girls = sh.worksheet("Дівчата")
ws_bookings = sh.worksheet("Бронювання")
ws_points = sh.worksheet("Бали історія")
ws_codes = sh.worksheet("Коди")
ws_events = sh.worksheet("Івенти")

# New Phase 2 sheets — created lazily
_ws_matches = None
_ws_broadcasts = None


def _get_or_create_sheet(name: str, headers: list[str]):
    try:
        ws = sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")
        log.info("Created sheet: %s", name)
    return ws


def get_ws_matches():
    global _ws_matches
    if _ws_matches is None:
        _ws_matches = _get_or_create_sheet("Матч-бланки", [
            "ID запису", "ID дівчини", "Імʼя", "Назва івенту", "Дата івенту",
            "Номер на бланку",
            "Слот 1", "Слот 2", "Слот 3", "Слот 4", "Слот 5", "Слот 6",
            "Слот 7", "Слот 8", "Слот 9", "Слот 10", "Слот 11", "Слот 12",
            "Слот 13", "Слот 14", "Слот 15", "Слот 16", "Слот 17", "Слот 18",
            "Слот 19", "Слот 20", "Слот 21", "Слот 22", "Слот 23", "Слот 24",
            "Дата запису",
        ])
    return _ws_matches


def get_ws_broadcasts():
    global _ws_broadcasts
    if _ws_broadcasts is None:
        _ws_broadcasts = _get_or_create_sheet("Розсилки", [
            "ID розсилки", "Дата", "Тип", "Івент", "Текст",
            "Кількість отримувачів", "Статус",
        ])
    return _ws_broadcasts


# --- Helpers ---

def _transliterate(name: str) -> str:
    table = {
        "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d",
        "е": "e", "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i",
        "ї": "yi", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ь": "", "ю": "yu", "я": "ya", "ы": "y", "э": "e",
    }
    result = ""
    for ch in name.lower():
        result += table.get(ch, ch)
    return result


def _generate_refcode(name: str) -> str:
    trans = _transliterate(name).upper()
    prefix = trans[:6].replace(" ", "")
    if len(prefix) < 3:
        prefix = prefix.ljust(3, "X")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{suffix}"


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "380" + digits[1:]
    if digits.startswith("80") and len(digits) == 11:
        digits = "3" + digits
    return digits


def get_status_label(total_points: float) -> str:
    label = STATUSES[0][1]
    for threshold, name in STATUSES:
        if total_points >= threshold:
            label = name
    return label


def get_next_status_info(total_points: float) -> dict | None:
    for threshold, name in STATUSES:
        if total_points < threshold:
            return {"status": name, "threshold": threshold, "points_left": threshold - total_points}
    return None


# --- Girls CRUD ---

def find_girl_by_chat_id(chat_id: str) -> dict | None:
    data = ws_girls.get_all_values()
    headers = data[0]
    chat_col = headers.index("Telegram chat id") if "Telegram chat id" in headers else None
    if chat_col is None:
        return None
    for i, row in enumerate(data[1:], start=2):
        if len(row) > chat_col and str(row[chat_col]) == str(chat_id):
            return {"row": i, "data": dict(zip(headers, row))}
    return None


def find_girl_by_username(username: str) -> dict | None:
    data = ws_girls.get_all_values()
    headers = data[0]
    tg_col = headers.index("Telegram username") if "Telegram username" in headers else None
    if tg_col is None:
        return None
    for i, row in enumerate(data[1:], start=2):
        if len(row) > tg_col and row[tg_col].lower().strip("@") == username.lower().strip("@"):
            return {"row": i, "data": dict(zip(headers, row))}
    return None


def find_girl_by_phone(phone: str) -> dict | None:
    normalized = _normalize_phone(phone)
    if len(normalized) < 10:
        return None
    data = ws_girls.get_all_values()
    headers = data[0]
    phone_col = headers.index("Телефон") if "Телефон" in headers else None
    if phone_col is None:
        return None
    for i, row in enumerate(data[1:], start=2):
        if len(row) > phone_col:
            row_phone = _normalize_phone(str(row[phone_col]))
            if row_phone and row_phone == normalized:
                return {"row": i, "data": dict(zip(headers, row))}
    return None


def find_girl_by_name(name: str) -> dict | None:
    data = ws_girls.get_all_values()
    headers = data[0]
    name_col = headers.index("Імʼя") if "Імʼя" in headers else None
    if name_col is None:
        return None
    name_lower = name.lower().strip()

    # Exact match
    for i, row in enumerate(data[1:], start=2):
        if len(row) > name_col and row[name_col].lower().strip() == name_lower:
            return {"row": i, "data": dict(zip(headers, row))}

    # Starts-with match (Софія matches Софія Коваленко)
    for i, row in enumerate(data[1:], start=2):
        if len(row) > name_col:
            row_name = row[name_col].lower().strip()
            if row_name.startswith(name_lower) or name_lower.startswith(row_name):
                return {"row": i, "data": dict(zip(headers, row))}

    # Contains match
    for i, row in enumerate(data[1:], start=2):
        if len(row) > name_col:
            row_name = row[name_col].lower().strip()
            if name_lower in row_name or row_name in name_lower:
                return {"row": i, "data": dict(zip(headers, row))}

    return None


def find_girl_by_name_and_event(name: str, event_name: str) -> dict | None:
    return find_girl_by_name(name)


def update_phone(row: int, phone: str):
    data = ws_girls.row_values(1)
    col = data.index("Телефон") + 1 if "Телефон" in data else None
    if col:
        ws_girls.update_cell(row, col, _normalize_phone(phone))


def update_chat_id(row: int, chat_id: str):
    data = ws_girls.row_values(1)
    col = data.index("Telegram chat id") + 1 if "Telegram chat id" in data else None
    if col:
        ws_girls.update_cell(row, col, str(chat_id))


def register_girl(chat_id: str, username: str, full_name: str, phone: str = "") -> dict:
    data = ws_girls.get_all_values()
    headers = data[0]
    next_id = len(data)

    refcode = _generate_refcode(full_name)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_row = [""] * len(headers)
    col = {h: i for i, h in enumerate(headers)}

    new_row[col["ID"]] = str(next_id)
    new_row[col["Дата реєстрації"]] = now
    new_row[col["Імʼя"]] = full_name
    if "Телефон" in col:
        new_row[col["Телефон"]] = phone
    if "Telegram username" in col:
        new_row[col["Telegram username"]] = username
    if "Telegram chat id" in col:
        new_row[col["Telegram chat id"]] = str(chat_id)
    if "Реф код" in col:
        new_row[col["Реф код"]] = refcode
    if "Total балів" in col:
        new_row[col["Total балів"]] = "0"
    if "Available балів" in col:
        new_row[col["Available балів"]] = "0"
    if "Статус дівчини" in col:
        new_row[col["Статус дівчини"]] = "Гостя"

    ws_girls.append_row(new_row, value_input_option="USER_ENTERED")

    ws_codes.append_row([
        refcode,
        "Реферальний (дівчина)",
        f"{full_name} (ID:{next_id})",
        "Знижка %",
        "10",
        "50",
        "",
        "0",
        "",
        "Активний",
        now,
        "",
    ], value_input_option="USER_ENTERED")

    return {"id": next_id, "name": full_name, "refcode": refcode}


def update_girl_profile(row: int, profile_data: dict):
    headers = ws_girls.row_values(1)
    col_map = {h: i + 1 for i, h in enumerate(headers)}
    updates = []
    for field, value in profile_data.items():
        if field in col_map and value is not None:
            updates.append((row, col_map[field], str(value)))
    for r, c, v in updates:
        ws_girls.update_cell(r, c, v)


# --- Balance ---

def get_balance(girl_data: dict) -> dict:
    total = float(girl_data.get("Total балів", 0) or 0)
    available = float(girl_data.get("Available балів", 0) or 0)
    status = get_status_label(total)
    return {
        "total": total,
        "available": available,
        "status": status,
        "until_free": max(0, FREE_TICKET_COST - available),
    }


def get_refcode(girl_data: dict) -> str:
    return girl_data.get("Реф код", "")


def get_referrals(refcode: str) -> list[dict]:
    if not refcode:
        return []
    data = ws_girls.get_all_values()
    headers = data[0]
    ref_col = headers.index("Хто привів") if "Хто привів" in headers else None
    if ref_col is None:
        return []
    referrals = []
    for row in data[1:]:
        if len(row) > ref_col and refcode in str(row[ref_col]):
            name_col = headers.index("Імʼя")
            referrals.append({"name": row[name_col] if len(row) > name_col else "?"})
    return referrals


# --- Events ---

def get_upcoming_events() -> list[dict]:
    data = ws_events.get_all_values()
    headers = data[0]
    events = []
    now = datetime.now()
    for row in data[1:]:
        if not row[0]:
            continue
        d = dict(zip(headers, row))
        try:
            raw_date = d.get("Дата івенту", "")[:10]
            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
            if event_date >= now:
                d["_date"] = event_date
                events.append(d)
        except (ValueError, TypeError):
            continue
    events.sort(key=lambda x: x["_date"])
    return events


def get_events_for_site() -> list[dict]:
    events = get_upcoming_events()
    bookings = ws_bookings.get_all_values()
    b_headers = bookings[0] if bookings else []

    date_col = b_headers.index("Дата івенту") if "Дата івенту" in b_headers else None
    status_col = b_headers.index("Статус оплати") if "Статус оплати" in b_headers else None

    sold_by_date: dict[str, int] = {}
    if date_col is not None:
        for row in bookings[1:]:
            if len(row) <= date_col:
                continue
            b_date = row[date_col].strip()
            if status_col is not None and len(row) > status_col:
                if row[status_col].strip().lower() in ("скасовано", "відмінено", "cancelled"):
                    continue
            sold_by_date[b_date] = sold_by_date.get(b_date, 0) + 1

    result = []
    for ev in events:
        raw_date = ev.get("Дата івенту", "")[:10]
        name = ev.get("Назва івенту", "").strip()
        emoji = ev.get("Емоджі", "").strip() or (name[0] if name else "📅")
        capacity = int(ev.get("Макс місць", "12") or 12)
        desc = ev.get("Опис", "").strip()
        dress_code = ev.get("Дрес-код", "").strip()
        location = ev.get("Локація", "").strip()
        time = ev.get("Час", "").strip()

        try:
            d = ev["_date"]
            weekdays = ["Понеділок", "Вівторок", "Середа", "Четвер", "Пʼятниця", "Субота", "Неділя"]
            date_formatted = f"{d.strftime('%d.%m.%Y')} · {weekdays[d.weekday()]} · {time}"
        except (KeyError, ValueError):
            date_formatted = f"{raw_date} · {time}"

        sold = 0
        for b_date_key, count in sold_by_date.items():
            b_normalized = b_date_key[:10].strip()
            if b_normalized == raw_date or b_normalized == d.strftime("%d.%m.%Y"):
                sold += count

        tags = [f"До {capacity} дівчат"]
        if location:
            tags.append(location)
        if dress_code:
            tags.append(dress_code)

        result.append({
            "name": name,
            "emoji": emoji,
            "date": date_formatted,
            "desc": desc,
            "tags": tags,
            "sold": sold,
            "capacity": capacity,
            "location": location,
        })

    return result


# --- Refcodes ---

def validate_refcode(code: str) -> dict | None:
    data = ws_codes.get_all_values()
    headers = data[0]
    for row in data[1:]:
        if not row[0]:
            continue
        d = dict(zip(headers, row))
        if d.get("Код", "").upper() == code.upper() and d.get("Статус") == "Активний":
            return d
    return None


# --- Bookings ---

def create_booking(
    event_name: str,
    event_date: str,
    location: str,
    name: str,
    phone: str,
    instagram: str = "",
    telegram: str = "",
    base_amount: float = 0,
    refcode: str = "",
    discount: float = 0,
    paid_amount: float = 0,
    payment_type: str = "",
    invoice_id: str = "",
) -> str:
    data = ws_bookings.get_all_values()
    booking_id = f"WEB-{len(data):04d}"

    girl = find_girl_by_phone(phone)
    girl_id = girl["data"].get("ID", "") if girl else ""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = data[0]
    new_row = [""] * len(headers)
    col = {h: i for i, h in enumerate(headers)}

    if "ID бронювання" in col:
        new_row[col["ID бронювання"]] = booking_id
    if "Дата івенту" in col:
        new_row[col["Дата івенту"]] = event_date
    if "Локація" in col:
        new_row[col["Локація"]] = location
    if "ID дівчини" in col:
        new_row[col["ID дівчини"]] = str(girl_id)
    if "Імʼя" in col:
        new_row[col["Імʼя"]] = name
    if "Телефон" in col:
        new_row[col["Телефон"]] = _normalize_phone(phone)
    if "Сума базова" in col:
        new_row[col["Сума базова"]] = str(base_amount)
    if "Реф код" in col:
        new_row[col["Реф код"]] = refcode
    if "Знижка" in col:
        new_row[col["Знижка"]] = str(discount)
    if "Сума оплачена" in col:
        new_row[col["Сума оплачена"]] = str(paid_amount)
    if "Статус оплати" in col:
        new_row[col["Статус оплати"]] = "Очікує оплати"
    if "Прийшла" in col:
        new_row[col["Прийшла"]] = "Ні"
    if "Дата оплати" in col:
        new_row[col["Дата оплати"]] = ""
    if "Коментар" in col:
        new_row[col["Коментар"]] = f"Сайт | {payment_type} | {invoice_id}"

    ws_bookings.append_row(new_row, value_input_option="USER_ENTERED")
    return booking_id


def update_booking_status(invoice_id: str, status: str = "Повна оплата") -> dict | None:
    data = ws_bookings.get_all_values()
    headers = data[0]
    comment_col = headers.index("Коментар") if "Коментар" in headers else None
    status_col = headers.index("Статус оплати") if "Статус оплати" in headers else None
    date_col = headers.index("Дата оплати") if "Дата оплати" in headers else None

    if comment_col is None:
        return None

    for i, row in enumerate(data[1:], start=2):
        if len(row) > comment_col and invoice_id in str(row[comment_col]):
            if status_col:
                ws_bookings.update_cell(i, status_col + 1, status)
            if date_col:
                ws_bookings.update_cell(i, date_col + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return {"row": i, "data": dict(zip(headers, row))}
    return None


def get_bookings_for_event(event_date: str) -> list[dict]:
    data = ws_bookings.get_all_values()
    if len(data) <= 1:
        return []
    headers = data[0]
    date_col = headers.index("Дата івенту") if "Дата івенту" in headers else None
    if date_col is None:
        return []
    results = []
    for row in data[1:]:
        if len(row) > date_col and row[date_col].strip()[:10] == event_date.strip()[:10]:
            results.append(dict(zip(headers, row)))
    return results


def get_girls_with_chat_id() -> list[dict]:
    data = ws_girls.get_all_values()
    headers = data[0]
    chat_col = headers.index("Telegram chat id") if "Telegram chat id" in headers else None
    if chat_col is None:
        return []
    results = []
    for row in data[1:]:
        if len(row) > chat_col and row[chat_col].strip():
            results.append(dict(zip(headers, row)))
    return results


def get_girls_for_event(event_date: str) -> list[dict]:
    bookings = get_bookings_for_event(event_date)
    if not bookings:
        return []
    girls_data = ws_girls.get_all_values()
    headers = girls_data[0]
    id_col = headers.index("ID") if "ID" in headers else None
    chat_col = headers.index("Telegram chat id") if "Telegram chat id" in headers else None
    if id_col is None or chat_col is None:
        return []

    girl_map = {}
    for row in girls_data[1:]:
        if len(row) > max(id_col, chat_col) and row[chat_col].strip():
            girl_map[str(row[id_col])] = dict(zip(headers, row))

    results = []
    for b in bookings:
        girl_id = b.get("ID дівчини", "")
        if girl_id in girl_map:
            results.append({**girl_map[girl_id], "_booking": b})
    return results


# --- Match blanks ---

def write_match_blank(girl_id: str, girl_name: str, event_name: str, event_date: str,
                      blank_number: int, slots: list[str]):
    ws = get_ws_matches()
    data = ws.get_all_values()
    record_id = f"MB-{len(data):04d}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    padded_slots = (slots + [""] * 24)[:24]

    row = [record_id, str(girl_id), girl_name, event_name, event_date,
           str(blank_number)] + padded_slots + [now]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return record_id


def get_match_blanks_for_event(event_name: str) -> list[dict]:
    ws = get_ws_matches()
    data = ws.get_all_values()
    if len(data) <= 1:
        return []
    headers = data[0]
    results = []
    for row in data[1:]:
        d = dict(zip(headers, row))
        if d.get("Назва івенту", "").strip() == event_name.strip():
            results.append(d)
    return results


def get_girl_events_with_blanks(girl_id: str) -> list[str]:
    ws = get_ws_matches()
    data = ws.get_all_values()
    if len(data) <= 1:
        return []
    headers = data[0]
    events = set()
    for row in data[1:]:
        d = dict(zip(headers, row))
        if str(d.get("ID дівчини", "")) == str(girl_id):
            events.add(d.get("Назва івенту", ""))
    return sorted(events)


# --- Broadcasts ---

def log_broadcast(broadcast_type: str, event_name: str, text: str, count: int):
    ws = get_ws_broadcasts()
    data = ws.get_all_values()
    broadcast_id = f"BC-{len(data):04d}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        broadcast_id, now, broadcast_type, event_name, text[:200],
        str(count), "Надіслано",
    ], value_input_option="USER_ENTERED")
    return broadcast_id


# --- Points history ---

def add_points_record(girl_id: str, girl_name: str, action: str, points: int, comment: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_points.append_row([
        now, str(girl_id), girl_name, action, str(points), comment,
    ], value_input_option="USER_ENTERED")


# --- OCR Learning Dictionary ---

_ws_ocr_dict = None


def get_ws_ocr_dict():
    global _ws_ocr_dict
    if _ws_ocr_dict is None:
        _ws_ocr_dict = _get_or_create_sheet("OCR словник", [
            "Поле", "Claude побачив", "Правильний текст", "Кількість",
        ])
    return _ws_ocr_dict


def ocr_learn(field: str, raw_chars: str, correct_text: str):
    ws = get_ws_ocr_dict()
    data = ws.get_all_values()
    raw_norm = raw_chars.strip().lower()
    correct_norm = correct_text.strip()

    for i, row in enumerate(data[1:], start=2):
        if len(row) >= 3 and row[0] == field and row[1].strip().lower() == raw_norm:
            ws.update_cell(i, 3, correct_norm)
            count = int(row[3] or 0) if len(row) > 3 else 0
            ws.update_cell(i, 4, str(count + 1))
            return

    ws.append_row([field, raw_chars.strip(), correct_norm, "1"],
                  value_input_option="USER_ENTERED")


def ocr_lookup(field: str, raw_chars: str) -> str | None:
    ws = get_ws_ocr_dict()
    data = ws.get_all_values()
    if len(data) <= 1:
        return None
    raw_norm = raw_chars.strip().lower()
    for row in data[1:]:
        if len(row) >= 3 and row[0] == field and row[1].strip().lower() == raw_norm:
            return row[2]
    return None


def ocr_find_similar(field: str, raw_chars: str) -> list[str]:
    ws = get_ws_ocr_dict()
    data = ws.get_all_values()
    if len(data) <= 1:
        return []
    results = []
    raw_words = set(raw_chars.strip().lower().split())
    for row in data[1:]:
        if len(row) >= 3 and row[0] == field:
            stored_words = set(row[1].strip().lower().split())
            overlap = len(raw_words & stored_words)
            if overlap >= max(1, len(raw_words) // 2):
                results.append(row[2])
    return results[:3]


def check_story_tag_awarded(girl_id: str, event_name: str) -> bool:
    data = ws_points.get_all_values()
    for row in data[1:]:
        if len(row) >= 6:
            if str(row[1]) == str(girl_id) and "story_tag" in str(row[3]) and event_name in str(row[5]):
                return True
    return False
