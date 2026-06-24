import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from config import POINTS
from sheets import (
    add_points_record,
    check_story_tag_awarded,
    find_girl_by_chat_id,
    get_balance,
    ws_girls,
)
from texts import POINTS_STORY_ALREADY, STATUS_EMOJI

log = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("story_tag:"))
async def cb_story_tag(callback: CallbackQuery):
    await callback.answer()

    girl = find_girl_by_chat_id(str(callback.from_user.id))
    if not girl:
        return

    event_name = callback.data.replace("story_tag:", "")
    girl_id = girl["data"].get("ID", "")
    girl_name = girl["data"].get("Імʼя", "")

    if check_story_tag_awarded(girl_id, event_name):
        await callback.message.edit_text(
            POINTS_STORY_ALREADY,
            parse_mode=ParseMode.HTML,
        )
        return

    pts = POINTS["story_tag"]
    add_points_record(girl_id, girl_name, "story_tag", pts, event_name)

    headers = ws_girls.row_values(1)
    col_map = {h: i + 1 for i, h in enumerate(headers)}

    total = float(girl["data"].get("Total балів", 0) or 0) + pts
    available = float(girl["data"].get("Available балів", 0) or 0) + pts

    if "Total балів" in col_map:
        ws_girls.update_cell(girl["row"], col_map["Total балів"], str(int(total)))
    if "Available балів" in col_map:
        ws_girls.update_cell(girl["row"], col_map["Available балів"], str(int(available)))

    bal = {"total": total, "available": available, "status": ""}
    from sheets import get_status_label
    status = get_status_label(total)
    status_emoji = STATUS_EMOJI.get(status, "🤍")

    await callback.message.edit_text(
        f"📸 <b>+{pts} балів за сторіс!</b>\n\n"
        f"Зараз: <b>{int(available)}</b> балів\n"
        f"Статус: {status_emoji} <b>{status}</b>\n\n"
        f"Дякую що ділишся! 💗",
        parse_mode=ParseMode.HTML,
    )
