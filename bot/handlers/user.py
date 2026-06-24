import re
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT_ID, ADMIN_CHAT_IDS
from sheets import (
    find_girl_by_chat_id,
    find_girl_by_phone,
    find_girl_by_username,
    get_balance,
    get_refcode,
    get_referrals,
    get_upcoming_events,
    register_girl,
    update_chat_id,
    update_phone,
    ws_bookings,
)
from texts import (
    ADMIN_NEW_REG,
    BALANCE,
    BALANCE_EXTRA_FREE,
    BALANCE_EXTRA_PROGRESS,
    CONTACT,
    EVENTS_EMPTY,
    EVENTS_HEADER,
    EVENTS_ITEM,
    HELP,
    HOWTOVIP,
    INFO,
    MYCARD,
    MYREFS_EMPTY,
    MYREFS_HEADER,
    MYREFS_ITEM,
    NEXT_EVENT_BLOCK,
    NOT_REGISTERED,
    REDEEM_NOT_ENOUGH,
    REDEEM_OK,
    REFCODE,
    SHARECODE,
    SHARECODE_EVENT_LINE,
    SHARECODE_NO_EVENT,
    STATUS_EMOJI,
    WELCOME_BACK,
    WELCOME_NEW,
)

router = Router()

PHONE_PATTERN = re.compile(r"^[\+]?[\d\s\-\(\)]{9,15}$")


def _main_menu_kb(user_id: int = 0):
    rows = [
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            InlineKeyboardButton(text="🖤 Моя картка", callback_data="mycard"),
        ],
        [
            InlineKeyboardButton(text="📅 Вечори", callback_data="events"),
            InlineKeyboardButton(text="🎟 Мій код", callback_data="refcode"),
        ],
        [
            InlineKeyboardButton(text="📨 Запросити подругу", callback_data="sharecode"),
            InlineKeyboardButton(text="👯 Мої подруги", callback_data="myrefs"),
        ],
        [
            InlineKeyboardButton(text="💗 Мої матчі", callback_data="matches"),
            InlineKeyboardButton(text="🏆 Як стати VIP", callback_data="howtovip"),
        ],
        [
            InlineKeyboardButton(text="📩 Контакт", callback_data="contact"),
        ],
    ]
    if user_id in ADMIN_CHAT_IDS:
        rows.append([InlineKeyboardButton(text="🔧 Адмін-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu")],
    ])


def _format_next_event(events: list[dict]) -> str:
    if not events:
        return ""
    ev = events[0]
    name = ev.get("Назва івенту", "")
    emoji = name[0] if name else "📅"
    date_str = ev.get("Дата івенту", "")[:10]
    try:
        d = datetime.strptime(date_str, "%d.%m.%Y")
        days_left = (d - datetime.now()).days
        date_str = d.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        days_left = "?"
    return NEXT_EVENT_BLOCK.format(
        emoji=emoji,
        event_name=name.strip(),
        event_date=date_str,
        event_time=ev.get("Час", ""),
        event_location=ev.get("Локація", ""),
        days_left=days_left,
    )


def _get_girl(message_or_callback) -> dict | None:
    user = message_or_callback.from_user
    girl = find_girl_by_chat_id(str(user.id))
    if not girl and user.username:
        girl = find_girl_by_username(user.username)
        if girl:
            update_chat_id(girl["row"], str(user.id))
    return girl


def _link_girl_by_phone(phone: str, chat_id: str, username: str = "") -> dict | None:
    girl = find_girl_by_phone(phone)
    if girl:
        update_chat_id(girl["row"], chat_id)
    return girl


def _get_events_count(girl_data: dict) -> int:
    data = ws_bookings.get_all_values()
    if len(data) <= 1:
        return 0
    headers = data[0]
    id_col = headers.index("ID дівчини") if "ID дівчини" in headers else None
    came_col = headers.index("Прийшла") if "Прийшла" in headers else None
    if id_col is None:
        return 0
    girl_id = girl_data.get("ID", "")
    count = 0
    for row in data[1:]:
        if len(row) > max(id_col, came_col or 0):
            if str(row[id_col]) == str(girl_id):
                if came_col is None or row[came_col].lower() in ("так", "yes", "true", "✅"):
                    count += 1
    return count


