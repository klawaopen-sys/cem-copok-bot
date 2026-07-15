# =====================================================================
#                  🤖 НАЛАШТУВАННЯ СУПЕР-БОТА
# =====================================================================

# ---------------------------------------------------------------------
# 1. Загальні налаштування Google Таблиць (для трейдинг-звіту "Сім сорок")
# ---------------------------------------------------------------------
GOOGLE_SHEET_ID = '1paefPw7TChWjwMv2g1ZPgbU5Qbd4f4nuHF0tzzhpEs8'
GOOGLE_CREDENTIALS_FILE = 'klava-assistant-496912-07d33b419253.json'

# ---------------------------------------------------------------------
# 2. Налаштування Telegram Userbot (Telethon - Клава)
# ---------------------------------------------------------------------
API_ID = 37335025
API_HASH = '65354c57d6e3f7691120cf1e55b46fdc'

# ---------------------------------------------------------------------
# 3. Зовнішні API Ключі
# ---------------------------------------------------------------------
CMC_API_KEY = 'eb3f0248df7946f681f7577a96fd85b7'
GEMINI_API_KEY = 'AIzaSyDA7jVvIIh-2KRX6hYteGfkfIWzB-Fxlzc'
GEMINI_PSY_API_KEY = 'AQ.Ab8RN6KxsJ_Kz_S7_rv_-ZkaxOkVoB--_thX5rbFPPRAOTFQew' # Ключ для Психології
GEMINI_AI_API_KEY = 'AQ.Ab8RN6KAbhrlG4gogPjUi8Qm5R7XEPbLhTYsyPkDHgm-bzMPKQ'  # Ключ для ШІ
PSY_BOT_TOKEN = '6557362587:AAHmNbPuhKI9swW96m7ou4B-4fBhcuzVbdI' # Бот-психолог (@bbig333_bot)
GROQ_API_KEY = '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' # Ключ для Groq (Whisper)
GROQ_MODEL = 'whisper-large-v3-turbo' # Модель транскрибації

# Налаштування OmniRouter
import os
OMNIROUTER_BASE_URL = os.getenv("OMNIROUTER_BASE_URL", "http://localhost:20128/v1")
OMNIROUTER_API_KEY = os.getenv("OMNIROUTER_API_KEY")

# ---------------------------------------------------------------------
# 4. Проект "СІМ СОРОК" (Трейдинг & Фінанси)
# ---------------------------------------------------------------------
BOT_TOKEN = '7394557878:AAEAn_wnrNGRVDmlcG_iUwTaeM94go-te3A' # Бот-постер для трейдингу
TARGET_CHANNEL = '@cem_copok'
MORNING_POST_TIME = '07:40'
TIMEZONE = 'Europe/Kyiv'

# Реферальні посилання трейдинг-постів
REFERRAL_LINKS = {
    "Binance": "https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=ru-UA&ref=GRO_28502_BR8TC&utm_source=referral_entrance",
    "TradingView": "https://www.tradingview.com/pricing/?share_your_love=GLove_",
    "Bybit": "https://www.bybit.com/invite?ref=N8DGMD&medium=referral&utm_campaign=evergreen&share_to=link",
    "CoinMarketCap": ""
}

# Канали-донори для обіду новин трейдингу (12:00)
NEWS_DONOR_CHANNELS = [
    "cointelegraph",
    "Coin_Post",
    "incrypted",
    "Binance_UA_official",
    "kryptodohidua",
    "doubletop",
    -1001593088122
]

# Джерела RSS для автономного пошуку новин (AI-Репортер)
TRADING_REPORTER_RSS_URLS = [
    "https://cointelegraph.com/rss",
    "https://incrypted.com/feed/",
    "https://forklog.com/feed"
]

AI_REPORTER_RSS_URLS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://itc.ua/feed/",
    "https://ain.ua/feed/",
    "https://gagadget.com/uk/rss/",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://theverge.com/rss/index.xml"
]

PSY_REPORTER_RSS_URLS = [
    "https://www.psychologytoday.com/us/front/feed",
    "https://psychcentral.com/feed",
    "https://ideas.ted.com/feed/"
]

# Канали для розумного автокомментування трейдингу (Gemini) - ВИМКНЕНО
COMMENT_CHANNELS = []

# Канали для розумного автокоментування нерухомості (Gemini)
REAL_ESTATE_CHANNELS = []

