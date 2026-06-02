import schedule
import time
import asyncio
import threading
import os
import re
from telethon import TelegramClient
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Імпорт логіки публікацій
from poster import run_poster
from news_poster import run_news_poster, run_ai_news_poster, run_psy_news_poster, run_weekly_digest, fill_daily_queue, run_image_control_check
from commenter import register_commenter
import config

# Ініціалізація юзербота Telethon (Клава)
client = TelegramClient('klava', config.API_ID, config.API_HASH)
main_loop = None

# Ініціалізація бота-бібліотекаря Aiogram
bot = Bot(token=config.LIBRARIAN_BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Ініціалізація окремого бота-психолога Aiogram (@bbig333_bot)
psy_bot = Bot(token=config.PSY_BOT_TOKEN)
psy_dp = Dispatcher()
psy_router = Router()
psy_dp.include_router(psy_router)

from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_psy_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Розпочати діалог", callback_data="start_psy_chat_from_menu")
    builder.button(text="🧠 Канал Психологія", url="https://t.me/ncux_olo_guY")
    builder.adjust(1)
    return builder.as_markup()

def get_psy_back_to_channel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🧠 Перейти до каналу Психологія", url="https://t.me/ncux_olo_guY")
    builder.button(text="🔄 Розпочати новий діалог", callback_data="start_psy_chat_from_menu")
    builder.adjust(1)
    return builder.as_markup()

class PsyChatStates(StatesGroup):
    in_chat = State()

async def check_psy_subscription(user_id: int) -> bool:
    try:
        member = await psy_bot.get_chat_member(chat_id='@ncux_olo_guY', user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ Помилка перевірки підписки на психологію: {e}")
        return False

def get_psy_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Підписатися на Психологію", url="https://t.me/ncux_olo_guY")
    builder.button(text="🔄 Перевірити підписку", callback_data="check_psy_chat")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------
# А. Логіка Бота-Бібліотекаря (Subscription Gate & Telegram Stars)
# ---------------------------------------------------------------------
async def check_subscriptions(user_id: int) -> list:
    """Перевіряє підписку користувача на обов'язкові канали. Повертає список непідписаних."""
    unsubscribed = []
    for channel, name in config.REQUIRED_CHANNELS.items():
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed.append(channel)
        except Exception as e:
            print(f"⚠️ Помилка перевірки підписки для {channel}: {e}")
            unsubscribed.append(channel)
    return unsubscribed

def get_subscription_keyboard(unsubscribed, file_key):
    """Створює меню з кнопками підписки та кнопками перевірки/оплати"""
    builder = InlineKeyboardBuilder()
    for channel in unsubscribed:
        name = config.REQUIRED_CHANNELS.get(channel, channel)
        url = f"https://t.me/{channel.replace('@', '')}"
        builder.button(text=f"📌 Підписатися на {name.split('|')[1].strip() if '|' in name else name}", url=url)
    builder.button(text="🔄 Перевірити підписку", callback_data=f"check_{file_key}")
    builder.button(text="⭐️ Забрати за 1 Зірку (без підписки)", callback_data=f"pay_{file_key}")
    builder.adjust(1)
    return builder.as_markup()

async def deliver_file_or_lock(message: Message, file_key: str, is_callback: bool = False):
    """Перевіряє підписку та копіює потрібне повідомлення/книгу з каналу-бібліотеки @l_ibrar_y"""
    user_chat_id = message.chat.id
    user_id = message.from_user.id
    
    unsubscribed = await check_subscriptions(user_id)
    
    # Витягуємо номер ID повідомлення з ключа
    match = re.search(r'\d+', file_key)
    if not match:
        error_text = "❌ <b>Помилка:</b> Посилання не містить правильного ідентифікатора книги."
        if is_callback: await message.edit_text(error_text, parse_mode="HTML")
        else: await message.answer(error_text, parse_mode="HTML")
        return
        
    message_id = int(match.group(0))
    
    if not unsubscribed:
        # Успішно підписаний на всі канали!
        loading_msg = None
        if is_callback: await message.edit_text("⏳ Перевірка успішна! Завантажую книгу з бібліотеки...")
        else: loading_msg = await message.answer("⏳ Перевірка успішна! Завантажую книгу з бібліотеки...")
            
        try:
            # Копіюємо повідомлення з каналу-бібліотеки прямо в чат користувачу
            await bot.copy_message(
                chat_id=user_chat_id,
                from_chat_id='@l_ibrar_y',
                message_id=message_id
            )
            if is_callback: await message.delete()
            elif loading_msg: await loading_msg.delete()
        except Exception as e:
            error_text = (
                f"❌ <b>Помилка завантаження книги!</b>\n\n"
                f"Бот не зміг знайти або скопіювати повідомлення з ID <code>{message_id}</code> з каналу <b>@l_ibrar_y</b>.\n\n"
                f"<i>👉 Переконайтеся, що пост {message_id} існує в каналі @l_ibrar_y і бот доданий туди як адміністратор!</i>"
            )
            if is_callback: await message.edit_text(error_text, parse_mode="HTML")
            else:
                if loading_msg: await loading_msg.delete()
                await message.answer(error_text, parse_mode="HTML")
    else:
        # Користувач не підписаний на всі канали
        lock_text = (
            "🔒 <b>Доступ обмежено!</b>\n\n"
            "Щоб безкоштовно розблокувати цей файл, тобі потрібно підписатися на наші корисні канали.\n\n"
            "Будь ласка, підпишись на канали нижче та натисни кнопку перевірки підписки:"
        )
        if is_callback:
            await message.edit_text(lock_text, reply_markup=get_subscription_keyboard(unsubscribed, file_key), parse_mode="HTML")
        else:
            await message.answer(lock_text, reply_markup=get_subscription_keyboard(unsubscribed, file_key), parse_mode="HTML")

@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    file_key = command.args
    if file_key:
        await deliver_file_or_lock(message, file_key.strip())
    else:
        welcome_text = (
            "<b>Привіт! Я твій особистий Бібліотекар 📚</b>\n\n"
            "Я видаю корисні книги, чек-листи та ШІ-промпти за підписку на наші канали!\n\n"
            "Перейдіть у наші канали, щоб знайти посилання на завантаження потрібних матеріалів:\n"
            "📢 @cem_copok (Трейдинг)\n"
            "🧠 @ncux_olo_guY (Психологія)\n"
            "🤖 @te_shoo_treba (AI)"
        )
        await message.answer(welcome_text, parse_mode="HTML")

# --- Обробники для окремого бота-психолога (@bbig333_bot) ---

@psy_router.message(Command("start"))
async def cmd_psy_start(message: Message, state: FSMContext):
    # Очищуємо старий стан та показуємо чисте головне меню
    await state.clear()
    welcome_msg = (
        "🌿 <b>Вітаю у просторі психологічної підтримки!</b>\n\n"
        "Я — твій особистий ШІ-Психотерапевт. Тут ти можеш поділитися своїми переживаннями, "
        "знайти підтримку або просто виговоритись у конфіденційному форматі.\n\n"
        "Оберіть дію нижче 👇"
    )
    await message.answer(
        welcome_msg, 
        reply_markup=get_psy_main_keyboard(), 
        parse_mode="HTML"
    )

@psy_router.callback_query(F.data == "start_psy_chat_from_menu")
async def handle_start_psy_chat_callback(query: CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    is_subbed = await check_psy_subscription(user_id)
    if not is_subbed:
        await query.message.answer(
            "❌ <b>Тільки для підписників нашого каналу Психологія!</b>\n\n"
            "Будь ласка, підпишись на наш канал та натисни кнопку перевірки нижче, щоб розпочати діалог з ШІ-психологом:",
            reply_markup=get_psy_subscription_keyboard(),
            parse_mode="HTML"
        )
        await query.answer()
        return
        
    await query.message.delete()
    await state.clear()
    await state.set_state(PsyChatStates.in_chat)
    await state.update_data(history=[])
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb_builder = ReplyKeyboardBuilder()
    kb_builder.button(text="❌ Завершити діалог")
    
    await query.message.answer(
        "🧠 <b>Вітаю! Я твій особистий ШІ-Психолог.</b>\n\n"
        "Я тут, щоб вислухати тебе, підтримати та допомогти розібратися в емоціях у безпечному й абсолютно конфіденційному просторі.\n\n"
        "<i>Напиши, будь ласка, як я можу до тебе звертатися? Як твоє ім'я? 😊</i>\n\n"
        "<i>👉 Натисни кнопку нижче в будь-який момент, щоб завершити діалог.</i>",
        reply_markup=kb_builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )
    await query.answer()

@psy_router.callback_query(F.data == "check_psy_chat")
async def handle_check_psy_chat_subscription(query: CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    is_subbed = await check_psy_subscription(user_id)
    if not is_subbed:
        await query.answer("❌ Ти ще не підписався на канал Психологія!", show_alert=True)
        return
        
    await query.message.delete()
    await state.clear()
    await state.set_state(PsyChatStates.in_chat)
    await state.update_data(history=[])
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb_builder = ReplyKeyboardBuilder()
    kb_builder.button(text="❌ Завершити діалог")
    
    await query.message.answer(
        "🧠 <b>Вітаю! Я твій особистий ШІ-Психолог.</b>\n\n"
        "Я тут, щоб вислухати тебе, підтримати та допомогти розібратися в емоціях у безпечному й абсолютно конфіденційному просторі.\n\n"
        "<i>Напиши, будь ласка, як я можу до тебе звертатися? Як твоє ім'я? 😊</i>\n\n"
        "<i>👉 Натисни кнопку нижче в будь-який момент, щоб завершити діалог.</i>",
        reply_markup=kb_builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )
    await query.answer()

@router.callback_query(F.data.startswith("check_"))
async def handle_check_subscription(query: CallbackQuery):
    file_key = query.data.replace("check_", "")
    await deliver_file_or_lock(query.message, file_key, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("pay_"))
async def handle_pay_with_stars(query: CallbackQuery):
    file_key = query.data.replace("pay_", "")
    user_chat_id = query.message.chat.id
    match = re.search(r'\d+', file_key)
    if not match:
        await query.answer("❌ Помилка: неправильний ID файлу.", show_alert=True)
        return
        
    message_id = int(match.group(0))
    try:
        await bot.send_invoice(
            chat_id=user_chat_id,
            title="Швидкий доступ до книги",
            description=f"Отримати файл з ID {message_id} без обов'язкової підписки за 1 Зірку",
            payload=f"stars_{message_id}",
            provider_token="",  # Порожній токен для Telegram Stars!
            currency="XTR",
            prices=[LabeledPrice(label="Telegram Stars", amount=1)]
        )
        await query.answer()
    except Exception as e:
        await query.message.answer(f"❌ Не вдалося виставити рахунок: {e}")
        await query.answer()

@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    match = re.search(r'\d+', payload)
    if not match:
        await message.answer("❌ Помилка обробки оплати.")
        return
        
    message_id = int(match.group(0))
    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id='@l_ibrar_y',
            message_id=message_id
        )
        await message.answer("🎉 <b>Дякуємо за підтримку зірками! Твій файл успішно завантажено. Приємного читання!</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(
            f"❌ <b>Оплата пройшла успішно, але сталася помилка доставки файлу!</b>\n\n"
            f"Бот не зміг скопіювати повідомлення з ID {message_id} з каналу @l_ibrar_y.\n"
            f"<i>Будь ласка, зверніться до адміністратора.</i>",
            parse_mode="HTML"
        )

# --- Обработчики ШІ-Психолога ---

@psy_router.message(PsyChatStates.in_chat, F.text == "❌ Завершити діалог")
async def cmd_stop_chat(message: Message, state: FSMContext):
    await state.clear()
    from aiogram.types import ReplyKeyboardRemove
    
    await message.answer(
        "🧠 <b>Діалог завершено. Сподіваюсь, наша розмова була корисною для тебе!</b>\n\n"
        "Я завжди тут, коли тобі знадобиться підтримка або захочеться виговоритись.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    
    await message.answer(
        "🌿 Оберіть дію нижче для переходу до каналу або старту нового діалогу:",
        reply_markup=get_psy_back_to_channel_keyboard(),
        parse_mode="HTML"
    )

@psy_router.message(PsyChatStates.in_chat, F.text)
async def handle_psychologist_chat(message: Message, state: FSMContext):
    user_message = message.text.strip()
    
    state_data = await state.get_data()
    history = state_data.get("history", [])
    
    await psy_bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    system_prompt = (
        "Ти — професійний, емпатичний та теплий практичний психотерапевт. "
        "Твоя мета — вислухати користувача, підтримати його, допомогти проаналізувати свої емоції та знизити рівень стресу. "
        "Пиши виключно українською мовою. Спілкуйся м'яко, не давай сухих шаблонних відповідей робота. "
        "Став відкриті запитання, використовуй активне слухання. Заборонено ставити діагнози чи виписувати ліки. "
        "Якщо людина говорить про self-harm або критичну депресію, вислови максимальну турботу та м'яко запропонуй контакти служб підтримки."
    )
    
    import requests
    
    api_key = getattr(config, 'GEMINI_PSY_API_KEY', config.GEMINI_API_KEY)
    if not api_key or api_key.startswith('AQ.'):
        api_key = config.GEMINI_API_KEY
        
    if not api_key:
        await message.answer("⚠️ Помилка конфігурації: API-ключ не знайдено.")
        return
        
    history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    
    if len(history) > 12:
        history = history[-12:]
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": history,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            ai_reply = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            history.append({
                "role": "model",
                "parts": [{"text": ai_reply}]
            })
            await state.update_data(history=history)
            await message.answer(ai_reply, parse_mode="HTML")
        else:
            print(f"Gemini API Error in Psy Chat: {r.status_code} - {r.text}")
            await message.answer("🧠 Я почув тебе і глибоко задумався над твоїми словами... Спробуй, будь ласка, написати ще раз трохи пізніше.")
    except Exception as e:
        print(f"Exception in Psy Chat Gemini call: {e}")
        await message.answer("🧠 Я почув тебе і глибоко задумався над твоїми словами... Спробуй, будь ласка, написати ще раз трохи пізніше.")

@psy_router.message(PsyChatStates.in_chat, F.voice)
async def handle_psychologist_voice(message: Message, state: FSMContext):
    await psy_bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # 1. Завантаження голосового повідомлення
    destination = f"voice_{message.from_user.id}.ogg"
    try:
        file_id = message.voice.file_id
        file = await psy_bot.get_file(file_id)
        await psy_bot.download_file(file.file_path, destination)
    except Exception as e:
        print(f"❌ Failed to download voice message: {e}")
        await message.answer("⚠️ Не вдалося завантажити голосове повідомлення. Спробуйте надіслати текстове.")
        return
        
    # 2. Транскрибація голосового через Groq (Whisper)
    import requests
    
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}"
    }
    
    transcribed_text = ""
    try:
        with open(destination, "rb") as f:
            files = {
                "file": (os.path.basename(destination), f, "audio/ogg")
            }
            data = {
                "model": config.GROQ_MODEL,
                "language": "uk"
            }
            r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            if r.status_code == 200:
                transcribed_text = r.json().get("text", "").strip()
            else:
                print(f"❌ Groq Transcription API Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Exception during Groq transcription: {e}")
    finally:
        # Очищення тимчасового файлу
        if os.path.exists(destination):
            try: os.remove(destination)
            except Exception: pass
            
    if not transcribed_text:
        await message.answer("🧠 Вибачте, мені не вдалося розпізнати ваше голосове повідомлення. Спробуйте записати чіткіше або написати текстом.")
        return
        
    # 3. Обробка розпізнаного тексту як звичайного повідомлення психологу
    state_data = await state.get_data()
    history = state_data.get("history", [])
    
    system_prompt = (
        "Ти — професійний, емпатичний та теплий практичний психотерапевт. "
        "Твоя мета — вислухати користувача, підтримати його, допомогти проаналізувати свої емоції та знизити рівень стресу. "
        "Пиши виключно українською мовою. Спілкуйся м'яко, не давай сухих шаблонних відповідей робота. "
        "Став відкриті запитання, використовуй активне слухання. Заборонено ставити діагнози чи виписувати ліки. "
        "Обов'язково зверни увагу на те, як користувач представився. Надалі завжди звертайся до нього по імені. "
        "УНИКАЙ незграбних гендерних закінчень через сліш (наприклад, 'звернувся/лася', 'почув/ла'). "
        "Пиши так, щоб це виглядало гарно, природно та професійно, підлаштовуючи закінчення під гендер користувача, якщо він зрозумілий, або використовуючи нейтральні конструкції. "
        "Якщо людина говорить про self-harm або критичну депресію, вислови максимальну турботу та м'яко запропонуй контакти служб підтримки."
    )
    
    api_key = getattr(config, 'GEMINI_PSY_API_KEY', config.GEMINI_API_KEY)
    if not api_key or api_key.startswith('AQ.'):
        api_key = config.GEMINI_API_KEY
        
    history.append({
        "role": "user",
        "parts": [{"text": transcribed_text}]
    })
    
    if len(history) > 12:
        history = history[-12:]
        
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    gemini_headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": history,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }
    
    try:
        r = requests.post(gemini_url, headers=gemini_headers, json=payload, timeout=30)
        if r.status_code == 200:
            ai_reply = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            history.append({
                "role": "model",
                "parts": [{"text": ai_reply}]
            })
            await state.update_data(history=history)
            
            await message.answer(ai_reply, parse_mode="HTML")
        else:
            print(f"Gemini API Error in Psy Chat Voice: {r.status_code} - {r.text}")
            await message.answer("🧠 Я почув тебе і глибоко задумався над твоїми словами... Спробуй, будь ласка, написати або записати ще раз трохи пізніше.")
    except Exception as e:
        print(f"Exception in Psy Chat Voice Gemini call: {e}")
        await message.answer("🧠 Я почув тебе і глибоко задумався над твоїми словами... Спробуй, будь ласка, написати або записати ще раз трохи пізніше.")


