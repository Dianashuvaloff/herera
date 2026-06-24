WELCOME_NEW = (
    "Привіт, {name}! 💗\n\n"
    "Ласкаво просимо до <b>HER ERA</b> — закритий клуб жіночих вечорів у Києві.\n\n"
    "Твій персональний реферальний код:\n"
    "🎟 <code>{refcode}</code>\n\n"
    "Поділись ним з подругою — вона отримає знижку 10%, а ти +50 балів!\n\n"
    "{next_event}"
)

WELCOME_BACK = (
    "З поверненням, {name}! 💗\n\n"
    "💰 {available} балів · {status}\n\n"
    "{next_event}"
)

NEXT_EVENT_BLOCK = (
    "🔥 <b>Найближчий вечір:</b>\n"
    "{emoji} <b>{event_name}</b>\n"
    "📅 {event_date} о {event_time}\n"
    "📍 {event_location}\n"
    "⏰ Через {days_left} дн."
)

NEXT_EVENT_EMPTY = ""

BALANCE = (
    "💰 <b>Твій баланс</b>\n\n"
    "Total балів: <b>{total}</b>\n"
    "Available: <b>{available}</b>\n"
    "Статус: <b>{status}</b>\n\n"
    "{extra}"
)

BALANCE_EXTRA_FREE = "🎁 У тебе достатньо балів для безкоштовного квитка! Натисни /redeem"
BALANCE_EXTRA_PROGRESS = "До безкоштовного квитка: ще {until_free} балів"

REFCODE = (
    "🎟 Твій реферальний код:\n\n"
    "<code>{refcode}</code>\n\n"
    "Що він дає:\n"
    "• Подрузі — знижка 10% на перший вечір\n"
    "• Тобі — +50 балів за кожну нову подругу"
)

SHARECODE = (
    "Хей! 💗\n\n"
    "Запрошую тебе на закритий жіночий вечір <b>HER ERA</b> у Києві — "
    "знайомства, фотосесія, шампанське, нетворкінг.\n\n"
    "{next_event_short}\n\n"
    "Мій промокод на знижку <b>10%</b>:\n"
    "🎟 <code>{refcode}</code>\n\n"
    "Пиши сюди → @herera_crm_bot\n"
    "Просто натисни Start і введи мій код 💗"
)

SHARECODE_EVENT_LINE = "🔥 Найближчий: <b>{name}</b> — {date}, {location}"
SHARECODE_NO_EVENT = "Слідкуй за розкладом вечорів у боті!"

MYCARD = (
    "┌───────────────────────────┐\n"
    "│       🖤 <b>HER ERA CARD</b>       │\n"
    "│                                              │\n"
    "│  👤 {name}\n"
    "│  {status_emoji} Статус: <b>{status}</b>\n"
    "│  💰 <b>{total}</b> балів\n"
    "│  🔥 <b>{events_count}</b> вечорів\n"
    "│  📅 з {member_since}\n"
    "│                                              │\n"
    "│  🎟 <code>{refcode}</code>\n"
    "│  👯 Привела: <b>{refs_count}</b> подруг\n"
    "└───────────────────────────┘"
)

STATUS_EMOJI = {
    "Гостя": "🤍",
    "HER ERA Girl": "💜",
    "ERA Regular": "💎",
    "ERA VIP": "👑",
}

MYREFS_HEADER = "👯 <b>Подруги які прийшли по твоєму коду:</b>\n\n"
MYREFS_EMPTY = "Поки ніхто не скористався твоїм кодом.\nПоділись ним — натисни 📨 нижче 💗"
MYREFS_ITEM = "• {name}\n"

EVENTS_HEADER = "📅 <b>Найближчі вечори HER ERA:</b>\n\n"
EVENTS_EMPTY = "Найближчих івентів поки немає. Слідкуй за оновленнями! 💗"
EVENTS_ITEM = (
    "{emoji} <b>{name}</b>\n"
    "📅 {date} о {time}\n"
    "📍 {location}\n"
    "👥 Місць: {max_spots}\n\n"
)

