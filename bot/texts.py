WELCOME_NEW = (
    "Привіт, {name}! 💗\n\n"
    "Ласкаво просимо до <b>HER ERA</b> — закритий клуб жіночих вечорів у Києві.\n\n"
    "Твій персональний реферальний код:\n"
    "🎟 <code>{refcode}</code>\n\n"
    "Поділись ним з подругою — вона отримає знижку 10%, а ти +100 балів!\n\n"
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
    "• Тобі — +100 балів за кожну нову подругу"
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
    "Постійна": "💜",
    "VIP": "👑",
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
    "🏆 <b>Як стати VIP?</b>\n\n"
    "Збирай бали за активність:\n\n"
    "🎉 Прийшла на вечір — <b>+50</b>\n"
    "👯 Привела нову подругу — <b>+100</b>\n"
    "🔄 Привела повторно — <b>+30</b>\n"
    "📸 Сторіс з міткою — <b>+30</b>\n"
    "✍️ Залишила відгук — <b>+20</b>\n"
    "🎂 День народження — <b>+200</b>\n"
    "🎟 Використала чийсь код — <b>+50</b>\n\n"
    "Статуси:\n"
    "• 0-499 балів — 🤍 Гостя\n"
    "• 500-1999 балів — 💜 Постійна\n"
    "• 2000+ балів — 👑 <b>VIP</b>\n\n"
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
    "Instagram: @her.era.kyiv\n"
    "Telegram: @dianashuvaloff"
)

CONTACT = (
    "📩 Зв'язок з організатором:\n\n"
    "Telegram: @dianashuvaloff\n"
    "Instagram: @her.era.kyiv"
)

HELP = (
    "🖤 <b>HER ERA — Команди:</b>\n\n"
    "/balance — мій баланс і статус\n"
    "/mycard — моя картка учасниці\n"
    "/refcode — мій реферальний код\n"
    "/sharecode — переслати код подрузі\n"
    "/myrefs — хто прийшов по моєму коду\n"
    "/events — найближчі вечори\n"
    "/howtovip — як стати VIP\n"
    "/redeem — обміняти бали на квиток\n"
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
