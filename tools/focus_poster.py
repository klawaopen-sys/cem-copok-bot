import sys
import os
import asyncio
import re
from aiogram import Bot
from aiogram.types import FSInputFile

# Додаємо корінь проекту до sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tools.news_reporter import fetch_rss_news
from tools.news_poster import get_latest_news_texts
from tools.gemini_client import gemini_post_with_retry

async def fetch_all_sources(client):
    print("Gathering sources for focus of the day...")
    # RSS news
    rss_urls = getattr(config, 'TRADING_REPORTER_RSS_URLS', [])
    rss_news = fetch_rss_news(rss_urls, limit=5)
    
    # Telethon donor channel posts
    donor_posts = []
    try:
        donor_posts = await get_latest_news_texts(client, limit=5)
    except Exception as e:
        print(f"Error getting donor posts: {e}")
        
    combined_texts = []
    for item in rss_news:
        combined_texts.append(f"RSS article title: {item['title']}\nDescription: {item['description']}")
    for item in donor_posts:
        combined_texts.append(f"Donor post: {item['text']}")
        
    return "\n\n---\n\n".join(combined_texts)

def generate_focus_text(sources_text):
    if not sources_text.strip():
        return "NO_DATA"
        
    prompt = (
        "Ти — професійний криптовалютний аналітик каналу 'Сім сорок'. "
        "Твоє завдання — проаналізувати надані тексти свіжих новин та аналітичних публікацій з каналів-донорів та знайти в них фактично згадані рівні підтримки (support), опору (resistance) та ринковий сценарій для Bitcoin (BTC).\n\n"
        "ВАЖЛИВО:\n"
        "1. Категорично заборонено вигадувати, розраховувати чи прогнозувати рівні самостійно! Рівні мають бути взяті виключно в готовому вигляді з наданих нижче текстів.\n"
        "2. Зберігай ПОВНИЙ запис рівнів та цін з усіма цифрами та знаками валюти (наприклад: $66,200, $65,000, $68,800). В жодному разі не обрізай перші цифри (наприклад, не пиши ',200' замість '$66,200').\n"
        "3. Категорично заборонено вигадувати ринкові сценарії. Опис має базуватися тільки на фактах із джерел.\n"
        "4. Якщо в наданих джерелах НЕМАЄ згадок конкретних рівнів підтримки або опору для BTC, або немає актуальної аналітики ситуації, ти зобов'язаний відповісти ОДНИМ словом: NO_DATA.\n"
        "5. Якщо дані знайдено, сформуй пост СТРОГО за таким шаблоном:\n"
        "🎯 <b>Фокус дня: BTC</b>\n\n"
        "🔑 <b>Підтримка:</b>\n"
        "[рівень 1] / [рівень 2]\n\n"
        "🚧 <b>Опір:</b>\n"
        "[рівень]\n\n"
        "📊 <b>Сценарій:</b>\n"
        "[Короткий опис поточної ринкової ситуації українською мовою на основі знайдених даних (без води, фінансових рекомендацій та обіцянок прибутку).]\n\n"
        "6. Загальна довжина посту не повинна перевищувати 500 символів (разом із пробілами).\n"
        "7. Використовуй ТІЛЬКИ HTML-теги для оформлення (наприклад, <b>жирний текст</b>). Не використовуй маркдаун зі зірочками.\n\n"
        "Вхідні дані (свіжа аналітика та новини):\n"
        f"{sources_text}\n\n"
        "Відповідь (або пост за шаблоном, або слово NO_DATA):"
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={config.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        r = gemini_post_with_retry(url, headers, payload, timeout=30)
        if r.status_code == 200:
            return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"Gemini Focus API error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Exception during focus generation: {e}")
    return "NO_DATA"

async def post_focus_day(client):
    print("🚀 Початок процесу публікації 'Фокус дня'...")
    sources_text = await fetch_all_sources(client)
    
    post_text = generate_focus_text(sources_text)
    if not post_text or "NO_DATA" in post_text or post_text.strip() == "NO_DATA":
        print("ℹ️ Немає підтверджених рівнів або аналітики у джерелах. Публікація скасовується.")
        return False
        
    bot = Bot(token=config.BOT_TOKEN)
    try:
        if len(post_text) > 500:
            post_text = post_text[:497] + "..."
            
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_path = os.path.join(project_root, '.tmp', 'focus_default.jpg')
        
        if os.path.exists(image_path):
            print(f"Sending Focus of the Day photo post to {config.TARGET_CHANNEL}...")
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
        print("✅ Focus of the Day post sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error posting Focus of the Day: {e}")
        return False
    finally:
        await bot.session.close()

def run_focus_poster(client, loop):
    asyncio.run_coroutine_threadsafe(post_focus_day(client), loop)
