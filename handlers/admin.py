import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_CHAT_ID, ADMIN_CHAT_IDS
from sheets import (
    find_girl_by_name_and_event,
    find_girls_by_name,
    get_bookings_for_event,
    get_girls_for_event,
    get_girls_with_chat_id,
    get_upcoming_events,
    log_broadcast,
    ocr_find_similar,
    ocr_learn,
    ocr_lookup,
    update_girl_profile,
    write_match_blank,
)
from services.claude_vision import recognize_match_grid, recognize_profile
from texts import (
    ADMIN_PANEL,
    BLANK_CONFIRM,
    BLANK_ERROR,
    BLANK_NOT_FOUND,
    BLANK_SAVED,
    BLANK_SELECT_EVENT,
    BLANK_SEND_PHOTO,
    BROADCAST_CONFIRM,
    BROADCAST_DONE,
    BROADCAST_ENTER_TEXT,
    BROADCAST_SELECT_AUDIENCE,
    BROADCAST_SELECT_EVENT,
)

log = logging.getLogger(__name__)

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_CHAT_IDS


# --- FSM States ---

class BlankFSM(StatesGroup):
    waiting_profile_photo = State()
    waiting_match_photo = State()
    waiting_event = State()
    resolving_unclear = State()
    confirming = State()
    selecting_girl = State()


class BroadcastFSM(StatesGroup):
    selecting_type = State()
    selecting_event = State()
    entering_text = State()
    confirming = State()


# --- Admin panel ---

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        ADMIN_PANEL,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Розпізнати бланк", callback_data="admin_blank")],
            [InlineKeyboardButton(text="📢 Розіслати контент", callback_data="admin_broadcast_content")],
            [InlineKeyboardButton(text="📨 Довільна розсилка", callback_data="admin_broadcast_custom")],
        ]),
    )


# --- Blank recognition flow ---

