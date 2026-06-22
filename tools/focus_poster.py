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
        "Твоє завдання — проаналізувати надані тексти свіжих новин та аналітичних публікацій з каналів-донорів та знайти в них рівні підтримки (support), опору (resistance) та ринковий сценарій для Bitcoin (BTC).\n\n"
        "ВАЖЛИВО:\n"
        "1. Рівні підтримки та опору мають бути взяті з наданих джерел. Якщо конкретні рівні підтримки/опору не згадуються прямо, ти можеш використати згадані в новинах ключові цінові зони, локальні екстремуми (мінімуми та максимуми) або найближчі круглі психологічні рівні (наприклад, $60,000, $65,000, $70,000).\n"
        "2. Зберігай ПОВНИЙ запис рівнів та цін з усіма цифрами та знаками валюти (наприклад: $66,200, $65,000, $68,800).\n"
        "3. Категорично заборонено самостійно прогнозувати майбутню траєкторію або вигадувати ринкові сценарії. Опис ринкової ситуації має базуватися виключно на фактах із джерел.\n"
        "4. Якщо в наданих джерелах немає жодної інформації про рух ціни, поточний курс чи ринковий контекст BTC, тільки тоді поверни ОДНЕ слово: NO_DATA.\n"
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
        print("ℹ️ Немає підтверджених рівнів або аналітики у джерелах. Запускаємо генерацію фолбеку через CoinMarketCap...")
        try:
            from tools.crypto_parser import get_crypto_prices, get_btc_levels
            prices = get_crypto_prices()
            btc_price = None
            if prices and 'BTC' in prices:
                btc_price = prices['BTC']['price']
            
            if not btc_price:
                print("⚠️ Не вдалося отримати ціну BTC з CoinMarketCap. Використовуємо дефолтне значення.")
                btc_price = 65000.0
                
            support, resistance = get_btc_levels(btc_price)
            
            # Запитуємо у Gemini написати короткий опис ринку (сценарій)
            fallback_prompt = (
                "Ти — професійний криптовалютний аналітик каналу 'Сім сорок'. "
                "Тобі потрібно написати короткий ринковий сценарій для Bitcoin (BTC) на сьогодні. "
                "Він має бути корисним, написаним гарною українською мовою та відповідати поточному ринковому контексту.\n\n"
                f"Поточна ціна Bitcoin: ${btc_price:,.2f}.\n"
                f"Джерела новин:\n{sources_text if sources_text else 'Стабільна ринкова активність, очікування макроекономічних даних.'}\n\n"
                "Напиши ТІЛЬКИ короткий ринковий сценарій (1-2 речення, до 250 символів) без вступних слів, лапок або форматування. Починай одразу з суті."
            )
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={config.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": fallback_prompt}]}]}
            
            scenario = "На ринку спостерігається консолідація в очікуванні подальших макроекономічних тригерів. Рекомендується дотримуватись ризик-менеджменту."
            try:
                r = gemini_post_with_retry(url, headers, payload, timeout=25)
                if r.status_code == 200:
                    scenario = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    scenario = scenario.strip('"`\'')
            except Exception as e:
                print(f"Exception during fallback scenario generation: {e}")
                
            post_text = (
                "🎯 <b>Фокус дня: BTC</b>\n\n"
                f"🔑 <b>Підтримка:</b>\n"
                f"${support.replace(' / ', ' / $')}\n\n"
                f"🚧 <b>Опір:</b>\n"
                f"${resistance}\n\n"
                f"📊 <b>Сценарій:</b>\n"
                f"{scenario}"
            )
        except Exception as fe:
            print(f"❌ Помилка під час генерації фолбеку: {fe}")
            return False
        
    bot = Bot(token=config.BOT_TOKEN)
    try:
        if len(post_text) > 500:
            post_text = post_text[:497] + "..."
            
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Use configurable focus image from config, default to .tmp/focus_default.jpg if not set
        focus_image_rel = getattr(config, 'FOCUS_IMAGE', '.tmp/focus_default.jpg')
        image_path = os.path.join(project_root, focus_image_rel)
        
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
