import asyncio
import os
import requests
from telethon import TelegramClient
from aiogram import Bot
from aiogram.types import FSInputFile
import config
import pytz
from datetime import datetime
from crypto_parser import apply_referral_links
from PIL import Image
import re

# ---------------------------------------------------------------------
# А. Налаштування для Трейдингу (12:00)
# ---------------------------------------------------------------------
TRADING_CHANNELS = getattr(config, 'NEWS_DONOR_CHANNELS', ["cointelegraph", "Coin_Post", "money"])

async def get_latest_news_texts(client, limit=3):
    """Збирає останні новини трейдингу з каналів-донорів"""
    news_list = []
    print("📥 Збираю пости з каналів-донорів трейдингу...")
    for channel in TRADING_CHANNELS:
        try:
            channel_name = f"@{channel}" if isinstance(channel, str) else f"ID {channel}"
            print(f"📡 Зчитую канал {channel_name}...")
            async for message in client.iter_messages(channel, limit=limit):
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
            channel_name = f"@{channel}" if isinstance(channel, str) else f"ID {channel}"
            print(f"⚠️ Не вдалося зчитати канал {channel_name}: {e}")
    return news_list

def select_and_rewrite_news_with_gemini(news_items):
    """Вибирає найкращу новину трейдингу через Gemini та робить рерайт"""
    if not config.GEMINI_API_KEY:
        return None, None

    candidates_text = ""
    for idx, item in enumerate(news_items):
        has_img_str = "ТАК" if item['has_photo'] else "НІ"
        candidates_text += f"\n--- КАНДИДАТ #{idx} (Канал: @{item['channel']}, Має картинку: {has_img_str}, ID: {item['message_id']}) ---\n{item['text']}\n"

    prompt = (
        "Ти — головний редактор популярного фінансово-криптовалютного Telegram-каналу 'Сім сорок'. "
        "Твоє завдання — переглянути останні новини з інших каналів та створити один ідеальний, якісний та захоплюючий інформаційний пост українською мовою для публікації о 12:00 дня.\n\n"
        "Ось зібрані свіжі пости з каналів-донорів:\n"
        f"{candidates_text}\n"
        "Інструкція з виконання:\n"
        "1. Обери ОДНУ найважливішу, найцікавішу та найактуальнішу новину (або об'єднай дві коротких, якщо вони пов'язані).\n"
        "   - ВАЖЛИВО: Надавай високий пріоритет кандидатам, у яких 'Має картинку: ТАК', щоб пост вийшов з красивим зображенням!\n"
        "2. Напиши професійний, захоплюючий рерайт цієї новини українською мовою.\n"
        "3. Пост має бути лаконічним, чітким і СТРОГО до 600-650 символів (разом із пробілами), структурованим (використовуй абзаци, емодзі). Не пиши занадто розлогих текстів!\n"
        "4. КРИТИЧНО: Пиши бездоганною, природною українською мовою без русизмів чи кальок з англійської. Наприклад, 'stickers from a photo' перекладай виключно як 'стікери з фото' (використовуй прийменник 'з' для позначення джерела/походження, а не 'за', що означає плату або обмін). Текст має бути стилістично ідеально відшліфованим.\n"
        "5. ВАЖЛИВО: Використовуй ТІЛЬКИ HTML-теги для виділення жирного тексту: <b>текст</b> та </b>. НІКОЛИ не використовуй маркдаун зі зірочками (типу **текст** або *текст*).\n"
        "6. В кінці поста додай тематичні хештеги.\n"
        "7. Золоте правило: у НАЙПЕРШОМУ рядку своєї відповіді напиши ТІЛЬКИ індекс обраного кандидата у форматі 'INDEX: X' (наприклад, 'INDEX: 3'), а далі з нового рядка пиши текст самого поста.\n\n"
        "Почни відповідь з 'INDEX: X' та пиши виключно українською мовою з використанням HTML-форматування <b>...</b> для жирного тексту."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            response_text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            
            lines = response_text.split('\n')
            first_line = lines[0].strip()
            chosen_index = 0
            post_text = response_text
            
            if "INDEX:" in first_line:
                try:
                    chosen_index = int(first_line.replace("INDEX:", "").strip())
                    post_text = "\n".join(lines[1:]).strip()
                except Exception:
                    pass
            
            chosen_item = news_items[chosen_index] if chosen_index < len(news_items) else news_items[0]
            return post_text, chosen_item
    except Exception as e:
        print(f"Помилка генерації новин трейдингу через Gemini: {e}")
    return None, None

# ---------------------------------------------------------------------
# Б. Налаштування для Іскусственного Інтелекту (AI / ШІ)
# ---------------------------------------------------------------------
AI_CHANNELS = getattr(config, 'AI_DONOR_CHANNELS', ["futuretools", "neuro_news", "prompt_hub"])

AI_CATEGORIES = {
    "AI News & Web3 Tech": (
        "<b>AI News & Web3 Tech</b> (Останні релізи та Web3-інструменти).\n"
        "Обери пост про запуск нових ШІ-моделей, корисні веб-сервіси або інтеграцію ШІ в Web3/блокчейн.\n"
        "Рерайт має фокусуватись на новизні, користі та надавати посилання на нові веб-інструменти."
    ),
    "AI Productivity & Work": (
        "<b>AI Productivity & Work</b> (ШІ для підвищення продуктивності та автоматизації).\n"
        "Обери пост про інструменти для роботи з текстом, розшифровки та суммаризації созвонів, плагіни, розширення та автоматизацію рутини.\n"
        "Рерайт має показувати користь для роботи, економити час та надавати інструкції."
    ),
    "AI Finance & Dev Tools": (
        "<b>AI Finance & Dev Tools</b> (ШІ для розробки, написання коду та фінансів).\n"
        "Обери пост про софт для автоматизації програмування, кодінг-асистентів, написання скриптів для трейдингу, роботу з API та базами даних.\n"
        "Рерайт має містити технічні деталі, користь для девелоперів, але без торгових сигналів та аналітики ринку."
    ),
    "AI Media & Creative": (
        "<b>AI Media & Creative</b> (Нейромережі для дизайну, генерації медіа та промпти).\n"
        "Обери пост про генерацію фото, відео, графіки, 3D або аудіо з ШІ, а також готові корисні шаблони промптів.\n"
        "Рерайт має описувати роботу з візуальними ШІ та містити приклади промптів."
    )
}

async def get_latest_ai_posts(client):
    """Збирає останні пости по ШІ з каналів-донорів"""
    news_list = []
    print("📥 Збираю свіжі пости з каналів-донорів ШІ...")
    for channel in AI_CHANNELS:
        try:
            print(f"📡 Зчитую канал @{channel}...")
            async for message in client.iter_messages(channel, limit=4):
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

def select_and_rewrite_ai_with_gemini(news_list, category_name):
    """Запитує у Gemini рерайт ШІ-поста під конкретну тематику"""
    api_key = getattr(config, 'GEMINI_AI_API_KEY', config.GEMINI_API_KEY)
    if not api_key:
        return None, None

    category_info = AI_CATEGORIES.get(category_name, "")
    candidates_text = ""
    for idx, item in enumerate(news_list):
        has_img_str = "ТАК" if item['has_photo'] else "НІ"
        candidates_text += f"\n--- КАНДИДАТ #{idx} (Канал: @{item['channel']}, Зображення: {has_img_str}, ID: {item['message_id']}) ---\n{item['text']}\n"

    prompt = (
        "Ти — головний редактор популярного українського Telegram-каналу про технології майбутнього та штучний інтелект 'Те що треба | AI'.\n"
        f"Твоє завдання — переглянути зібрані пости донорів та написати один унікальний пост під категорію: {category_name}.\n\n"
        f"Опис категорії:\n{category_info}\n\n"
        "Зібрані кандидати з каналів-доноров:\n"
        f"{candidates_text}\n"
        "Інструкція з написання:\n"
        "1. Обери ОДНОГО найкращого кандидата, який відповідає вказаній категорії (перевага тим, у кого є картинка).\n"
        "2. Напиши професійний, унікальний та захоплюючий рерайт цієї новини/огляду виключно українською мовою.\n"
        "3. Пост має бути лаконічним і СТРОГО до 650-700 символів (разом із пробілами).\n"
        "4. КРИТИЧНО: Заборонено давати будь-які фінансові поради, аналітику цін криптовалют чи торгові сигнали. Тільки софт, ШІ-інструменти, гайди та технології.\n"
        "5. КРИТИЧНО: Пиши бездоганною, природною українською мовою без русизмів чи кальок з англійської. Наприклад, 'stickers from a photo' перекладай виключно як 'стікери з фото' (використовуй прийменник 'з' для позначення джерела/походження, а не 'за', що означає плату або обмін). Текст має бути стилістично ідеально відшліфованим.\n"
        "6. Використовуй ТІЛЬКИ HTML-теги для виділення жирного тексту: <b>жирний текст</b>.\n"
        "7. Золоте правило: у НАЙПЕРШОМУ рядку відповіді напиши ТІЛЬКИ індекс у форматі 'INDEX: X', а далі з нового рядка пиши текст самого поста.\n"
        "8. ВАЖЛИВО: Якщо в обраному пості-кандидаті є готовий промпт (наприклад, для Midjourney, ChatGPT, Flux, Stable Diffusion тощо) або корисний шаблон/код запиту, обов'язково знайди та витягни його у первісному вигляді (зазвичай англійською мовою, без змін).\n"
        "   - Наприкінці своєї відповіді, після тексту самого поста, додай цей промпт, виділивши його спеціальними тегами ось так:\n"
        "     [PROMPT_START]\n"
        "     тут текст промпту/промптів (наприклад: /imagine prompt: ...)\n"
        "     [PROMPT_END]\n"
        "   - Якщо готового промпту в пості немає, НЕ додавай теги [PROMPT_START] та [PROMPT_END] взагалі.\n\n"
        "Почни відповідь з 'INDEX: X' та пиши виключно українською мовою з HTML-форматуванням <b>...</b> для жирного тексту."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            response_text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            lines = response_text.split('\n')
            first_line = lines[0].strip()
            chosen_index = 0
            post_text = response_text
            
            if "INDEX:" in first_line:
                try:
                    chosen_index = int(first_line.replace("INDEX:", "").strip())
                    post_text = "\n".join(lines[1:]).strip()
                except Exception:
                    pass
            
            chosen_item = news_list[chosen_index] if chosen_index < len(news_list) else news_list[0]
            
            # Витягуємо промпт, якщо він присутній в тексті
            extracted_prompt = None
            if "[PROMPT_START]" in post_text and "[PROMPT_END]" in post_text:
                try:
                    parts = post_text.split("[PROMPT_START]")
                    post_text = parts[0].strip()
                    prompt_part = parts[1].split("[PROMPT_END]")[0].strip()
                    extracted_prompt = prompt_part
                except Exception:
                    pass
                    
            return post_text, chosen_item, extracted_prompt
    except Exception as e:
        print(f"❌ Помилка генерації ШІ-поста через Gemini: {e}")
    return None, None, None

# ---------------------------------------------------------------------
# В. Загальні утиліти (водяний знак, автозаміна посилань)
# ---------------------------------------------------------------------
def apply_watermark_to_photo(photo_path):
    try:
        logo_file = "logo.jpg"
        if photo_path and os.path.exists(photo_path) and os.path.exists(logo_file):
            main_img = Image.open(photo_path).convert("RGBA")
            logo = Image.open(logo_file).convert("RGBA")
            
            datas = logo.getdata()
            new_data = []
            for item in datas:
                if item[0] > 220 and item[1] > 220 and item[2] > 220:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append((item[0], item[1], item[2], int(item[3] * 0.8)))
            logo.putdata(new_data)
            
            logo_width = int(main_img.width * 0.125)
            aspect_ratio = logo.height / logo.width
            logo_height = int(logo_width * aspect_ratio)
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            padding = int(main_img.width * 0.03)
            position = (main_img.width - logo_width - padding, main_img.height - logo_height - padding)
            
            transparent = Image.new('RGBA', main_img.size, (0,0,0,0))
            transparent.paste(logo, position)
            
            result = Image.alpha_composite(main_img, transparent)
            result.convert("RGB").save(photo_path, "JPEG")
            print("✅ Водяний знак бренду успішно накладено!")
            return True
    except Exception as e:
        print(f"⚠️ Не вдалося накласти водяний знак: {e}")
    return False

def auto_replace_links(text):
    if not text: return text
    pattern = r'https?://t\.me/l_ibrar_y/(\d+)'
    return re.sub(pattern, r'https://t.me/librar_ian_bot?start=\1', text)

# ---------------------------------------------------------------------
# Г. Головні функції публікації (Трейдинг та ІИ)
# ---------------------------------------------------------------------
async def post_news_report(client):
    """Публікує денну новину Трейдингу (12:00)"""
    print("🚀 Початок процесу денної публікації новин трейдингу...")
    bot = Bot(token=config.BOT_TOKEN)
    try:
        news_items = await get_latest_news_texts(client)
        if not news_items:
            print("⚠️ Новин трейдингу не знайдено.")
            return
            
        post_text, chosen_item = select_and_rewrite_news_with_gemini(news_items)
        if not post_text:
            print("❌ Не вдалося згенерувати пост трейдингу.")
            return
        
        post_text = apply_referral_links(post_text)
        post_text = auto_replace_links(post_text)
        
        # Скачування картинки + ватермарк
        photo_path = None
        if chosen_item and chosen_item["has_photo"]:
            try:
                photo_path = await client.download_media(chosen_item["message_obj"], file="news_photo.jpg")
                apply_watermark_to_photo(photo_path)
            except Exception as e:
                print(f"⚠️ Помилка скачування картинки: {e}")

        # Публікація
        if photo_path and os.path.exists(photo_path):
            if len(post_text) <= 1024:
                await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path), caption=post_text, parse_mode='HTML')
            else:
                msg_photo = await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path))
                await bot.send_message(chat_id=config.TARGET_CHANNEL, text=post_text, parse_mode='HTML', reply_to_message_id=msg_photo.message_id)
            try: os.remove(photo_path)
            except Exception: pass
        else:
            await bot.send_message(chat_id=config.TARGET_CHANNEL, text=post_text, parse_mode='HTML')
        print("✅ Денний огляд новин трейдингу опубліковано!")
    except Exception as e:
        print(f"❌ Помилка в процесі публікації новин трейдингу: {e}")
    finally:
        await bot.session.close()