# Канали для розумного автокоментування манікюру (Gemini)
MANICURE_CHANNELS = []

# Канали-донори для промо-акцій трейдингу (режим ДОНОРА для Сім сорок) - ВИМКНЕНО
TRADING_DONOR_CHANNELS = []

# ---------------------------------------------------------------------
# 5. Проект "НЕЙРО-АПГРЕЙД" (Психологія)
# ---------------------------------------------------------------------
PSY_TARGET_CHANNEL = '@ncux_olo_guY'

# Канали-донори з психології (додавайте свої юзернейми сюди!)
PSY_DONOR_CHANNELS = [
    'psy_people',                # Практична психологія стосунків
    'Psikhologiaz',              # Психология | Психосоматика
    'Psychologs',                # Психология отношений
    'notburningout',             # Чтобы не выгорать
    'TheMentalHealthSchool',     # Школа психологического просвещения
    'post_trevoga',              # пост_тревога
    'Psihologiya_samorazvitie',  # Психология саморазвитие
    'volna_cc',                 # Море волнуется, а ты — нет
         
]

# Тайм-слоти для публікацій Психології (Нейро-Апгрейд)
# ВАЖЛИВО: слоти навмисно розведені в часі з трейдингом та щоденною прокачкою!
# noon_job (трейдинг) о 14:00 → PSY_SLOT_2 зсунуто на 13:30
# daily_upgrade о 19:00 → PSY_SLOT_3 зсунуто на 19:30
PSY_SLOT_1_TIME = '08:30'  # Morning Motivation (Мотивація та натхнення)
PSY_SLOT_2_TIME = '13:30'  # Practical Psychology — НЕ 14:00 (конфлікт з трейдингом)
PSY_SLOT_3_TIME = '19:30'  # Mindfulness & Relationships — НЕ 19:00 (конфлікт з прокачкою)

# Сигнатура з посиланням на психолога в кінці постів психології
PSY_SIGNATURE = "\n\n🌿 <b>Твій особистий ШІ-Психолог —  24/7👇</b>"

# ---------------------------------------------------------------------
# 6. Проект "ТЕ ЩО ТРЕБА" (Штучний Інтелект / AI)
# ---------------------------------------------------------------------
AI_TARGET_CHANNEL = '@te_shoo_treba'

# Тайм-слоти для публікацій ІИ (скорочено до 3-х постів на день)
AI_SLOT_1_TIME = '10:00'  # AI News & Web3 Tech
AI_SLOT_2_TIME = '15:00'  # AI Productivity & Work
AI_SLOT_3_TIME = '20:00'  # AI Media & Creative

# Канали-донори по ІИ та технологіях (додавайте свої юзернейми сюди!)
AI_DONOR_CHANNELS = [
    'prompt_hub',
    'ai_tools',
    'AI_to_business',
    'TochkiNadAI',
    'hiaimedia',
    'ai_newz',
    'DeepTechNET',
    'misha_davai_po_novoi',
    'neuro_channel',
    -1002546853359  # ID приватного каналу 'Никита Велс | AI'
]

# Сигнатура з посиланням на бібліотекаря в кінці постів ІИ
AI_SIGNATURE = "\n\n🎙️ <b>Отримати безкоштовний голосовий віджет👇</b>"

# ---------------------------------------------------------------------
# 7. Проект "БОТ-БІБЛІОТЕКАР" (@librar_ian_bot)
# ---------------------------------------------------------------------
LIBRARIAN_BOT_TOKEN = '7256816649:AAEM2RdvGCkDjycNZemp3oeM0DyqqA-5IDo'
LIBRARY_CHANNEL = 'https://t.me/l_ibrar_y'

# Канали, на які користувач повинен підписатися для доступу до книг
REQUIRED_CHANNELS = {
    '@cem_copok': '📢 Сім сорок | Трейдинг',
    '@ncux_olo_guY': '🧠 Психологія',
    '@te_shoo_treba': '🤖 Те що треба | AI'
}

# ---------------------------------------------------------------------
# 8. Налаштування нових рубрик
# ---------------------------------------------------------------------
DAILY_UPGRADE_POST_TIME = '19:00'
DAILY_UPGRADE_IMAGE = '.tmp/daily_upgrade.jpg'
FOCUS_POST_TIME = '12:00'
FOCUS_IMAGE = '.tmp/focus_default.jpg'

