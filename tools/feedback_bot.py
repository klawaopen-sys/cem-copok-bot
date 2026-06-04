import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import os
import re
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime
import pytz

import config

# Ініціалізація бота
FEEDBACK_BOT_TOKEN = getattr(config, 'FEEDBACK_BOT_TOKEN', '7256816649:AAEM2RdvGCkDjycNZemp3oeM0DyqqA-5IDo') # Використовуємо дефолтний або окремий токен
bot = Bot(token=FEEDBACK_BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

ADMIN_CHAT_ID = getattr(config, 'ADMIN_CHAT_ID', 648937213) # Задайте ID адміна в config.py

# Стан для FSM
class FeedbackStates(StatesGroup):
    choosing_channel = State()
    writing_ad_details = State()
    writing_support_msg = State()

def get_ad_requests_worksheet():
    """Отримує доступ або створює лист AD_REQUESTS в Google Sheets"""
    SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
    
    try:
        ws = sh.worksheet('AD_REQUESTS')
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title='AD_REQUESTS', rows='10000', cols='7')
        headers = ["id", "user_id", "username", "channel", "message", "status", "created_at"]
        ws.append_row(headers)
    return ws

def save_ad_request(user_id, username, channel, message_text):
    """Зберігає запит на рекламу в Google Sheets"""
    try:
        ws = get_ad_requests_worksheet()
        data = ws.get_all_values()
        next_id = len(data)
        now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')
        row = [str(next_id), str(user_id), f"@{username}" if username else "Немає", channel, message_text, "new", now_str]
        ws.append_row(row)
        return next_id
    except Exception as e:
        print(f"⚠️ Помилка збереження запиту реклами в Sheets: {e}")
        return None

# Клавіатури
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Замовити Рекламу в каналах", callback_data="order_advertising")
    builder.button(text="✍️ Написати Адміністратору", callback_data="write_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def get_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Сім сорок | Трейдинг (@cem_copok)", callback_data="ad_channel_trading")
    builder.button(text="🤖 Те що треба | AI (@te_shoo_treba)", callback_data="ad_channel_ai")
    builder.button(text="🧠 Психологія (@ncux_olo_guY)", callback_data="ad_channel_psy")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "👋 <b>Вітаємо в офіційному боті зворотного зв'язку!</b>\n\n"
        "Тут ви можете замовити рекламу в наших Telegram-каналах або звернутися безпосередньо до адміністратора мережі з будь-яким питанням.\n\n"
        "<i>Оберіть дію нижче 👇</i>"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(query: CallbackQuery, state: FSMContext):
    await state.clear()
    welcome_text = (
        "👋 <b>Вітаємо в офіційному боті зворотного зв'язку!</b>\n\n"
        "Тут ви можете замовити рекламу в наших Telegram-каналах або звернутися безпосередньо до адміністратора мережі з будь-яким питанням.\n\n"
        "<i>Оберіть дію нижче 👇</i>"
    )
    await query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    await query.answer()