async def post_ai_category_update(client, category_name):
    """Публікує пост ІИ під конкретний слот/категорію"""
    print(f"🚀 Початок публікації для ШІ-категорії '{category_name}'...")
    try:
        from telethon.tl.functions.channels import GetFullChannelRequest
        
        news_list = await get_latest_ai_posts(client)
        if not news_list:
            print("⚠️ ШІ-постів у донорів не знайдено.")
            return

        post_text, chosen_item, extracted_prompt = select_and_rewrite_ai_with_gemini(news_list, category_name)
        if not post_text:
            print("❌ Не вдалося згенерувати ШІ-пост.")
            return

        # Перевіряємо, чи є підв'язана група для коментарів
        has_linked_chat = False
        try:
            c_entity = await client.get_entity(config.AI_TARGET_CHANNEL)
            full_chat_info = await client(GetFullChannelRequest(c_entity))
            if full_chat_info.full_chat.linked_chat_id:
                has_linked_chat = True
        except Exception as e:
            print(f"⚠️ Не вдалося перевірити наявність коментарів у каналі: {e}")

        # Формуємо фінальний текст
        final_post_text = post_text
        
        # Якщо є промпт, але коментарі відсутні — додаємо промпт безпосередньо в пост!
        if extracted_prompt and not has_linked_chat:
            # Адаптуємо заклик до дії: замінюємо коментарі на пост
            final_post_text = final_post_text.replace("у коментарях нижче", "прямо з поста нижче")
            final_post_text = final_post_text.replace("в коментарях нижче", "прямо з поста нижче")
            final_post_text = final_post_text.replace("в коментарях", "прямо з поста")
            final_post_text = final_post_text.replace("в комментариях ниже", "прямо из поста ниже")
            final_post_text = final_post_text.replace("в комментариях", "прямо из поста")
            
            # Додаємо гарно оформлений промпт у тегах <code> (копіювання одним тапом!)
            final_post_text += f"\n\n📋 <b>Промпт для генерації:</b>\n<code>{extracted_prompt}</code>"

        final_post_text = auto_replace_links(final_post_text)

        # Скачування картинки + ватермарк
        photo_path = None
        if chosen_item and chosen_item["has_photo"]:
            try:
                photo_path = await client.download_media(chosen_item["message_obj"], file="temp_ai_post.jpg")
                apply_watermark_to_photo(photo_path)
            except Exception as e:
                print(f"⚠️ Помилка обробки картинки: {e}")

        # Публікуємо в ІИ-канал через Telethon (від імені користувача Клава!)
        msg = None
        if photo_path and os.path.exists(photo_path):
            msg = await client.send_message(entity=config.AI_TARGET_CHANNEL, message=final_post_text, file=photo_path, parse_mode='html')
            try: os.remove(photo_path)
            except Exception: pass
        else:
            msg = await client.send_message(entity=config.AI_TARGET_CHANNEL, message=final_post_text, parse_mode='html')
            
        print(f"✅ ШІ-пост '{category_name}' успішно опубліковано!")

        # Якщо коментарі є і знайдено промпт, публікуємо його у коментарях
        if msg and extracted_prompt and has_linked_chat:
            try:
                await asyncio.sleep(3.0)  # Маленька затримка для надійності
                await client.send_message(entity=config.AI_TARGET_CHANNEL, message=extracted_prompt, comment_to=msg)
                print("✅ Промпт успішно опубліковано в коментарях!")
            except Exception as e:
                print(f"⚠️ Не вдалося опублікувати промпт в коментарях: {e}")
                
    except Exception as e:
        print(f"❌ Помилка в процесі публікації ШІ-категорії '{category_name}': {e}")