@router.callback_query(F.data == "admin_blank")
async def cb_admin_blank(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.set_state(BlankFSM.waiting_profile_photo)
    await callback.message.answer(BLANK_SEND_PHOTO, parse_mode=ParseMode.HTML)


@router.message(BlankFSM.waiting_profile_photo, F.photo)
async def on_profile_photo(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    wait_msg = await message.answer("⏳ Розпізнаю профіль...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    data = image_bytes.read()

    try:
        profile = await recognize_profile(data)
    except Exception as e:
        log.error("Profile recognition error: %s", e)
        await wait_msg.edit_text(BLANK_ERROR, parse_mode=ParseMode.HTML)
        await state.clear()
        return

    await state.update_data(profile=profile)
    await state.set_state(BlankFSM.waiting_match_photo)
    await wait_msg.edit_text(
        f"✅ Профіль розпізнано: <b>{profile.get('name', '?')}</b>, №{profile.get('number', '?')}\n\n"
        "Тепер надішли фото <b>матч-сітки</b> (бордова сторона):",
        parse_mode=ParseMode.HTML,
    )


@router.message(BlankFSM.waiting_match_photo, F.photo)
async def on_match_photo(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    wait_msg = await message.answer("⏳ Розпізнаю матч-сітку...")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    data = image_bytes.read()

    try:
        match_data = await recognize_match_grid(data)
    except Exception as e:
        log.error("Match grid recognition error: %s", e)
        await wait_msg.edit_text(BLANK_ERROR, parse_mode=ParseMode.HTML)
        await state.clear()
        return

    await state.update_data(match_data=match_data)
    await state.set_state(BlankFSM.waiting_event)

    slots = match_data.get("slots", {})
    filled = sum(1 for v in slots.values() if v)

    events = get_upcoming_events()
    all_events = _get_recent_and_upcoming_events()

    buttons = []
    for ev in all_events:
        name = ev.get("Назва івенту", "").strip()
        date = ev.get("Дата івенту", "")[:10]
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({date})",
            callback_data=f"blank_event:{name}|{date}",
        )])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="blank_cancel")])

    await wait_msg.edit_text(
        f"✅ Матч-сітка: <b>{filled}</b> відміток\n\n" + BLANK_SELECT_EVENT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


def _get_recent_and_upcoming_events() -> list[dict]:
    from sheets import ws_events
    from datetime import datetime, timedelta
    data = ws_events.get_all_values()
    headers = data[0]
    events = []
    cutoff = datetime.now() - timedelta(days=30)
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
            if event_date >= cutoff:
                d["_date"] = event_date
                events.append(d)
        except (ValueError, TypeError):
            continue
    events.sort(key=lambda x: x["_date"], reverse=True)
    return events


@router.callback_query(F.data.startswith("blank_event:"))
async def cb_blank_event(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    parts = callback.data.replace("blank_event:", "").split("|")
    event_name = parts[0]
    event_date = parts[1] if len(parts) > 1 else ""

    await state.update_data(event_name=event_name, event_date=event_date)

    fsm_data = await state.get_data()
    profile = fsm_data["profile"]
    match_data = fsm_data["match_data"]
    slots = match_data.get("slots", {})
    filled = sum(1 for v in slots.values() if v)

    seeking_parts = []
    seeking = profile.get("seeking", {})
    if seeking.get("подругу"):
        seeking_parts.append("подругу")
    if seeking.get("знайомства"):
        seeking_parts.append("знайомства")
    if seeking.get("колаборацію"):
        seeking_parts.append("колаборацію")
    if seeking.get("бізнес"):
        seeking_parts.append("бізнес")
    if seeking.get("романтика"):
        seeking_parts.append("романтику")
    if profile.get("seeking_custom"):
        seeking_parts.append(profile["seeking_custom"])
    seeking_text = ", ".join(seeking_parts) if seeking_parts else "—"

    # Collect unclear fields that need resolution
    unclear = profile.get("unclear_fields", [])
    unclear = [uf for uf in unclear if len(uf.get("possible_readings", [])) > 1]
    await state.update_data(unclear_queue=unclear, unclear_index=0)

    # If there are unclear fields, resolve them first
    if unclear:
        await state.set_state(BlankFSM.resolving_unclear)
        await _send_unclear_choice(callback.message, state, edit=True)
    else:
        await _send_final_confirm(callback.message, state, profile, match_data, seeking_text, filled, edit=True)


FIELD_LABELS = {
    "name": "Ім'я",
    "age": "Вік",
    "occupation": "Чим займається",
    "hobbies": "Хобі",
    "best_trait": "Краща риса",
    "worst_trait": "Найгірша риса",
}


async def _send_unclear_choice(message, state: FSMContext, edit: bool = False):
    fsm_data = await state.get_data()
    unclear_queue = fsm_data.get("unclear_queue", [])
    index = fsm_data.get("unclear_index", 0)

    if index >= len(unclear_queue):
        # All unclear fields resolved — go to final confirm
        profile = fsm_data["profile"]
        match_data = fsm_data["match_data"]
        slots = match_data.get("slots", {})
        filled = sum(1 for v in slots.values() if v)
        seeking = profile.get("seeking", {})
        seeking_parts = []
        if seeking.get("подругу"): seeking_parts.append("подругу")
        if seeking.get("знайомства"): seeking_parts.append("знайомства")
        if seeking.get("колаборацію"): seeking_parts.append("колаборацію")
        if seeking.get("бізнес"): seeking_parts.append("бізнес")
        if seeking.get("романтика"): seeking_parts.append("романтику")
        if profile.get("seeking_custom"): seeking_parts.append(profile["seeking_custom"])
        seeking_text = ", ".join(seeking_parts) if seeking_parts else "—"
        await state.set_state(BlankFSM.confirming)
        await _send_final_confirm(message, state, profile, match_data, seeking_text, filled, edit=edit)
        return

    uf = unclear_queue[index]
    field = uf["field"]
    label = FIELD_LABELS.get(field, field)
    raw = uf.get("raw_chars", "?")
    readings = uf.get("possible_readings", [])[:3]

    # Check learned dictionary — exact match auto-resolves
    learned = ocr_lookup(field, raw)
    if learned:
        fsm_data = await state.get_data()
        profile = fsm_data["profile"]
        profile[field] = learned
        await state.update_data(profile=profile, unclear_index=index + 1)
        if edit:
            try:
                await message.edit_text(
                    f"✅ <b>{label}</b>: {learned} <i>(з словника)</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        else:
            await message.answer(
                f"✅ <b>{label}</b>: {learned} <i>(з словника)</i>",
                parse_mode=ParseMode.HTML,
            )
        import asyncio as _aio
        await _aio.sleep(0.5)
        await _send_unclear_choice(message, state, edit=False)
        return

    # Check for similar entries in dictionary — add as first options
    similar = ocr_find_similar(field, raw)
    if similar:
        readings = similar + [r for r in readings if r not in similar]
        readings = readings[:4]

    text = (
        f"🔍 <b>Нечітке поле ({index + 1}/{len(unclear_queue)})</b>\n\n"
        f"📝 <b>{label}</b>\n"
        f"Бачу: «{raw}»\n\n"
        f"Обери правильний варіант або <b>напиши свій текстом</b>:"
    )

    buttons = []
    for i, reading in enumerate(readings):
        display = reading
        buttons.append([InlineKeyboardButton(
            text=display,
            callback_data=f"uf_pick:{index}:{i}",
        )])
    buttons.append([InlineKeyboardButton(text="⏭ Залишити як є", callback_data=f"uf_skip:{index}")])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="blank_cancel")])

    if edit:
        await message.edit_text(text, parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await message.answer(text, parse_mode=ParseMode.HTML,
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("uf_pick:"), BlankFSM.resolving_unclear)
async def cb_unclear_pick(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    parts = callback.data.replace("uf_pick:", "").split(":")
    field_idx = int(parts[0])
    reading_idx = int(parts[1])

    fsm_data = await state.get_data()
    unclear_queue = fsm_data.get("unclear_queue", [])
    profile = fsm_data["profile"]

    if field_idx < len(unclear_queue):
        uf = unclear_queue[field_idx]
        field = uf["field"]
        readings = uf.get("possible_readings", [])
        if reading_idx < len(readings):
            chosen = readings[reading_idx]
            profile[field] = chosen
            await state.update_data(profile=profile)
            raw = uf.get("raw_chars", "")
            if raw:
                ocr_learn(field, raw, chosen)

    await state.update_data(unclear_index=field_idx + 1)
    await _send_unclear_choice(callback.message, state, edit=True)


@router.callback_query(F.data.startswith("uf_skip:"), BlankFSM.resolving_unclear)
async def cb_unclear_skip(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    field_idx = int(callback.data.replace("uf_skip:", ""))
    await state.update_data(unclear_index=field_idx + 1)
    await _send_unclear_choice(callback.message, state, edit=True)


@router.message(BlankFSM.resolving_unclear, F.text)
async def on_unclear_manual_input(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    fsm_data = await state.get_data()
    unclear_queue = fsm_data.get("unclear_queue", [])
    index = fsm_data.get("unclear_index", 0)
    profile = fsm_data["profile"]

    if index < len(unclear_queue):
        uf = unclear_queue[index]
        field = uf["field"]
        manual_text = message.text.strip()
        profile[field] = manual_text
        await state.update_data(profile=profile, unclear_index=index + 1)
        raw = uf.get("raw_chars", "")
        if raw:
            ocr_learn(field, raw, manual_text)

    await _send_unclear_choice(message, state, edit=False)


async def _send_final_confirm(message, state: FSMContext, profile: dict = None,
                               match_data: dict = None, seeking_text: str = "",
                               filled: int = 0, edit: bool = False):
    # Always read fresh data from state to include manual corrections
    fsm_data = await state.get_data()
    profile = fsm_data.get("profile", profile or {})
    match_data = match_data or fsm_data.get("match_data", {})

    slots = match_data.get("slots", {})
    filled = sum(1 for v in slots.values() if v)

    seeking = profile.get("seeking", {})
    seeking_parts = []
    if seeking.get("подругу"): seeking_parts.append("подругу")
    if seeking.get("знайомства"): seeking_parts.append("знайомства")
    if seeking.get("колаборацію"): seeking_parts.append("колаборацію")
    if seeking.get("бізнес"): seeking_parts.append("бізнес")
    if seeking.get("романтика"): seeking_parts.append("романтику")
    if profile.get("seeking_custom"): seeking_parts.append(profile["seeking_custom"])
    seeking_text = ", ".join(seeking_parts) if seeking_parts else "—"

    text = BLANK_CONFIRM.format(
        name=profile.get("name", "?"),
        age=profile.get("age", "?"),
        occupation=profile.get("occupation", "?"),
        hobbies=profile.get("hobbies", "?"),
        best_trait=profile.get("best_trait", "?"),
        worst_trait=profile.get("worst_trait", "?"),
        seeking=seeking_text,
        match_count=filled,
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Зберегти", callback_data="blank_save"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="blank_cancel"),
        ],
    ])

    if edit:
        await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(F.data == "blank_save")
async def cb_blank_save(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    fsm_data = await state.get_data()
    profile = fsm_data["profile"]
    match_data = fsm_data["match_data"]
    event_name = fsm_data["event_name"]
    event_date = fsm_data["event_date"]

    name = profile.get("name", "")
    candidates = find_girls_by_name(name)

    if len(candidates) > 1:
        # Multiple matches — let Diana choose
        await state.update_data(girl_candidates=[(c["row"], c["data"].get("Імʼя", ""), c["data"].get("ID", "")) for c in candidates])
        await state.set_state(BlankFSM.selecting_girl)
        buttons = []
        for i, c in enumerate(candidates[:6]):
            d = c["data"]
            label = f"{d.get('Імʼя', '?')} (ID:{d.get('ID', '?')}, {d.get('Телефон', '') or d.get('Instagram', '') or '—'})"
            label = label[:60]
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"girl_pick:{c['row']}")])
        buttons.append([InlineKeyboardButton(text="➕ Створити нову", callback_data="girl_pick:new")])
        buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="blank_cancel")])
        await callback.message.edit_text(
            f"👥 Знайдено <b>{len(candidates)}</b> збігів для «{name}».\nОбери правильну:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        return

    if len(candidates) == 1:
        girl = candidates[0]
    else:
        # No match — create new
        from sheets import register_girl
        register_girl(chat_id="", username="", full_name=name)
        girl = find_girl_by_name_and_event(name, event_name)
        if not girl:
            await callback.message.edit_text(BLANK_NOT_FOUND, parse_mode=ParseMode.HTML)
            await state.clear()
            return
        log.info("Created new girl record for blank: %s", name)

    await _save_blank_data(callback, state, girl, profile, match_data, event_name, event_date)


@router.callback_query(F.data.startswith("girl_pick:"), BlankFSM.selecting_girl)
async def cb_girl_pick(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    pick = callback.data.replace("girl_pick:", "")
    fsm_data = await state.get_data()
    profile = fsm_data["profile"]
    match_data = fsm_data["match_data"]
    event_name = fsm_data["event_name"]
    event_date = fsm_data["event_date"]
    name = profile.get("name", "")

    if pick == "new":
        from sheets import register_girl
        register_girl(chat_id="", username="", full_name=name)
        girl = find_girl_by_name_and_event(name, event_name)
        if not girl:
            await callback.message.edit_text(BLANK_NOT_FOUND, parse_mode=ParseMode.HTML)
            await state.clear()
            return
        log.info("Created new girl from pick: %s", name)
    else:
        row = int(pick)
        from sheets import ws_girls
        data = ws_girls.get_all_values()
        headers = data[0]
        girl_row = data[row - 1] if row <= len(data) else None
        if not girl_row:
            await callback.message.edit_text(BLANK_NOT_FOUND, parse_mode=ParseMode.HTML)
            await state.clear()
            return
        girl = {"row": row, "data": dict(zip(headers, girl_row))}

    await state.set_state(BlankFSM.confirming)
    await _save_blank_data(callback, state, girl, profile, match_data, event_name, event_date)


async def _save_blank_data(callback, state, girl, profile, match_data, event_name, event_date):
    name = profile.get("name", "")
    seeking = profile.get("seeking", {})
    profile_update = {}
    if profile.get("age"):
        profile_update["Вік"] = profile["age"]
    if profile.get("occupation"):
        profile_update["Чим займається"] = profile["occupation"]
    if profile.get("hobbies"):
        profile_update["Хобі"] = profile["hobbies"]
    if profile.get("best_trait"):
        profile_update["Моя краща риса"] = profile["best_trait"]
    if profile.get("worst_trait"):
        profile_update["Моя найгірша риса"] = profile["worst_trait"]

    profile_update["Шукаю: подругу"] = "✓" if seeking.get("подругу") else "✗"
    profile_update["Шукаю: знайомства"] = "✓" if seeking.get("знайомства") else "✗"
    profile_update["Шукаю: колаборацію"] = "✓" if seeking.get("колаборацію") else "✗"
    profile_update["Шукаю: бізнес"] = "✓" if seeking.get("бізнес") else "✗"
    profile_update["Шукаю: романтику"] = "✓" if seeking.get("романтика") else "✗"
    if profile.get("seeking_custom"):
        profile_update["Шукаю: свій варіант"] = profile["seeking_custom"]

    update_girl_profile(girl["row"], profile_update)

    slots = match_data.get("slots", {})
    slot_list = [slots.get(str(i), "") or "" for i in range(1, 25)]

    write_match_blank(
        girl_id=girl["data"].get("ID", ""),
        girl_name=girl["data"].get("Імʼя", name),
        event_name=event_name,
        event_date=event_date,
        blank_number=int(profile.get("number", 0) or 0),
        slots=slot_list,
    )

    await callback.message.edit_text(
        BLANK_SAVED.format(name=girl["data"].get("Імʼя", name)),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()


@router.callback_query(F.data == "blank_cancel")
async def cb_blank_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Скасовано", parse_mode=ParseMode.HTML)


# --- Broadcast flow ---

@router.callback_query(F.data == "admin_broadcast_content")
async def cb_broadcast_content(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.update_data(broadcast_type="content")

    events = _get_recent_and_upcoming_events()
    buttons = []
    for ev in events:
        name = ev.get("Назва івенту", "").strip()
        date = ev.get("Дата івенту", "")[:10]
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({date})",
            callback_data=f"bc_event:{name}|{date}",
        )])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="bc_cancel")])

    await state.set_state(BroadcastFSM.selecting_event)
    await callback.message.edit_text(
        BROADCAST_SELECT_EVENT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "admin_broadcast_custom")