HOWTOVIP = (
    "🏆 <b>Як отримати статус?</b>\n\n"
    "Збирай бали за активність:\n\n"
    "🎉 Прийшла на вечір — <b>+100</b>\n"
    "👯 Привела подругу — <b>+50</b> (обом!)\n"
    "📸 Відмітила в сторіс — <b>+25</b>\n"
    "🎂 День народження у нас — <b>+200</b>\n\n"
    "Статуси:\n"
    "• 0-499 балів — 🤍 Гостя\n"
    "• 500-999 балів — 💜 <b>HER ERA Girl</b> (пріоритетний доступ)\n"
    "• 1000-1999 балів — 💎 <b>ERA Regular</b> (знижка 200 грн)\n"
    "• 2000+ балів — 👑 <b>ERA VIP</b> (безкоштовний вечір раз на сезон)\n\n"
    "🎁 1000 Available балів = безкоштовний квиток!"
)

REDEEM_OK = (
    "🎁 <b>Квиток активовано!</b>\n\n"
    "З твого балансу списано 1000 балів.\n"
    "Напиши @dianashuvaloff щоб забронювати місце на найближчий вечір 💗"
)

REDEEM_NOT_ENOUGH = (
    "Недостатньо балів 😔\n\n"
    "Зараз: {available} Available балів\n"
    "Потрібно: 1000\n\n"
    "Збирай бали — /howtovip"
)

INFO = (
    "🖤 <b>HER ERA</b> — закритий клуб жіночих вечорів у Києві.\n\n"
    "Знайомства, фотосесія, шампанське, нетворкінг, покер, тематичні вечори.\n\n"
    'Instagram: <a href="https://instagram.com/her.era.kyiv">@her.era.kyiv</a>\n'
    "Telegram: @dianashuvaloff"
)

CONTACT = (
    "📩 Зв'язок з організатором:\n\n"
    "Telegram: @dianashuvaloff\n"
    'Instagram: <a href="https://instagram.com/her.era.kyiv">@her.era.kyiv</a>'
)

HELP = (
    "🖤 <b>HER ERA — Команди:</b>\n\n"
    "/balance — мій баланс і статус\n"
    "/mycard — моя картка учасниці\n"
    "/refcode — мій реферальний код\n"
    "/sharecode — переслати код подрузі\n"
    "/myrefs — хто прийшов по моєму коду\n"
    "/events — найближчі вечори\n"
    "/howtovip — як отримати статус\n"
    "/redeem — обміняти бали на квиток\n"
    "/matches — мої матчі з вечорів\n"
    "/info — про HER ERA\n"
    "/contact — зв'язок з організатором"
)

NOT_REGISTERED = (
    "Ти ще не зареєстрована 💗\n"
    "Натисни /start щоб почати!"
)

ADMIN_NEW_REG = (
    "🆕 <b>Нова реєстрація</b>\n\n"
    "Імʼя: {name}\n"
    "Telegram: @{username}\n"
    "Реф-код: <code>{refcode}</code>"
)

# --- Reminders ---

REMINDER_BEFORE_EVENT = (
    "Привіт, {name}! 💗\n\n"
    "Нагадуємо — вже скоро твій вечір <b>HER ERA</b>!\n\n"
    "{emoji} <b>{event_name}</b>\n"
    "📅 {event_date} о {event_time}\n"
    "📍 {event_location}\n\n"
    "{payment_note}"
    "Чекаємо на тебе! 🖤"
)

REMINDER_PAYMENT_NOTE = "💰 Залишок до оплати: <b>{remaining} грн</b>\n\n"

REMINDER_DAY_OF_UNPAID = (
    "Привіт, {name}! 💗\n\n"
    "Сьогодні твій вечір <b>HER ERA</b>!\n\n"
    "💰 В тебе ще залишок: <b>{remaining} грн</b>\n"
    "Будь ласка, оплати до початку вечора 🙏\n\n"
    "Чекаємо! 🖤"
)

REMINDER_4H_BEFORE = (
    "До зустрічі через кілька годин! 💗\n\n"
    "{emoji} <b>{event_name}</b>\n"
    "📍 {event_location}\n"
    "👗 Дрес-код: {dress_code}\n\n"
    "{reels_note}"
    "Чекаємо на тебе! 🖤"
)