# ---------------------------------------------------------------------
# Г-2. Тижневий дайджест (Підсумки тижня - неділя 14:00)
# ---------------------------------------------------------------------
async def post_weekly_digest(client):
    """Публікує тижневий дайджест Трейдингу (неділя 14:00)"""
    print("🚀 Початок процесу щотижневого дайджесту...")
    bot = Bot(token=config.BOT_TOKEN)
    try:
        # Збираємо останні пости з каналів-донорів трейдингу (по 8 з кожного)
        news_items = []
        for channel in TRADING_CHANNELS:
            try:
                channel_name = f"@{channel}" if isinstance(channel, str) else f"ID {channel}"
                print(f"📡 Дайджест: зчитую останні пости з {channel_name}...")
                async for message in client.iter_messages(channel, limit=8):
                    text = message.text or message.message
                    if text and len(text.strip()) > 30:
                        news_items.append({
                            "channel": channel,
                            "text": text.strip(),
                            "has_photo": bool(message.photo),
                            "message_obj": message
                        })
            except Exception as e:
                channel_name = f"@{channel}" if isinstance(channel, str) else f"ID {channel}"
                print(f"⚠️ Не вдалося зчитати {channel_name} для дайджесту: {e}")
                
        if not news_items:
            print("⚠️ Новин для тижневого дайджесту не знайдено.")
            return
            
        # Формуємо текст кандидатів
        candidates_text = ""
        for idx, item in enumerate(news_items[:20]):
            candidates_text += f"\n--- НОВИНА #{idx} ---\n{item['text']}\n"
            
        prompt = (
            "Ти — провідний фінансовий аналітик та головний редактор популярного Telegram-каналу 'Сім сорок'. "
            "Твоє завдання — написати масштабний, преміальний, аналітичний та корисний тижневий дайджест (підсумки тижня) під назвою "
            "<b>📊 Дайджест вихідного дня: Підсумки тижня</b>.\n\n"
            "Ось ключові новини за останні дні:\n"
            f"{candidates_text}\n"
            "Інструкція з написання:\n"
            "1. На основі цих новин обери 3-4 найважливіші події або тренди в криптосвіті за минулий тиждень.\n"
            "2. Структуруй кожну подію: напиши красивий заголовок з емодзі, короткий аналіз події та чому це важливо для ринку.\n"
            "3. Пост має бути написаний красивою, соковитою українською мовою в іронічному та професійному стилі нашого бренду 'Сім сорок'.\n"
            "4. Загальна довжина тексту має бути близько 800-950 символів, щоб легко читалося, але при цьому було змістовно.\n"
            "5. Використовуй ТІЛЬКИ HTML-теги для форматування: <b>жирний текст</b>. Не використовуй маркдаун зі зірочками.\n"
            "6. В кінці додай висновок або корисну пораду на наступний тиждень та підпис бренду.\n\n"
            "Пиши виключно українською мовою з використанням HTML-форматування."
        )
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={config.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                digest_text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                if digest_text.startswith('"') and digest_text.endswith('"'):
                    digest_text = digest_text[1:-1]
                if digest_text.startswith('«') and digest_text.endswith('»'):
                    digest_text = digest_text[1:-1]
            else:
                print(f"Помилка Gemini API в дайджесті: {r.status_code}")
                return
        except Exception as e:
            print(f"❌ Помилка генерації дайджесту через Gemini: {e}")
            return
            
        digest_text = apply_referral_links(digest_text)
        digest_text = auto_replace_links(digest_text)
        
        # Шукаємо першу ліпшу картинку серед донорів для обкладинки
        photo_path = None
        for item in news_items:
            if item["has_photo"]:
                try:
                    photo_path = await client.download_media(item["message_obj"], file="digest_photo.jpg")
                    apply_watermark_to_photo(photo_path)
                    break
                except Exception:
                    continue
                    
        # Якщо картинки немає в постах, спробуємо використати недільний дефолт або ранковий дефолт або запостити без фото
        if not photo_path or not os.path.exists(photo_path):
            if os.path.exists("sunday_digest_default.png"):
                import shutil
                shutil.copy("sunday_digest_default.png", "digest_photo.png")
                photo_path = "digest_photo.png"
                # Водяний знак вже впечений в sunday_digest_default.png!
            elif os.path.exists("morning_default.png"):
                import shutil
                shutil.copy("morning_default.png", "digest_photo.png")
                photo_path = "digest_photo.png"
                apply_watermark_to_photo(photo_path)
                
        # Публікація в канал
        if photo_path and os.path.exists(photo_path):
            if len(digest_text) <= 1024:
                await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path), caption=digest_text, parse_mode='HTML')
            else:
                msg_photo = await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path))
                await bot.send_message(chat_id=config.TARGET_CHANNEL, text=digest_text, parse_mode='HTML', reply_to_message_id=msg_photo.message_id)
            try: os.remove(photo_path)
            except Exception: pass
        else:
            await bot.send_message(chat_id=config.TARGET_CHANNEL, text=digest_text, parse_mode='HTML')
            
        print("✅ Щотижневий фінансовий дайджест успішно опубліковано!")
    except Exception as e:
        print(f"❌ Помилка в процесі публікації щотижневого дайджесту: {e}")
    finally:
        await bot.session.close()