async def cb_broadcast_custom(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.update_data(broadcast_type="custom")

    events = _get_recent_and_upcoming_events()
    buttons = []
    for ev in events:
        name = ev.get("Назва івенту", "").strip()
        date = ev.get("Дата івенту", "")[:10]
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({date})",
            callback_data=f"bc_event:{name}|{date}",
        )])
    buttons.append([InlineKeyboardButton(text="📋 Всі дівчата", callback_data="bc_event:__all__")])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="bc_cancel")])

    await state.set_state(BroadcastFSM.selecting_event)
    await callback.message.edit_text(
        BROADCAST_SELECT_AUDIENCE,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("bc_event:"), BroadcastFSM.selecting_event)
async def cb_bc_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    raw = callback.data.replace("bc_event:", "")

    if raw == "__all__":
        await state.update_data(audience="all", event_name="Всі дівчата", event_date="")
    else:
        parts = raw.split("|")
        await state.update_data(audience="event", event_name=parts[0], event_date=parts[1] if len(parts) > 1 else "")

    await state.set_state(BroadcastFSM.entering_text)
    await callback.message.edit_text(BROADCAST_ENTER_TEXT, parse_mode=ParseMode.HTML)


@router.message(BroadcastFSM.entering_text, F.text)
async def on_broadcast_text(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    text = message.text.strip()
    await state.update_data(text=text)

    fsm_data = await state.get_data()
    audience = fsm_data.get("audience", "event")
    event_name = fsm_data.get("event_name", "")

    if audience == "all":
        girls = get_girls_with_chat_id()
    else:
        event_date = fsm_data.get("event_date", "")
        girls = get_girls_for_event(event_date)

    await state.update_data(recipient_count=len(girls))
    await state.set_state(BroadcastFSM.confirming)

    await message.answer(
        BROADCAST_CONFIRM.format(
            audience=event_name,
            count=len(girls),
            text=text[:500],
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Надіслати", callback_data="bc_send"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="bc_cancel"),
            ],
        ]),
    )


@router.callback_query(F.data == "bc_send", BroadcastFSM.confirming)
async def cb_bc_send(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()

    fsm_data = await state.get_data()
    text = fsm_data["text"]
    audience = fsm_data.get("audience", "event")
    event_name = fsm_data.get("event_name", "")
    event_date = fsm_data.get("event_date", "")
    broadcast_type = fsm_data.get("broadcast_type", "custom")

    if audience == "all":
        girls = get_girls_with_chat_id()
    else:
        girls = get_girls_for_event(event_date)

    await callback.message.edit_text("⏳ Надсилаю...", parse_mode=ParseMode.HTML)

    sent = 0
    bot: Bot = callback.bot
    for girl in girls:
        chat_id = girl.get("Telegram chat id", "").strip()
        if not chat_id:
            continue
        try:
            await bot.send_message(int(chat_id), text, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            log.warning("Broadcast send error to %s: %s", chat_id, e)

    log_broadcast(broadcast_type, event_name, text, sent)

    await callback.message.edit_text(
        BROADCAST_DONE.format(sent=sent, total=len(girls)),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()


@router.callback_query(F.data == "bc_cancel")
async def cb_bc_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Розсилку скасовано", parse_mode=ParseMode.HTML)