REMINDER_REELS_NOTE = '🎬 Як доїхати: <a href="{reels_link}">дивись тут</a>\n\n'

REMINDER_POST_EVENT = (
    "Дякуємо за чудовий вечір, {name}! 💗\n\n"
    "Маємо для тебе подарунок — <b>знижка 10%</b> на наступний вечір!\n\n"
    '💬 Напиши нам в <a href="{dm_link}">Директ</a> щоб забронювати 🖤'
)

# --- Points post-event ---

POINTS_POST_EVENT = (
    "💰 <b>Твої бали після вечора</b>\n\n"
    "Зараз: <b>{available}</b> балів\n"
    "Статус: {status_emoji} <b>{status}</b>\n\n"
    "{next_perk_text}"
    "{story_tag_text}"
    "{free_ticket_text}"
)

POINTS_NEXT_PERK = "🎯 До <b>{next_status}</b>: ще {points_left} балів ({perk})\n\n"
POINTS_ALREADY_MAX = "🎯 Ти вже на максимальному рівні — <b>ERA VIP</b> 👑\n\n"

POINTS_STORY_TAG = "📸 Відмітила нас в сторіс? Натисни кнопку нижче — отримаєш <b>+25 балів</b>!\n\n"
POINTS_STORY_ALREADY = "📸 Бали за сторіс вже нараховані для цього вечора ✅\n\n"

POINTS_FREE_TICKET = "🎁 До безкоштовного квитка: ще <b>{events_left}</b> оплачених вечорів\n"

# --- Matches ---

MATCHES_SELECT_EVENT = "💗 <b>Мої матчі</b>\n\nОбери вечір щоб побачити матчі:"

MATCHES_EMPTY = "На цьому вечорі поки немає взаємних матчів 😔"

MATCHES_NO_EVENTS = "Поки немає вечорів з матчами. Приходь на наступний вечір! 💗"

MATCH_CARD = (
    "💗 <b>{name}</b>, {age}\n"
    "💼 {occupation}\n"
    "🎯 {hobbies}\n\n"
    "✨ Збіглось: {match_reasons}\n\n"
    "{socials}"
)

MATCH_SOCIALS = (
    "{instagram_line}"
    "{tiktok_line}"
    "{telegram_line}"
)

# --- Broadcasts ---

BROADCAST_SELECT_EVENT = "📢 Обери івент для розсилки:"
BROADCAST_SELECT_AUDIENCE = "📢 Обери аудиторію:"
BROADCAST_ENTER_TEXT = "✏️ Введи текст розсилки:"
BROADCAST_CONFIRM = (
    "📢 <b>Підтвердження розсилки</b>\n\n"
    "Аудиторія: {audience}\n"
    "Отримувачів: {count}\n\n"
    "Текст:\n{text}\n\n"
    "Надіслати?"
)
BROADCAST_DONE = "✅ Розсилку надіслано: {sent}/{total} отримувачів"

# --- Admin ---

ADMIN_PANEL = (
    "🔧 <b>Адмін-панель HER ERA</b>\n\n"
    "Обери дію:"
)

BLANK_SEND_PHOTO = "📋 Надішли фото заповненого бланку гості"
BLANK_SELECT_EVENT = "📋 Для якого вечора цей бланк?"
BLANK_CONFIRM = (
    "📋 <b>Розпізнані дані:</b>\n\n"
    "👤 {name}, {age}\n"
    "💼 {occupation}\n"
    "🎯 {hobbies}\n"
    "✅ Краща риса: {best_trait}\n"
    "❌ Найгірша: {worst_trait}\n\n"
    "🔍 Шукає: {seeking}\n\n"
    "📊 Матч-сітка: {match_count} відміток\n\n"
    "Зберегти?"
)
BLANK_SAVED = "✅ Дані збережено для <b>{name}</b>"
BLANK_NOT_FOUND = "❌ Не вдалось знайти гостю в таблиці. Перевір імʼя та номер."
BLANK_ERROR = "❌ Помилка розпізнавання. Спробуй ще раз або завантаж чіткіше фото."
