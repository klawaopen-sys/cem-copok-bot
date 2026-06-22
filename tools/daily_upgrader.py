import sys
import os
import random
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
import re

# Додаємо корінь проекту до sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tools.gemini_client import gemini_post_with_retry

# Clean HTML for Telegram (allowed tags: b, i, u, s, code, pre, strong, em, a, blockquote, tg-spoiler)
def clean_html_for_telegram(text: str) -> str:
    # Replace <br> tags with newline
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Remove any disallowed HTML tags
    allowed = r"b|i|u|s|code|pre|strong|em|a|blockquote|tg-spoiler"
    text = re.sub(rf"</?(?!{allowed})[a-zA-Z0-9]+[^>]*>", "", text)
    return text

formats = [
    "Термін дня",
    "Міні-квіз",
    "Психологія трейдера",
    "Ризик-менеджмент",
    "Типова помилка трейдера",
    "Практична порада"
]

def generate_daily_upgrade_text(format_name):
    prompt = (
        "Ти — досвідчений фінансовий аналітик, професійний крипто-трейдер та автор освітнього каналу про трейдинг 'Сім сорок'.\n"
        "Твоє завдання — написати цікавий, корисний та лаконічний пост для щоденної освітньої рубрики 'Щоденна прокачка' для трейдерів.\n\n"
        f"Сьогоднішній вибраний формат рубрики: {format_name}\n\n"
        "Опис форматів для розуміння:\n"
        "1. Текстовий формат 'Термін дня' — просте і зрозуміле пояснення одного важливого трейдерського терміну (наприклад: ліквідність, дивергенція, FOMO, маркет-мейкер, фандінг тощо) з життєвим прикладом.\n"
        "2. Текстовий формат 'Міні-квіз' — невелике питання/загадка з варіантами відповідей та коротким поясненням правильної відповіді нижче.\n"
        "3. Текстовий формат 'Психологія трейдера' — про емоції (страх, жадібність, тільт), як з ними справлятися і зберігати дисципліну.\n"
        "4. Текстовий формат 'Ризик-менеджмент' — про правила виходу з угод, розрахунок обсягу позиції, стоп-лосси та збереження капіталу.\n"
        "5. Текстовий формат 'Типова помилка трейдера' — розбір однієї частої помилки (наприклад: торгівля без стопів, FOMO-вхід, пересиджування збитків, занадто велике плече) та як її уникнути.\n"
        "6. Текстовий формат 'Практична порада' — конкретна порада щодо налаштування графіків, використання індикаторів або аналізу склянки ордерів.\n\n"
        "Вимоги до тексту:\n"
        "1. Мова: бездоганна, природна українська.\n"
        "2. Обсяг: строго до 800 символів (разом із пробілами).\n"
        "3. Стиль: простий, зрозумілий, професійний, без зайвої «води».\n"
        "4. Форматування: використовуй ТІЛЬКИ HTML-теги для оформлення (наприклад, <b>жирний текст</b>, <i>курсив</i>). Не використовуй маркдаун (* або _).\n"
        f"5. Заголовок посту має починатися з емодзі та назви рубрики: 📈 <b>Щоденна прокачка | {format_name}</b>\n"
        "6. Наприкінці посту ОБОВ'ЯЗКОВО додай коротке та цікаве питання до аудиторії, щоб спонукати їх написати коментар (наприклад: 'А ви використовуєте цей індикатор?', 'Яка ваша найбільша помилка в тільті?', тощо).\n"
        "7. КРИТИЧНО: Заборонено давати прямі фінансові чи інвестиційні поради або прогнози конкретних цін активів.\n"
        "8. Додай тематичні хештеги в кінці: #ЩоденнаПрокачка #Трейдинг #Навчання\n\n"
        "Напиши тільки сам текст поста з HTML-тегами, без вступних фраз чи лапок."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        r = gemini_post_with_retry(url, headers, payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            post_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            post_text = post_text.strip('"`\'')
            return post_text
        else:
            print(f"Error calling Gemini: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Exception calling Gemini: {e}")
    return None

async def post_daily_upgrade():
    bot = Bot(token=config.BOT_TOKEN)
    try:
        format_name = random.choice(formats)
        print(f"Generating post for format: {format_name}...")
        post_text = generate_daily_upgrade_text(format_name)
        
        if not post_text:
            print("Failed to generate post text. Aborting.")
            return
            
        if len(post_text) > 1024:
            post_text = post_text[:1020] + "..."
            
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Use configurable daily upgrade image from config, default to .tmp/daily_upgrade.jpg
        daily_image_rel = getattr(config, 'DAILY_UPGRADE_IMAGE', '.tmp/daily_upgrade.jpg')
        image_path = os.path.join(project_root, daily_image_rel)
        
        if os.path.exists(image_path):
            print(f"Sending photo post to {config.TARGET_CHANNEL}...")
            await bot.send_photo(
                chat_id=config.TARGET_CHANNEL,
                photo=FSInputFile(image_path),
                caption=post_text,
                parse_mode='HTML'
            )
        else:
            print(f"Warning: Permanent image {image_path} not found! Sending as text post...")
            await bot.send_message(
                chat_id=config.TARGET_CHANNEL,
                text=post_text,
                parse_mode='HTML'
            )
        print("Daily upgrade post sent successfully!")
    except Exception as e:
        print(f"Error during posting: {e}")
    finally:
        await bot.session.close()

def run_daily_upgrader():
    asyncio.run(post_daily_upgrade())

if __name__ == "__main__":
    run_daily_upgrader()