# ---------------------------------------------------------------------
# Б. Логіка Планувальника Публікацій (Трейдинг та ШІ)
# ---------------------------------------------------------------------
def morning_job():
    print(f"⏰ Час {config.MORNING_POST_TIME}! Запускаю ранковий фінансовий огляд...")
    try: run_poster()
    except Exception as e: print(f"Помилка ранкового поста: {e}")

def noon_job():
    print("⏰ Час 12:00! Запускаю денний огляд новин трейдингу...")
    try:
        if main_loop and client: run_news_poster(client, main_loop)
    except Exception as e: print(f"Помилка денного поста трейдингу: {e}")

def ai_job_slot_1():
    print("⏰ Час SLOT 1 (09:00)! Запускаю AI News & Web3 Tech...")
    try:
        if main_loop and client: run_ai_news_poster(client, main_loop, "AI News & Web3 Tech")
    except Exception as e: print(f"Помилка в SLOT 1: {e}")

def ai_job_slot_2():
    print("⏰ Час SLOT 2 (13:00)! Запускаю AI Productivity & Work...")
    try:
        if main_loop and client: run_ai_news_poster(client, main_loop, "AI Productivity & Work")
    except Exception as e: print(f"Помилка в SLOT 2: {e}")

def ai_job_slot_3():
    print("⏰ Час SLOT 3 (17:00)! Запускаю AI Finance & Dev Tools...")
    try:
        if main_loop and client: run_ai_news_poster(client, main_loop, "AI Finance & Dev Tools")
    except Exception as e: print(f"Помилка в SLOT 3: {e}")

