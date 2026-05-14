import json
import os
import random
import string
from datetime import datetime
from pathlib import Path

import gspread

from config import CREDENTIALS_FILE, FREE_TICKET_COST, SPREADSHEET_ID, STATUSES

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


def get_status_label(total_points: float) -> str:
    label = STATUSES[0][1]
    for threshold, name in STATUSES:
        if total_points >= threshold:
            label = name
    return label


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


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "380" + digits[1:]
    if digits.startswith("80") and len(digits) == 11:
        digits = "3" + digits
    return digits


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


def update_phone(row: int, phone: str):
    data = ws_girls.row_values(1)
    col = data.index("Телефон") + 1 if "Телефон" in data else None
    if col:
        ws_girls.update_cell(row, col, _normalize_phone(phone))


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
        "100",
        "",
        "0",
        "",
        "Активний",
        now,
        "",
    ], value_input_option="USER_ENTERED")

    return {"id": next_id, "name": full_name, "refcode": refcode}


def update_chat_id(row: int, chat_id: str):
    data = ws_girls.row_values(1)
    col = data.index("Telegram chat id") + 1 if "Telegram chat id" in data else None
    if col:
        ws_girls.update_cell(row, col, str(chat_id))


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