# ---------------------------------------------------------------------
# Г-3. Налаштування для Психології (Нейро-Апгрейд)
# ---------------------------------------------------------------------
PSY_CHANNELS = getattr(config, 'PSY_DONOR_CHANNELS', [])

PSY_CATEGORIES = {
    "Morning Motivation": (
        "<b>Morning Motivation</b> (Мотивація, енергія на день, натхнення та боротьба з прокрастинацією).\n"
        "Обери пост, який найкраще підійде для ранкового настрою, або трансформуй обрану тему на надихаючий, мотивуючий та заряджаючий енергією меседж.\n"
        "Рерайт має фокусуватись на дії, позитивному настрої, продуктивності та надихати на розвиток."
    ),
    "Practical Psychology": (
        "<b>Practical Psychology</b> (Практична психологія, особиста ефективність, когнітивні упередження, аналіз поведінки та саморозвиток).\n"
        "Обери пост про те, як працює наш мозок, когнітивні пастки, методи фокусування уваги, корисні звички або вирішення повсякденних психологічних проблем.\n"
        "Рерайт має бути придатним для практичного застосування з чіткими кроками чи висновками."
    ),
    "Mindfulness & Relationships": (
        "<b>Mindfulness & Relationships</b> (Психологія стосунків, емоційний інтелект, вечірня рефлексія, робота зі стресом та ментальне здоров'я).\n"
        "Обери пост про взаєморозуміння, емпатію, розв'язання конфліктів у стосунках, або про внутрішній спокій, усвідомленість, релаксацію та боротьбу з вигоранням.\n"
        "Рерайт має бути теплим, емпатичним, глибоким та схиляти до роздумів перед сном."
    )
}

