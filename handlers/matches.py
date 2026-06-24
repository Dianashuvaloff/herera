import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from sheets import find_girl_by_chat_id, get_girl_events_with_blanks
from services.match_engine import find_mutual_matches
from texts import (
    MATCH_CARD,
    MATCHES_EMPTY,
    MATCHES_NO_EVENTS,
    MATCHES_SELECT_EVENT,
)

log = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "matches")
async def cb_matches(callback: CallbackQuery):
    await callback.answer()
    girl = find_girl_by_chat_id(str(callback.from_user.id))
    if not girl:
        await callback.message.edit_text("Натисни /start щоб зареєструватись 💗", parse_mode=ParseMode.HTML)
        return

    girl_id = girl["data"].get("ID", "")
    events = get_girl_events_with_blanks(girl_id)

    if not events:
        await callback.message.edit_text(
            MATCHES_NO_EVENTS,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Меню", callback_data="menu")],
            ]),
        )
        return

    buttons = []
    for event_name in events:
        buttons.append([InlineKeyboardButton(
            text=event_name,
            callback_data=f"matches_ev:{event_name[:40]}",
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Меню", callback_data="menu")])

    await callback.message.edit_text(
        MATCHES_SELECT_EVENT,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("matches_ev:"))
async def cb_matches_event(callback: CallbackQuery):
    await callback.answer()
    event_name = callback.data.replace("matches_ev:", "")

    girl = find_girl_by_chat_id(str(callback.from_user.id))
    if not girl:
        return

    girl_id = girl["data"].get("ID", "")
    matches = find_mutual_matches(girl_id, event_name)

    if not matches:
        await callback.message.edit_text(
            MATCHES_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Матчі", callback_data="matches")],
                [InlineKeyboardButton(text="◀️ Меню", callback_data="menu")],
            ]),
        )
        return

    text = f"💗 <b>Матчі з вечора «{event_name}»</b>\n\n"

    for m in matches[:10]:
        socials = ""
        if m["instagram"]:
            socials += f'📸 <a href="https://instagram.com/{m["instagram"].strip("@")}">Instagram</a>\n'
        if m["tiktok"]:
            socials += f"🎵 TikTok: {m['tiktok']}\n"
        if m["telegram"]:
            socials += f"✈️ Telegram: @{m['telegram'].strip('@')}\n"

        reasons = ", ".join(m["match_reasons"]) if m["match_reasons"] else "взаємний інтерес"

        text += MATCH_CARD.format(
            name=m["name"],
            age=m["age"] or "—",
            occupation=m["occupation"] or "—",
            hobbies=m["hobbies"] or "—",
            match_reasons=reasons,
            socials=socials,
        )
        text += "\n─────────────────\n\n"

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Матчі", callback_data="matches")],
            [InlineKeyboardButton(text="◀️ Меню", callback_data="menu")],
        ]),
    )