def ai_job_slot_4():
    print("⏰ Час SLOT 4 (21:00)! Запускаю AI Media & Creative...")
    try:
        if main_loop and client: run_ai_news_poster(client, main_loop, "AI Media & Creative")
    except Exception as e: print(f"Помилка в SLOT 4: {e}")

def psy_job_slot_1():
    print("⏰ Час PSY SLOT 1 (09:00)! Запускаю Morning Motivation...")
    try:
        if main_loop and client: run_psy_news_poster(client, main_loop, "Morning Motivation")
    except Exception as e: print(f"Помилка в PSY SLOT 1: {e}")

def psy_job_slot_2():
    print("⏰ Час PSY SLOT 2 (14:00)! Запускаю Practical Psychology...")
    try:
        if main_loop and client: run_psy_news_poster(client, main_loop, "Practical Psychology")
    except Exception as e: print(f"Помилка в PSY SLOT 2: {e}")

def psy_job_slot_3():
    print("⏰ Час PSY SLOT 3 (19:00)! Запускаю Mindfulness & Relationships...")
    try:
        if main_loop and client: run_psy_news_poster(client, main_loop, "Mindfulness & Relationships")
    except Exception as e: print(f"Помилка в PSY SLOT 3: {e}")

def weekly_digest_job():
    print("⏰ Час 14:00 (Неділя)! Запускаю тижневий дайджест...")
    try:
        if main_loop and client: run_weekly_digest(client, main_loop)
    except Exception as e: print(f"Помилка тижневого дайджесту: {e}")

