import asyncio
import os
import requests
from telethon import TelegramClient
from aiogram import Bot
from aiogram.types import FSInputFile
import config
import pytz
from datetime import datetime

# Список каналов-доноров
CHANNELS = ["cointelegraph", "Coin_Post", "money"]

async def get_latest_news_texts(client):
    """Собирает последние новости из каналов с помощью Telethon"""
    news_list = []
    print("📥 Збираю пости з каналів-донорів...")
    for channel in CHANNELS:
        try:
            print(f"📡 Зчитую канал @{channel}...")
            # Получаем последние 3 сообщения из каждого канала
            async for message in client.iter_messages(channel, limit=3):
                text = message.text or message.message
                if text and len(text.strip()) > 30:
                    news_list.append({
                        "channel": channel,
                        "message_id": message.id,
                        "text": text.strip(),
                        "has_photo": bool(message.photo),
                        "message_obj": message
                    })
        except Exception as e:
            print(f"⚠️ Не вдалося зчитати канал @{channel}: {e}")
    return news_list

def select_and_rewrite_news_with_gemini(news_items):
    """Выбирает лучшую новость через Gemini и переводит/сокращает её"""
    if not config.GEMINI_API_KEY:
        print("⚠️ Немає ключа Gemini API в конфігу!")
        return None, None
        
    if not news_items:
        print("⚠️ Список новин порожній!")
        return None, None

    # Формируем список новостей для промпта
    candidates_text = ""
    for idx, item in enumerate(news_items):
        candidates_text += f"\n--- КАНДИДАТ #{idx} (Канал: @{item['channel']}, ID: {item['message_id']}) ---\n{item['text']}\n"

    prompt = (
        "Ти — головний редактор популярного фінансово-криптовалютного Telegram-каналу 'Сім сорок'. "
        "Твоє завдання — переглянути останні новини з інших каналів та створити один ідеальний, якісний та захоплюючий інформаційний пост українською мовою для публікації о 12:00 дня.\n\n"
        "Ось зібрані свіжі пости з каналів-донорів:\n"
        f"{candidates_text}\n"
        "Інструкція з виконання:\n"
        "1. Обери ОДНУ найважливішу, найцікавішу та найактуальнішу новину (або об'єднай дві коротких, якщо вони пов'язані).\n"
        "2. Напиши професійний, захоплюючий рерайт цієї новини українською мовою.\n"
        "3. Пост має бути лаконічним (до 800-1000 символів), чітко структурованим (використовуй абзаци, списки та жирний шрифт для ключових слів) та містити відповідні емодзі. Не роби текст надто довгим!\n"
        "4. В кінці поста додай тематичні хештеги.\n"
        "5. Золоте правило: у НАЙПЕРШОМУ рядку своєї відповіді напиши ТІЛЬКИ індекс обраного кандидата у форматі 'INDEX: X' (наприклад, 'INDEX: 3'), а далі з нового рядка пиши текст самого поста. Це критично важливо для вибору правильної картинки!\n\n"
        "Почни відповідь з 'INDEX: X' та пиши виключно українською мовою."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            data = r.json()
            response_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Парсим INDEX
            first_line = response_text.split('\n')[0].strip()
            chosen_index = 0
            post_text = response_text
            
            if "INDEX:" in first_line:
                try:
                    chosen_index = int(first_line.replace("INDEX:", "").strip())
                    post_text = "\n".join(response_text.split('\n')[1:]).strip()
                except Exception:
                    pass
            
            chosen_item = news_items[chosen_index] if chosen_index < len(news_items) else news_items[0]
            return post_text, chosen_item
        else:
            print(f"Помилка Gemini API: HTTP {r.status_code}")
    except Exception as e:
        print(f"Помилка генерації новин через Gemini: {e}")
        
    return None, None

async def post_news_report():
    print("🚀 Початок процесу денної публікації новин...")
    
    # 1. Проверяем наличие сессии telethon
    if not os.path.exists("klava.session"):
        print("❌ Помилка: Файл сесії 'klava.session' не знайдено! Перенесіть його в папку бота.")
        return
        
    # 2. Инициализируем юзербота Telethon (работает в текущей папке)
    client = TelegramClient('klava', config.API_ID, config.API_HASH)
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        await client.start()
        
        # 3. Собираем новости
        news_items = await get_latest_news_texts(client)
        if not news_items:
            print("⚠️ Новин для обробки не знайдено.")
            return
            
        # 4. Просим Gemini выбрать и написать пост
        post_text, chosen_item = select_and_rewrite_news_with_gemini(news_items)
        if not post_text:
            print("❌ Не вдалося згенерувати текст поста через Gemini.")
            return
            
        # 5. Скачиваем медиа с помощью Telethon, если оно есть у выбранного кандидата
        photo_path = None
        if chosen_item and chosen_item["has_photo"]:
            try:
                print(f"📸 Завантажую картинку з обраного поста (Канал: @{chosen_item['channel']})...")
                # Скачиваем прямо в текущую папку под именем news_photo.jpg
                photo_path = await client.download_media(chosen_item["message_obj"], file="news_photo.jpg")
                print(f"✅ Картинку завантажено: {photo_path}")
            except Exception as e:
                print(f"⚠️ Не вдалося завантажити картинку з поста: {e}")

        # 6. Публикуем в Telegram-канал
        print("📤 Надсилаю денну новину в канал...")
        if photo_path and os.path.exists(photo_path):
            await bot.send_photo(
                chat_id=config.TARGET_CHANNEL,
                photo=FSInputFile(photo_path),
                caption=post_text,
                parse_mode='HTML'
            )
            # Удаляем временную картинку
            try:
                os.remove(photo_path)
            except Exception:
                pass
        else:
            await bot.send_message(
                chat_id=config.TARGET_CHANNEL,
                text=post_text,
                parse_mode='HTML'
            )
            
        print("✅ Денний огляд новин успішно опубліковано!")
        
    except Exception as e:
        print(f"❌ Помилка в процесі публікації новин: {e}")
        import traceback; traceback.print_exc()
    finally:
        await client.disconnect()
        await bot.session.close()

def run_news_poster():
    asyncio.run(post_news_report())

if __name__ == "__main__":
    run_news_poster()