async def get_latest_psy_posts(client):
    """Збирає останні пости з психології з каналів-донорів"""
    news_list = []
    print("📥 Збираю свіжі пости з каналів-донорів психології...")
    for channel in PSY_CHANNELS:
        try:
            print(f"📡 Зчитую канал @{channel}...")
            async for message in client.iter_messages(channel, limit=4):
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

def select_and_rewrite_psy_with_gemini(news_list, category_name):
    """Запитує у Gemini рерайт психологічного поста під конкретну тематику"""
    api_key = getattr(config, 'GEMINI_PSY_API_KEY', config.GEMINI_API_KEY)
    if not api_key:
        return None, None

    category_info = PSY_CATEGORIES.get(category_name, "")
    candidates_text = ""
    for idx, item in enumerate(news_list):
        has_img_str = "ТАК" if item['has_photo'] else "НІ"
        candidates_text += f"\n--- КАНДИДАТ #{idx} (Канал: @{item['channel']}, Зображення: {has_img_str}, ID: {item['message_id']}) ---\n{item['text']}\n"

    prompt = (
        "Ти — професійний психолог, автор та головний редактор популярного українського Telegram-каналу про психологію та саморозвиток 'Нейро-Апгрейд'.\n"
        f"Твоє завдання — переглянути зібрані пости донорів та написати один унікальний пост під категорію: {category_name}.\n\n"
        f"Опис категорії:\n{category_info}\n\n"
        "Зібрані кандидати з каналів-доноров:\n"
        f"{candidates_text}\n"
        "Інструкція з написання:\n"
        "1. Обери ОДНОГО найкращого кандидата, який найкраще підходить для вказаної категорії. ВАЖЛИВО: Надавай високий пріоритет кандидатам, у яких 'Зображення: ТАК', щоб пост вийшов з гарною картинкою!\n"
        "2. Напиши професійний, унікальний та захоплюючий рерайт цієї теми виключно українською мовою.\n"
        "3. Тон має бути авторитетним, але дружнім, захоплюючим та легким для сприйняття.\n"
        "4. Пост має бути лаконічним і СТРОГО до 650-700 symbols (разом із пробілами).\n"
        "5. КРИТИЧНО: Цей канал присвячений виключно класичній та практичній психології, саморозвитку та поведінці людей. НІКОЛИ не згадуй штучний інтелект, нейромережі, промпти чи ІТ-технології у тексті постів.\n"
        "6. КРИТИЧНО: Пиши бездоганною, природною українською мовою без русизмів чи кальок з англійської. Наприклад, 'stickers from a photo' перекладай виключно як 'стікери з фото' (використовуй прийменник 'з' для позначення джерела/походження, а не 'за', що означає плату або обмін). Текст має бути стилістично ідеально відшліфованим.\n"
        "7. Використовуй ТІЛЬКИ HTML-теги для виділення жирного тексту: <b>жирний текст</b>. НІКОЛИ не використовуй маркдаун зі зірочками.\n"
        "8. Золоте правило: у НАЙПЕРШОМУ рядку відповіді напиши ТІЛЬКИ індекс у форматі 'INDEX: X', а далі з нового рядка пиши текст самого поста.\n\n"
        "Почни відповідь з 'INDEX: X' та пиши виключно українською мовою з HTML-форматуванням <b>...</b> для жирного тексту."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            response_text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            lines = response_text.split('\n')
            first_line = lines[0].strip()
            chosen_index = 0
            post_text = response_text
            
            if "INDEX:" in first_line:
                try:
                    chosen_index = int(first_line.replace("INDEX:", "").strip())
                    post_text = "\n".join(lines[1:]).strip()
                except Exception:
                    pass
            
            chosen_item = news_list[chosen_index] if chosen_index < len(news_list) else news_list[0]
            return post_text, chosen_item
    except Exception as e:
        print(f"❌ Помилка генерації психологічного поста через Gemini: {e}")
    return None, None

async def post_psy_category_update(client, category_name):
    """Публікує пост психології під конкретний слот/категорію"""
    print(f"🚀 Початок публікації для психологічної категорії '{category_name}'...")
    try:
        news_list = await get_latest_psy_posts(client)
        if not news_list:
            print("⚠️ Постів з психології у донорів не знайдено.")
            return

        post_text, chosen_item = select_and_rewrite_psy_with_gemini(news_list, category_name)
        if not post_text:
            print("❌ Не вдалося згенерувати пост з психології.")
            return

        # Не додаємо сигнатуру за запитом користувача
        final_post_text = post_text
        final_post_text = auto_replace_links(final_post_text)

        # Обробка картинки:
        # 1. Якщо у донора є фото, спробуємо його скачати (але без водяного знаку 7_40)
        # 2. Якщо фото немає або сталася помилка, використовуємо дефолтний малюнок psy_default.png як дежурний
        photo_path = None
        if chosen_item and chosen_item["has_photo"]:
            try:
                photo_path = await client.download_media(chosen_item["message_obj"], file="temp_psy_post.jpg")
                # НЕ накладаємо жодних водяних знаків!
            except Exception as e:
                print(f"⚠️ Помилка скачування картинки донора: {e}")
                photo_path = None
                
        # Дефолтний дежурний малюнок, якщо нічого не підібрали
        if not photo_path or not os.path.exists(photo_path):
            # Дозволяємо використовувати дежурний малюнок тільки для ранкової мотивації
            if category_name == "Morning Motivation" and os.path.exists("psy_default.png"):
                photo_path = "psy_default.png"
                print("🎨 Використовую дежурний малюнок psy_default.png за замовчуванням для ранкової мотивації!")
            else:
                photo_path = None
                print(f"📝 Фото відсутнє для категорії '{category_name}'. Надсилаю як текстовий пост.")

        # Публікуємо в канал через Telethon (від імені користувача Клава!)
        if photo_path and os.path.exists(photo_path):
            is_default = (photo_path == "psy_default.png")
            await client.send_message(entity=config.PSY_TARGET_CHANNEL, message=final_post_text, file=photo_path, parse_mode='html')
            if not is_default:
                try: os.remove(photo_path)
                except Exception: pass
        else:
            await client.send_message(entity=config.PSY_TARGET_CHANNEL, message=final_post_text, parse_mode='html')
            
        print(f"✅ Психологічний пост '{category_name}' успешно опубліковано!")
    except Exception as e:
        print(f"❌ Помилка в процесі публікації психологічної категорії '{category_name}': {e}")

# ---------------------------------------------------------------------
# Д. Інтерфейс запуску з main.py
# ---------------------------------------------------------------------
def run_news_poster(client, loop):
    """Запуск денного огляду новин Трейдингу (12:00)"""
    asyncio.run_coroutine_threadsafe(post_news_report(client), loop)

def run_ai_news_poster(client, loop, category_name):
    """Запуск обзору для конкретної категорії ШІ"""
    asyncio.run_coroutine_threadsafe(post_ai_category_update(client, category_name), loop)

def run_psy_news_poster(client, loop, category_name):
    """Запуск огляду для конкретної категорії Психології"""
    asyncio.run_coroutine_threadsafe(post_psy_category_update(client, category_name), loop)

def run_weekly_digest(client, loop):
    """Запуск щотижневого дайджесту Трейдингу (неділя 14:00)"""
    asyncio.run_coroutine_threadsafe(post_weekly_digest(client), loop)