@router.callback_query(F.data == "order_advertising")
async def handle_order_advertising(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(
        "📊 <b>Оберіть Telegram-канал, в якому ви бажаєте замовити рекламу:</b>",
        reply_markup=get_channels_keyboard(),
        parse_mode="HTML"
    )
    await query.answer()

@router.callback_query(F.data.startswith("ad_channel_"))
async def handle_channel_selection(query: CallbackQuery, state: FSMContext):
    channel_key = query.data.replace("ad_channel_", "")
    channels_map = {
        "trading": "📢 Сім сорок | Трейдинг (@cem_copok)",
        "ai": "🤖 Те що треба | AI (@te_shoo_treba)",
        "psy": "🧠 Психологія (@ncux_olo_guY)"
    }
    selected_channel = channels_map.get(channel_key, "Наші канали")
    await state.update_data(selected_channel=selected_channel)
    
    await state.set_state(FeedbackStates.writing_ad_details)
    await query.message.edit_text(
        f"✍️ Ви обрали: <b>{selected_channel}</b>\n\n"
        f"Будь ласка, надішліть детальний опис вашого проекту, посилання та бажану дату публікації реклами.\n\n"
        f"<i>Адміністратор отримає ваш запит та зв'яжеться з вами прямо тут!</i>",
        parse_mode="HTML"
    )
    await query.answer()

@router.message(FeedbackStates.writing_ad_details)
async def process_ad_details(message: Message, state: FSMContext):
    user_data = await state.get_data()
    selected_channel = user_data.get("selected_channel", "Не вказано")
    ad_text = message.text or message.caption or "[Медіа-файл]"
    
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    # Зберігаємо в Google Sheets
    req_id = save_ad_request(user_id, username, selected_channel, ad_text)
    
    # Формуємо красиву картку для адміна
    admin_card = (
        f"🔔 <b>НОВИЙ ЗАПИТ НА РЕКЛАМУ #{req_id}</b>\n"
        f"👤 <b>Клієнт:</b> {fullname} (@{username if username else 'Немає'}) (ID: #u{user_id})\n"
        f"📈 <b>Канал:</b> {selected_channel}\n\n"
        f"📝 <b>Деталі:</b>\n{ad_text}\n\n"
        f"<i>👉 Щоб відповісти клієнту, просто зробіть РЕПЛАЙ (Reply) на це повідомлення!</i>"
    )
    
    try:
        # Пересилаємо адміну
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=admin_card, parse_mode="HTML")
        elif message.document:
            await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=admin_card, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_card, parse_mode="HTML")
            
        await message.answer(
            "✅ <b>Ваш запит на рекламу успішно надіслано адміністратору!</b>\n\n"
            "Ми опрацюємо його найближчим часом та напишемо вам відповідь прямо у цей чат. Дякуємо! 😊",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Не вдалося надіслати запит адміну: {e}")
        await message.answer("⚠️ Сталася помилка при надсиланні запиту адміну. Спробуйте пізніше або напишіть безпосередньо.")
        
    await state.clear()

@router.callback_query(F.data == "write_to_admin")
async def handle_write_to_admin(query: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackStates.writing_support_msg)
    await query.message.edit_text(
        "✍️ <b>Напишіть ваше питання або пропозицію для адміністратора:</b>\n\n"
        "<i>Ви можете надіслати текст, photo або файл. Адміністратор відповість вам прямо у цей чат.</i>",
        parse_mode="HTML"
    )
    await query.answer()

@router.message(FeedbackStates.writing_support_msg)
async def process_support_msg(message: Message, state: FSMContext):
    msg_text = message.text or message.caption or "[Медіа-файл]"
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    admin_card = (
        f"📩 <b>НОВЕ ПОВІДОМЛЕННЯ ВІД КОРИСТУВАЧА</b>\n"
        f"👤 <b>Відправник:</b> {fullname} (@{username if username else 'Немає'}) (ID: #u{user_id})\n\n"
        f"📝 <b>Повідомлення:</b>\n{msg_text}\n\n"
        f"<i>👉 Щоб відповісти користувачу, просто зробіть РЕПЛАЙ (Reply) на це повідомлення!</i>"
    )
    
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=admin_card, parse_mode="HTML")
        elif message.document:
            await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=admin_card, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_card, parse_mode="HTML")
            
        await message.answer(
            "✅ <b>Ваше повідомлення успішно надіслано адміністратору!</b>\n\n"
            "Ми відповімо вам найближчим часом. Гарного дня! 😊",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Не вдалося надіслати повідомлення адміну: {e}")
        await message.answer("⚠️ Помилка доставки. Спробуйте пізніше.")
        
    await state.clear()

# --- Логіка відповіді Адміністратора (Реплай) ---
@router.message(F.chat.id == ADMIN_CHAT_ID, F.reply_to_message)
async def handle_admin_reply(message: Message):
    # Шукаємо ID клієнта в тексті оригінального повідомлення
    source_msg = message.reply_to_message
    text_to_search = source_msg.text or source_msg.caption or ""
    
    match = re.search(r'\(ID:\s+#u(\d+)\)', text_to_search)
    if not match:
        return
        
    target_user_id = int(match.group(1))
    
    try:
        reply_prefix = "✉️ <b>Відповідь від Адміністратора:</b>\n\n"
        
        if message.photo:
            caption = reply_prefix + (message.caption or "")
            await bot.send_photo(chat_id=target_user_id, photo=message.photo[-1].file_id, caption=caption, parse_mode="HTML")
        elif message.document:
            caption = reply_prefix + (message.caption or "")
            await bot.send_document(chat_id=target_user_id, document=message.document.file_id, caption=caption, parse_mode="HTML")
        elif message.text:
            await bot.send_message(chat_id=target_user_id, text=reply_prefix + message.text, parse_mode="HTML")
        else:
            await bot.copy_message(chat_id=target_user_id, from_chat_id=ADMIN_CHAT_ID, message_id=message.message_id)
            
        await message.reply("✅ <b>Відповідь успішно доставлена користувачу!</b>", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ <b>Помилка доставки відповіді:</b> {e}", parse_mode="HTML")

async def main():
    print("=" * 45)
    print("   📊 FEEDBACK & ADVERTISING BOT STARTING...")
    print("=" * 45)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