# --- /start ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    girl = _get_girl(message)
    events = get_upcoming_events()
    next_event_text = _format_next_event(events)

    if girl:
        bal = get_balance(girl["data"])
        await message.answer(
            WELCOME_BACK.format(
                name=girl["data"].get("Імʼя", ""),
                available=int(bal["available"]),
                status=bal["status"],
                next_event=next_event_text,
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_main_menu_kb(message.from_user.id),
        )
        return

    name = message.from_user.full_name
    username = message.from_user.username or ""
    result = register_girl(
        chat_id=str(message.from_user.id),
        username=username,
        full_name=name,
    )

    await message.answer(
        WELCOME_NEW.format(
            name=name,
            refcode=result["refcode"],
            next_event=next_event_text,
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=_main_menu_kb(message.from_user.id),
    )

    bot = message.bot
    await bot.send_message(
        ADMIN_CHAT_ID,
        ADMIN_NEW_REG.format(name=name, username=username, refcode=result["refcode"]),
        parse_mode=ParseMode.HTML,
    )


# --- Callback handlers ---

@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    events = get_upcoming_events()
    next_event_text = _format_next_event(events)
    bal = get_balance(girl["data"])
    await callback.message.edit_text(
        WELCOME_BACK.format(
            name=girl["data"].get("Імʼя", ""),
            available=int(bal["available"]),
            status=bal["status"],
            next_event=next_event_text,
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=_main_menu_kb(callback.from_user.id),
    )


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    bal = get_balance(girl["data"])
    extra = BALANCE_EXTRA_FREE if bal["available"] >= 1000 else BALANCE_EXTRA_PROGRESS.format(until_free=int(bal["until_free"]))
    await callback.message.edit_text(
        BALANCE.format(total=int(bal["total"]), available=int(bal["available"]), status=bal["status"], extra=extra),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_kb(),
    )


@router.callback_query(F.data == "mycard")
async def cb_mycard(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return

    d = girl["data"]
    bal = get_balance(d)
    code = get_refcode(d)
    refs = get_referrals(code)
    events_count = _get_events_count(d)
    status = bal["status"]
    member_since = d.get("Дата реєстрації", "")[:10]

    await callback.message.edit_text(
        MYCARD.format(
            name=d.get("Імʼя", ""),
            status_emoji=STATUS_EMOJI.get(status, "🤍"),
            status=status,
            total=int(bal["total"]),
            events_count=events_count,
            member_since=member_since,
            refcode=code,
            refs_count=len(refs),
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_kb(),
    )


@router.callback_query(F.data == "events")
async def cb_events(callback: CallbackQuery):
    await callback.answer()
    events = get_upcoming_events()
    if not events:
        await callback.message.edit_text(EVENTS_EMPTY, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        return

    text = EVENTS_HEADER
    for ev in events:
        name = ev.get("Назва івенту", "")
        emoji = name[0] if name else "📅"
        date_str = ev.get("Дата івенту", "")[:10]
        try:
            d = datetime.strptime(date_str, "%d.%m.%Y")
            date_str = d.strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            pass
        text += EVENTS_ITEM.format(
            emoji=emoji, name=name.strip(), date=date_str,
            time=ev.get("Час", ""), location=ev.get("Локація", ""),
            max_spots=ev.get("Макс місць", ""),
        )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.callback_query(F.data == "refcode")
async def cb_refcode(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    code = get_refcode(girl["data"])
    await callback.message.edit_text(
        REFCODE.format(refcode=code),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 Запросити подругу", callback_data="sharecode")],
            [InlineKeyboardButton(text="◀️ Меню", callback_data="menu")],
        ]),
    )


@router.callback_query(F.data == "sharecode")
async def cb_sharecode(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return

    code = get_refcode(girl["data"])
    events = get_upcoming_events()
    if events:
        ev = events[0]
        name = ev.get("Назва івенту", "").strip()
        date_str = ev.get("Дата івенту", "")[:10]
        location = ev.get("Локація", "")
        next_event_short = SHARECODE_EVENT_LINE.format(name=name, date=date_str, location=location)
    else:
        next_event_short = SHARECODE_NO_EVENT

    await callback.message.answer(
        SHARECODE.format(refcode=code, next_event_short=next_event_short),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "myrefs")
async def cb_myrefs(callback: CallbackQuery):
    await callback.answer()
    girl = _get_girl(callback)
    if not girl:
        await callback.message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return

    code = get_refcode(girl["data"])
    refs = get_referrals(code)
    if not refs:
        await callback.message.edit_text(MYREFS_EMPTY, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        return

    text = MYREFS_HEADER
    for r in refs:
        text += MYREFS_ITEM.format(name=r["name"])
    text += f"\nВсього: {len(refs)} подруг 💗"
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.callback_query(F.data == "howtovip")
async def cb_howtovip(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(HOWTOVIP, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.callback_query(F.data == "contact")
async def cb_contact(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(CONTACT, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


# --- Command handlers (fallback for those who type commands) ---

@router.message(Command("balance"))
async def cmd_balance(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    bal = get_balance(girl["data"])
    extra = BALANCE_EXTRA_FREE if bal["available"] >= 1000 else BALANCE_EXTRA_PROGRESS.format(until_free=int(bal["until_free"]))
    await message.answer(
        BALANCE.format(total=int(bal["total"]), available=int(bal["available"]), status=bal["status"], extra=extra),
        parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
    )


@router.message(Command("mycard"))
async def cmd_mycard(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    d = girl["data"]
    bal = get_balance(d)
    code = get_refcode(d)
    refs = get_referrals(code)
    events_count = _get_events_count(d)
    status = bal["status"]
    member_since = d.get("Дата реєстрації", "")[:10]
    await message.answer(
        MYCARD.format(
            name=d.get("Імʼя", ""), status_emoji=STATUS_EMOJI.get(status, "🤍"),
            status=status, total=int(bal["total"]), events_count=events_count,
            member_since=member_since, refcode=code, refs_count=len(refs),
        ),
        parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
    )


@router.message(Command("refcode"))
async def cmd_refcode(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    code = get_refcode(girl["data"])
    await message.answer(REFCODE.format(refcode=code), parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("sharecode"))
async def cmd_sharecode(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    code = get_refcode(girl["data"])
    events = get_upcoming_events()
    if events:
        ev = events[0]
        next_event_short = SHARECODE_EVENT_LINE.format(
            name=ev.get("Назва івенту", "").strip(),
            date=ev.get("Дата івенту", "")[:10],
            location=ev.get("Локація", ""),
        )
    else:
        next_event_short = SHARECODE_NO_EVENT
    await message.answer(SHARECODE.format(refcode=code, next_event_short=next_event_short), parse_mode=ParseMode.HTML)


@router.message(Command("myrefs"))
async def cmd_myrefs(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    code = get_refcode(girl["data"])
    refs = get_referrals(code)
    if not refs:
        await message.answer(MYREFS_EMPTY, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        return
    text = MYREFS_HEADER
    for r in refs:
        text += MYREFS_ITEM.format(name=r["name"])
    text += f"\nВсього: {len(refs)} подруг 💗"
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("events"))
async def cmd_events(message: Message):
    events = get_upcoming_events()
    if not events:
        await message.answer(EVENTS_EMPTY, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        return
    text = EVENTS_HEADER
    for ev in events:
        name = ev.get("Назва івенту", "")
        emoji = name[0] if name else "📅"
        date_str = ev.get("Дата івенту", "")[:10]
        try:
            d = datetime.strptime(date_str, "%d.%m.%Y")
            date_str = d.strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            pass
        text += EVENTS_ITEM.format(
            emoji=emoji, name=name.strip(), date=date_str,
            time=ev.get("Час", ""), location=ev.get("Локація", ""),
            max_spots=ev.get("Макс місць", ""),
        )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("howtovip"))
async def cmd_howtovip(message: Message):
    await message.answer(HOWTOVIP, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("redeem"))
async def cmd_redeem(message: Message):
    girl = _get_girl(message)
    if not girl:
        await message.answer(NOT_REGISTERED, parse_mode=ParseMode.HTML)
        return
    bal = get_balance(girl["data"])
    if bal["available"] < 1000:
        await message.answer(REDEEM_NOT_ENOUGH.format(available=int(bal["available"])), parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        return
    await message.answer(REDEEM_OK, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
    bot = message.bot
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"🎁 <b>Запит на безкоштовний квиток</b>\n\n"
        f"Імʼя: {girl['data'].get('Імʼя', '')}\n"
        f"Available балів: {int(bal['available'])}\n"
        f"Підтвердіть списання 1000 балів у таблиці.",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("info"))
async def cmd_info(message: Message):
    await message.answer(INFO, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("contact"))
async def cmd_contact(message: Message):
    await message.answer(CONTACT, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP, parse_mode=ParseMode.HTML, reply_markup=_back_kb())


@router.message(F.contact)
async def on_contact(message: Message):
    phone = message.contact.phone_number
    chat_id = str(message.from_user.id)
    username = message.from_user.username or ""

    girl = _get_girl(message)
    if not girl:
        girl = _link_girl_by_phone(phone, chat_id, username)

    if girl:
        update_phone(girl["row"], phone)
        bal = get_balance(girl["data"])
        await message.answer(
            f"Дякую! Номер збережено 💗\n\n"
            f"Знайшла тебе — {girl['data'].get('Імʼя', '')}!\n"
            f"💰 {int(bal['available'])} балів · {bal['status']}",
            parse_mode=ParseMode.HTML,
            reply_markup=_main_menu_kb(message.from_user.id),
        )
    else:
        name = message.from_user.full_name
        result = register_girl(chat_id=chat_id, username=username, full_name=name, phone=phone)
        await message.answer(
            WELCOME_NEW.format(
                name=name, refcode=result["refcode"],
                next_event=_format_next_event(get_upcoming_events()),
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_main_menu_kb(message.from_user.id),
        )
        bot = message.bot
        await bot.send_message(
            ADMIN_CHAT_ID,
            ADMIN_NEW_REG.format(name=name, username=username, refcode=result["refcode"]),
            parse_mode=ParseMode.HTML,
        )

    bot = message.bot
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"📱 <b>Контакт отримано</b>\n\n"
        f"Імʼя: {girl['data'].get('Імʼя', '') if girl else message.from_user.full_name}\n"
        f"Телефон: {phone}",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text)
async def on_text_phone(message: Message):
    text = message.text.strip()
    if not PHONE_PATTERN.match(text):
        return

    chat_id = str(message.from_user.id)
    girl = _get_girl(message)

    if girl:
        update_phone(girl["row"], text)
        await message.answer("Дякую, номер оновлено! 💗", reply_markup=_main_menu_kb())
        return

    girl = _link_girl_by_phone(text, chat_id)
    if girl:
        bal = get_balance(girl["data"])
        await message.answer(
            f"Знайшла тебе — {girl['data'].get('Імʼя', '')}! 💗\n\n"
            f"💰 {int(bal['available'])} балів · {bal['status']}",
            parse_mode=ParseMode.HTML,
            reply_markup=_main_menu_kb(message.from_user.id),
        )
    else:
        await message.answer(
            "Не знайшла цей номер у базі 😔\n"
            "Натисни /start щоб зареєструватись!",
            parse_mode=ParseMode.HTML,
        )