def daily_queue_job_ai():
    print("⏰ Час 03:00! Запускаю нічну підготовку контенту для ШІ...")
    try:
        if main_loop and client:
            asyncio.run_coroutine_threadsafe(fill_daily_queue(client, "ai"), main_loop)
    except Exception as e: print(f"Помилка нічної підготовки черги ШІ: {e}")

def daily_queue_job_psy():
    print("⏰ Час 04:00! Запускаю нічну підготовку контенту для Психології...")
    try:
        if main_loop and client:
            asyncio.run_coroutine_threadsafe(fill_daily_queue(client, "psy"), main_loop)
    except Exception as e: print(f"Помилка нічної підготовки черги Психології: {e}")

# Функції контролю зображень за 20 хвилин до публікації
def check_ai_image_slot_1():
    print("⏰ Контроль зображення: SLOT 1 (09:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "ai", "AI News & Web3 Tech")

def check_ai_image_slot_2():
    print("⏰ Контроль зображення: SLOT 2 (13:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "ai", "AI Productivity & Work")

def check_ai_image_slot_3():
    print("⏰ Контроль зображення: SLOT 3 (17:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "ai", "AI Finance & Dev Tools")

def check_ai_image_slot_4():
    print("⏰ Контроль зображення: SLOT 4 (21:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "ai", "AI Media & Creative")

def check_psy_image_slot_1():
    print("⏰ Контроль зображення: PSY SLOT 1 (09:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "psy", "Morning Motivation")

def check_psy_image_slot_2():
    print("⏰ Контроль зображення: PSY SLOT 2 (14:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "psy", "Practical Psychology")

def check_psy_image_slot_3():
    print("⏰ Контроль зображення: PSY SLOT 3 (19:00)...")
    if main_loop and client: run_image_control_check(client, main_loop, "psy", "Mindfulness & Relationships")


def schedule_thread_func():
    """Фоновий потік для перевірки розкладу"""
    while True:
        schedule.run_pending()
        time.sleep(30)

# ---------------------------------------------------------------------
# В. Точка Запуску (Event Loop)
# ---------------------------------------------------------------------
async def main():
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    print("=" * 45)
    print("   🤖 СУПЕР-БОТ: ТРЕЙДИНГ + ПСИХОЛОГІЯ + ІИ + БІБЛІОТЕКАР")
    print("=" * 45)
    
    if not os.path.exists("klava.session"):
        print("❌ Файл klava.session не знайдено! Юзербот не зможе працювати.")
        return

    # 1. Запуск Telethon юзербота
    await client.start()
    print("✅ Telethon юзербот підключено успішно!")
    
    # Реєструємо всі авторепостери та автокоментатори екосистеми
    register_commenter(client)
    print("✅ Юзербот обробники успішно зареєстровані!")
    
    # Налаштовуємо команди для обох ботів та очищуємо старі
    try:
        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="start", description="Запустити бібліотеку 📚")
        ])
        await psy_bot.set_my_commands([
            BotCommand(command="start", description="Розпочати діалог 🧠")
        ])
        print("✅ Команди для ботів успішно налаштовані!")
    except Exception as e:
        print(f"⚠️ Не вдалося встановити команди для ботів: {e}")

    # 2. Запуск Aiogram бота-бібліотекаря в цьому ж event loop!
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(dp.start_polling(bot))
    print("✅ Бот-Бібліотекар успішно запущено!")
    
    # Запуск Aiogram бота-психолога (@bbig333_bot) в цьому ж event loop!
    await psy_bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(psy_dp.start_polling(psy_bot))
    print("✅ Бот-Психолог успішно запущено!")
    
    # 3. Налаштовуємо розклад публікацій
    # Трейдинг
    schedule.every().day.at(config.MORNING_POST_TIME, "Europe/Kyiv").do(morning_job)
    schedule.every().day.at("12:00", "Europe/Kyiv").do(noon_job)
    # Штучний Інтелект (AI)
    schedule.every().day.at(config.AI_SLOT_1_TIME, "Europe/Kyiv").do(ai_job_slot_1)
    schedule.every().day.at(config.AI_SLOT_2_TIME, "Europe/Kyiv").do(ai_job_slot_2)
    schedule.every().day.at(config.AI_SLOT_3_TIME, "Europe/Kyiv").do(ai_job_slot_3)
    schedule.every().day.at(config.AI_SLOT_4_TIME, "Europe/Kyiv").do(ai_job_slot_4)
    # Психологія (Нейро-Апгрейд)
    schedule.every().day.at(config.PSY_SLOT_1_TIME, "Europe/Kyiv").do(psy_job_slot_1)
    schedule.every().day.at(config.PSY_SLOT_2_TIME, "Europe/Kyiv").do(psy_job_slot_2)
    schedule.every().day.at(config.PSY_SLOT_3_TIME, "Europe/Kyiv").do(psy_job_slot_3)
    # Тижневий дайджест трейдингу (неділя о 14:00)
    schedule.every().sunday.at("14:00", "Europe/Kyiv").do(weekly_digest_job)
    # Нічна підготовка контенту (авточерга в Google Sheets)
    # Нічна підготовка контенту (роздільні завдання)
    schedule.every().day.at("03:00", "Europe/Kyiv").do(daily_queue_job_ai)
    schedule.every().day.at("04:00", "Europe/Kyiv").do(daily_queue_job_psy)

    # Контрольні перевірки наявності зображень за 20 хвилин до публікації
    # Штучний Інтелект (AI)
    schedule.every().day.at("08:40", "Europe/Kyiv").do(check_ai_image_slot_1)
    schedule.every().day.at("12:40", "Europe/Kyiv").do(check_ai_image_slot_2)
    schedule.every().day.at("16:40", "Europe/Kyiv").do(check_ai_image_slot_3)
    schedule.every().day.at("20:40", "Europe/Kyiv").do(check_ai_image_slot_4)
    # Психологія (PSY)
    schedule.every().day.at("08:40", "Europe/Kyiv").do(check_psy_image_slot_1)
    schedule.every().day.at("13:40", "Europe/Kyiv").do(check_psy_image_slot_2)
    schedule.every().day.at("18:40", "Europe/Kyiv").do(check_psy_image_slot_3)

    
    print(f"📅 Зареєстровано розклад трейдингу (Київ):")
    print(f"   - Ранковий аналіз: щодня о {config.MORNING_POST_TIME}")
    print(f"   - Денні новини:    щодня о 12:00")
    print(f"   - Тижневий дайджест: щонеділі о 14:00")
    print(f"📅 Зареєстровано розклад ШІ (Київ):")
    print(f"   - 1. AI News & Web3 Tech:        щодня о {config.AI_SLOT_1_TIME}")
    print(f"   - 2. AI Productivity & Work:     щодня о {config.AI_SLOT_2_TIME}")
    print(f"   - 3. AI Finance & Dev Tools:     щодня о {config.AI_SLOT_3_TIME}")
    print(f"   - 4. AI Media & Creative:        щодня о {config.AI_SLOT_4_TIME}")
    print(f"📅 Зареєстровано розклад Психології (Київ):")
    print(f"   - 1. Morning Motivation:         щодня о {config.PSY_SLOT_1_TIME}")
    print(f"   - 2. Practical Psychology:       щодня о {config.PSY_SLOT_2_TIME}")
    print(f"   - 3. Mindfulness & Relationships: щодня о {config.PSY_SLOT_3_TIME}")
    print(f"📅 Зареєстровано нічну авточергу в Sheets (Київ): ИИ в 03:00, Психология в 04:00")

    
    # Запускаємо розклад у фоновому потоці
    threading.Thread(target=schedule_thread_func, daemon=True).start()
    
    print("⏳ Супер-бот активний та очікує подій...")
    # Тримаємо програму відкритою і слухаємо Telethon
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
