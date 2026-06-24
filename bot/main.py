import asyncio
import logging
import threading

import requests as sync_requests
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ADMIN_CHAT_ID, API_BASE_URL, API_PORT, BOT_TOKEN, MONO_TOKEN, REFCODE_DISCOUNT_PCT
from handlers import all_routers
from sheets import (
    create_booking,
    get_events_for_site,
    validate_refcode,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ── FastAPI ──

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def _tg_notify(text: str):
    try:
        sync_requests.post(TG_API, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=5)
    except Exception as e:
        log.error("TG notify error: %s", e)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/events")
def api_events():
    try:
        events = get_events_for_site()
        return JSONResponse({"events": events})
    except Exception as e:
        log.error("Events API error: %s", e)
        return JSONResponse({"events": [], "error": str(e)}, status_code=500)


@app.post("/api/validate-refcode")
async def api_validate_refcode(request: Request):
    data = await request.json()
    code = data.get("code", "").strip()
    if not code:
        return JSONResponse({"valid": False})
    result = validate_refcode(code)
    if result:
        return JSONResponse({"valid": True, "discount_pct": REFCODE_DISCOUNT_PCT})
    return JSONResponse({"valid": False})


@app.post("/api/booking")
async def api_booking(request: Request):
    data = await request.json()

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    instagram = data.get("instagram", "").strip()
    telegram = data.get("telegram", "").strip()
    event_name = data.get("event_name", "").strip()
    event_date = data.get("event_date", "").strip()
    event_location = data.get("event_location", "").strip()
    payment_type = data.get("payment_type", "full")
    refcode = data.get("refcode", "").strip()
    amount = float(data.get("amount", 0))

    if not name or not phone or not amount:
        return JSONResponse({"error": "name, phone, amount required"}, status_code=400)

    discount = 0
    if refcode:
        rc = validate_refcode(refcode)
        if rc:
            discount = round(amount * REFCODE_DISCOUNT_PCT / 100)
            amount = amount - discount

    amount_kopecks = int(amount * 100)

    try:
        resp = sync_requests.post(
            "https://api.monobank.ua/api/merchant/invoice/create",
            headers={"X-Token": MONO_TOKEN},
            json={
                "amount": amount_kopecks,
                "ccy": 980,
                "merchantPaymInfo": {
                    "reference": f"{event_name} | {name}",
                    "destination": f"HER ERA — {event_name}",
                    "basketOrder": [
                        {
                            "name": f"Бронювання {event_name}",
                            "qty": 1,
                            "sum": amount_kopecks,
                        }
                    ],
                },
                "redirectUrl": "https://herera.netlify.app/?paid=true",
                "webHookUrl": f"{API_BASE_URL}/api/mono-webhook",
            },
            timeout=10,
        )
        mono_data = resp.json()
    except Exception as e:
        log.error("Monobank error: %s", e)
        return JSONResponse({"error": "payment service unavailable"}, status_code=502)

    invoice_id = mono_data.get("invoiceId", "")
    pay_url = mono_data.get("pageUrl", "")

    if not pay_url:
        log.error("Monobank no pageUrl: %s", mono_data)
        return JSONResponse({"error": "payment creation failed"}, status_code=502)

    booking_id = create_booking(
        event_name=event_name,
        event_date=event_date,
        location=event_location,
        name=name,
        phone=phone,
        instagram=instagram,
        telegram=telegram,
        base_amount=amount + discount,
        refcode=refcode,
        discount=discount,
        paid_amount=amount,
        payment_type=payment_type,
        invoice_id=invoice_id,
    )

    discount_line = f"\n🎟 Промокод: {refcode} (знижка {discount} грн)" if refcode and discount else ""
    _tg_notify(
        f"🎉 <b>НОВЕ БРОНЮВАННЯ З САЙТУ!</b>\n\n"
        f"👤 {name}\n"
        f"📱 Instagram: {instagram or '—'}\n"
        f"✈️ Telegram: {telegram or '—'}\n"
        f"📞 {phone}\n\n"
        f"🎪 {event_name}\n"
        f"📅 {event_date}\n"
        f"💰 {amount} грн ({payment_type})"
        f"{discount_line}\n"
        f"🆔 {booking_id}"
    )

    return JSONResponse({"success": True, "payUrl": pay_url, "bookingId": booking_id})


@app.post("/api/mono-webhook")
async def api_mono_webhook(request: Request):
    from sheets import update_booking_status

    data = await request.json()
    invoice_id = data.get("invoiceId", "")
    status = data.get("status", "")

    log.info("Mono webhook: invoiceId=%s status=%s", invoice_id, status)

    if status == "success" and invoice_id:
        booking = update_booking_status(invoice_id, "Повна оплата")
        if booking:
            name = booking["data"].get("Імʼя", "")
            _tg_notify(
                f"✅ <b>Оплата підтверджена!</b>\n\n"
                f"👤 {name}\n"
                f"💰 Статус: Повна оплата\n"
                f"🆔 Invoice: {invoice_id}"
            )

    return JSONResponse({"status": "ok"})


def _run_api():
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")


async def main():
    if not BOT_TOKEN:
        print("ERROR: Set BOT_TOKEN")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    for r in all_routers:
        dp.include_router(r)

    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    log.info("API started on port %s", API_PORT)

    from services.scheduler import init_scheduler
    init_scheduler(bot)

    log.info("HER ERA CRM Bot starting (Phase 2)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
