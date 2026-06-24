import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import DM_LINK, STATUS_PERKS, get_reels_link
from sheets import (
    get_balance,
    get_bookings_for_event,
    get_girls_for_event,
    get_next_status_info,
    ws_events,
)
from texts import (
    POINTS_ALREADY_MAX,
    POINTS_FREE_TICKET,
    POINTS_NEXT_PERK,
    POINTS_POST_EVENT,
    POINTS_STORY_TAG,
    REMINDER_4H_BEFORE,
    REMINDER_BEFORE_EVENT,
    REMINDER_DAY_OF_UNPAID,
    REMINDER_PAYMENT_NOTE,
    REMINDER_POST_EVENT,
    REMINDER_REELS_NOTE,
    STATUS_EMOJI,
)

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
_bot = None


def init_scheduler(bot):
    global _bot
    _bot = bot
    scheduler.add_job(
        _scan_and_schedule,
        IntervalTrigger(hours=6),
        id="scan_events",
        replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started")
    import asyncio
    asyncio.get_event_loop().create_task(_scan_and_schedule())


async def _scan_and_schedule():
    log.info("Scanning events for reminders...")
    try:
        data = ws_events.get_all_values()
        headers = data[0]
        now = datetime.now()

        for row in data[1:]:
            if not row[0]:
                continue
            ev = dict(zip(headers, row))
            raw_date = ev.get("Дата івенту", "")[:10]
            raw_time = ev.get("Час", "19:00").strip()

            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue

            try:
                hour, minute = map(int, raw_time.split(":"))
            except (ValueError, AttributeError):
                hour, minute = 19, 0

            event_dt = event_date.replace(hour=hour, minute=minute)
            event_name = ev.get("Назва івенту", "").strip()
            location = ev.get("Локація", "").strip()
            dress_code = ev.get("Дрес-код", "").strip()
            emoji = ev.get("Емоджі", "").strip() or (event_name[0] if event_name else "📅")

            # 1-2 days before (10:00)
            remind_dt = event_date - timedelta(days=1)
            remind_dt = remind_dt.replace(hour=10, minute=0)
            if remind_dt > now:
                scheduler.add_job(
                    _send_before_event_reminders,
                    DateTrigger(run_date=remind_dt),
                    id=f"remind_before_{raw_date}",
                    replace_existing=True,
                    kwargs={
                        "event_date_str": raw_date, "event_name": event_name,
                        "event_time": raw_time, "location": location, "emoji": emoji,
                    },
                )

            # Day of event 09:00 — unpaid check
            day_of_dt = event_date.replace(hour=9, minute=0)
            if day_of_dt > now:
                scheduler.add_job(
                    _send_day_of_unpaid,
                    DateTrigger(run_date=day_of_dt),
                    id=f"remind_dayof_{raw_date}",
                    replace_existing=True,
                    kwargs={"event_date_str": raw_date, "event_name": event_name},
                )

            # 4 hours before
            four_h_dt = event_dt - timedelta(hours=4)
            if four_h_dt > now:
                scheduler.add_job(
                    _send_4h_before,
                    DateTrigger(run_date=four_h_dt),
                    id=f"remind_4h_{raw_date}",
                    replace_existing=True,
                    kwargs={
                        "event_date_str": raw_date, "event_name": event_name,
                        "location": location, "dress_code": dress_code, "emoji": emoji,
                    },
                )

            # Post-event (+1 day at 12:00)
            post_dt = event_date + timedelta(days=1)
            post_dt = post_dt.replace(hour=12, minute=0)
            if post_dt > now:
                scheduler.add_job(
                    _send_post_event,
                    DateTrigger(run_date=post_dt),
                    id=f"remind_post_{raw_date}",
                    replace_existing=True,
                    kwargs={"event_date_str": raw_date, "event_name": event_name},
                )

    except Exception as e:
        log.error("Scheduler scan error: %s", e)


async def _send_before_event_reminders(event_date_str: str, event_name: str,
                                        event_time: str, location: str, emoji: str):
    girls = get_girls_for_event(event_date_str)
    for girl in girls:
        booking = girl.get("_booking", {})
        status = booking.get("Статус оплати", "").lower()
        if "передоплата" not in status and "оплат" not in status:
            continue

        chat_id = girl.get("Telegram chat id", "").strip()
        if not chat_id:
            continue

        base = float(booking.get("Сума базова", 0) or 0)
        paid = float(booking.get("Сума оплачена", 0) or 0)
        remaining = max(0, base - paid)

        payment_note = ""
        if remaining > 0:
            payment_note = REMINDER_PAYMENT_NOTE.format(remaining=int(remaining))

        try:
            await _bot.send_message(
                int(chat_id),
                REMINDER_BEFORE_EVENT.format(
                    name=girl.get("Імʼя", ""),
                    emoji=emoji,
                    event_name=event_name,
                    event_date=event_date_str,
                    event_time=event_time,
                    event_location=location,
                    payment_note=payment_note,
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Reminder send error: %s", e)


async def _send_day_of_unpaid(event_date_str: str, event_name: str):
    girls = get_girls_for_event(event_date_str)
    for girl in girls:
        booking = girl.get("_booking", {})
        status = booking.get("Статус оплати", "").lower()
        if "повна" in status:
            continue

        base = float(booking.get("Сума базова", 0) or 0)
        paid = float(booking.get("Сума оплачена", 0) or 0)
        remaining = max(0, base - paid)
        if remaining <= 0:
            continue

        chat_id = girl.get("Telegram chat id", "").strip()
        if not chat_id:
            continue

        try:
            await _bot.send_message(
                int(chat_id),
                REMINDER_DAY_OF_UNPAID.format(
                    name=girl.get("Імʼя", ""),
                    remaining=int(remaining),
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Day-of reminder error: %s", e)


async def _send_4h_before(event_date_str: str, event_name: str,
                           location: str, dress_code: str, emoji: str):
    reels_link = get_reels_link(location)
    reels_note = REMINDER_REELS_NOTE.format(reels_link=reels_link) if reels_link else ""

    girls = get_girls_for_event(event_date_str)
    for girl in girls:
        chat_id = girl.get("Telegram chat id", "").strip()
        if not chat_id:
            continue
        try:
            await _bot.send_message(
                int(chat_id),
                REMINDER_4H_BEFORE.format(
                    emoji=emoji,
                    event_name=event_name,
                    event_location=location,
                    dress_code=dress_code or "на твій смак",
                    reels_note=reels_note,
                ),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning("4h reminder error: %s", e)


async def _send_post_event(event_date_str: str, event_name: str):
    from sheets import check_story_tag_awarded

    girls = get_girls_for_event(event_date_str)
    for girl in girls:
        chat_id = girl.get("Telegram chat id", "").strip()
        if not chat_id:
            continue

        bal = get_balance(girl)
        total = bal["total"]
        available = bal["available"]
        status = bal["status"]
        status_emoji_val = STATUS_EMOJI.get(status, "🤍")

        next_info = get_next_status_info(total)
        if next_info:
            perk = STATUS_PERKS.get(next_info["status"], "")
            next_perk_text = POINTS_NEXT_PERK.format(
                next_status=next_info["status"],
                points_left=int(next_info["points_left"]),
                perk=perk,
            )
        else:
            next_perk_text = POINTS_ALREADY_MAX

        girl_id = girl.get("ID", "")
        already_tagged = check_story_tag_awarded(girl_id, event_name)
        story_tag_text = POINTS_STORY_TAG if not already_tagged else ""

        events_until_free = max(0, 10 - int(available / 100)) if available < 1000 else 0
        free_ticket_text = POINTS_FREE_TICKET.format(events_left=events_until_free) if events_until_free > 0 else ""

        try:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            kb = None
            if not already_tagged:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📸 Я відмітила в сторіс!",
                        callback_data=f"story_tag:{event_name[:30]}",
                    )],
                ])

            await _bot.send_message(
                int(chat_id),
                POINTS_POST_EVENT.format(
                    available=int(available),
                    status_emoji=status_emoji_val,
                    status=status,
                    next_perk_text=next_perk_text,
                    story_tag_text=story_tag_text,
                    free_ticket_text=free_ticket_text,
                ),
                parse_mode="HTML",
                reply_markup=kb,
            )
        except Exception as e:
            log.warning("Post-event message error: %s", e)

        try:
            await _bot.send_message(
                int(chat_id),
                REMINDER_POST_EVENT.format(
                    name=girl.get("Імʼя", ""),
                    dm_link=DM_LINK,
                ),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning("Post-event discount error: %s", e)
