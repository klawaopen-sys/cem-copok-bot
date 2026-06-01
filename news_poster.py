import asyncio
import os
import requests
import urllib.parse
from telethon import TelegramClient
from aiogram import Bot
from aiogram.types import FSInputFile
import config
import pytz
from datetime import datetime
from crypto_parser import apply_referral_links
from PIL import Image, ImageDraw, ImageFont
import re
import base64


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
        "5. КРИТИЧНО: Якщо в тексті згадуються теми штучного інтелекту, нейромереж чи ШІ-інструментів, обов'язково зроби красиве текстове відсилання-посилання на наш партнерський канал про штучний інтелект: @te_shoo_treba (наприклад, 'дізнатися більше можна в <b><a href=\"https://t.me/te_shoo_treba\">Те що треба | AI</a></b>'). "
        "Якщо в тексті згадується психологія, стрес, емоції чи ментальне здоров'я, зроби красиве відсилання на наш партнерський канал про психологію: @ncux_olo_guY (наприклад, 'підтримати ментальне здоров\\'я допоможе <b><a href=\"https://t.me/ncux_olo_guY\">Нейро-Апгрейд</a></b>').\n"
        "6. ВАЖЛИВО: Використовуй ТІЛЬКИ HTML-теги для виділення жирного тексту: <b>текст</b> та </b>. НІКОЛИ не використовуй маркдаун зі зірочками (типу **текст** або *текст*).\n"
        "7. В кінці поста додай тематичні хештеги.\n"
        "8. Золоте правило: у НАЙПЕРШОМУ рядку своєї відповіді напиши ТІЛЬКИ індекс обраного кандидата у форматі 'INDEX: X' (наприклад, 'INDEX: 3'), а далі з нового рядка пиши текст самого поста.\n\n"
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
            post_text = sanitize_post_text(post_text, 'trading')
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
    if not api_key or api_key.startswith('AQ.'):
        api_key = config.GEMINI_API_KEY
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
def draw_rounded_rectangle(draw, coordinates, radius, fill):
    """Draws a rounded rectangle with custom radius."""
    x1, y1, x2, y2 = coordinates
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

def apply_brand_frame(photo_path, channel_type):
    """
    Applies a stunning, professional brand frame and text tag to the image.
    channel_type can be: 'trading', 'ai', 'psy'
    """
    try:
        if not photo_path or not os.path.exists(photo_path):
            return False
        
        main_img = Image.open(photo_path).convert("RGBA")
        width, height = main_img.size
        
        overlay = Image.new("RGBA", main_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        if channel_type == 'trading':
            border_color = (26, 26, 26, 255)
            accent_color = (255, 193, 7, 255)
            tag_text = "@cem_copok"
            tag_bg = (33, 33, 33, 230)
            tag_text_color = (255, 255, 255, 255)
        elif channel_type == 'ai':
            border_color = (13, 13, 26, 255)
            accent_color = (0, 229, 255, 255)
            tag_text = "@te_shoo_treba"
            tag_bg = (18, 18, 36, 230)
            tag_text_color = (255, 255, 255, 255)
        else: # 'psy'
            border_color = (245, 242, 235, 255)
            accent_color = (179, 157, 219, 255)
            tag_text = "@ncux_olo_guY"
            tag_bg = (255, 255, 255, 230)
            tag_text_color = (78, 52, 46, 255)
            
        border_width = int(width * 0.02)
        
        # Outer borders
        draw.rectangle([0, 0, width, border_width], fill=border_color)
        draw.rectangle([0, height - border_width, width, height], fill=border_color)
        draw.rectangle([0, 0, border_width, height], fill=border_color)
        draw.rectangle([width - border_width, 0, width, height], fill=border_color)
        
        # Inner accent line
        accent_width = max(2, int(border_width * 0.15))
        draw.rectangle([border_width, border_width, width - border_width, border_width + accent_width], fill=accent_color)
        draw.rectangle([border_width, height - border_width - accent_width, width - border_width, height - border_width], fill=accent_color)
        draw.rectangle([border_width, border_width, border_width + accent_width, height - border_width], fill=accent_color)
        draw.rectangle([width - border_width - accent_width, border_width, width - border_width, height - border_width], fill=accent_color)
        
        # Font loading
        font = None
        font_paths = [
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\tahoma.ttf"
        ]
        font_size = int(height * 0.028)
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except Exception:
                    pass
        if not font:
            font = ImageFont.load_default()
            
        try:
            text_bbox = draw.textbbox((0, 0), tag_text, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_w, text_h = draw.textsize(tag_text, font=font)
            
        padding_x = int(width * 0.025)
        padding_y = int(height * 0.012)
        
        tag_w = text_w + padding_x * 2
        tag_h = text_h + padding_y * 2
        
        # Tag placement: bottom-left corner
        tag_x1 = border_width + int(width * 0.02)
        tag_y1 = height - border_width - tag_h - int(height * 0.02)
        tag_x2 = border_width + tag_w + int(width * 0.02)
        tag_y2 = height - border_width - int(height * 0.02)
        
        draw_rounded_rectangle(draw, [tag_x1, tag_y1, tag_x2, tag_y2], radius=int(tag_h * 0.25), fill=tag_bg)
        draw.rectangle([tag_x1, tag_y1 + int(tag_h * 0.2), tag_x1 + 4, tag_y2 - int(tag_h * 0.2)], fill=accent_color)
        
        text_x = tag_x1 + padding_x
        text_y = tag_y1 + padding_y - int(text_h * 0.1)
        draw.text((text_x, text_y), tag_text, fill=tag_text_color, font=font)
        
        # Watermark
        logo_file = "logo.jpg"
        if channel_type == 'psy':
            logo_file = "psy_logo.png"
        elif channel_type == 'ai':
            logo_file = "ai_logo.png"
            
        if os.path.exists(logo_file):
            try:
                logo = Image.open(logo_file).convert("RGBA")
                
                # Make it semi-transparent (45% opacity)
                opacity = 0.45
                alpha = logo.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                logo.putalpha(alpha)
                
                logo_size = int(width * 0.08)
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Logo placement: bottom-right corner
                logo_x = width - border_width - logo_size - int(width * 0.02)
                logo_y = height - border_width - logo_size - int(height * 0.02)
                
                if channel_type in ['psy', 'ai']:
                    overlay.paste(logo, (logo_x, logo_y), mask=logo)
                else:
                    mask = Image.new("L", (logo_size, logo_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)
                    
                    circular_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
                    circular_logo.paste(logo, (0, 0), mask=mask)
                    
                    overlay.paste(circular_logo, (logo_x, logo_y), mask=circular_logo)
            except Exception as le:
                print(f"⚠️ Logo watermark error: {le}")

                
        result = Image.alpha_composite(main_img, overlay)
        result.convert("RGB").save(photo_path, "JPEG", quality=95)
        print(f"✅ Sleek brand frame applied for '{channel_type}'!")
        return True
    except Exception as e:
        print(f"⚠️ Error applying brand frame: {e}")
        return False

def contains_russian_text(image_path):
    """
    Uses Gemini to analyze if the image contains any Russian text.
    Returns True if Russian text is present, False otherwise.
    """
    if not image_path or not os.path.exists(image_path):
        return False
        
    api_key = config.GEMINI_API_KEY
    if not api_key:
        print("⚠️ Gemini key not found for OCR check.")
        return False
        
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
            
        mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        
        prompt = (
            "Analyze this image carefully. Your task is to detect if there is any visible text or writing on the image, "
            "and determine if any of that text is in the Russian language (written in Cyrillic, using Russian words like 'да', 'и', 'чего', 'криндж', 'сломался', etc.).\n\n"
            "Return ONLY 'YES' if Russian text is present on the image, or 'NO' if there is no text or the text is in English, Ukrainian, or any other language.\n"
            "Do not write any other words, explanations, or markdown. Only output 'YES' or 'NO'."
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_data
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        print(f"👁️ Sending image to Gemini for Russian text detection (OCR)...")
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            result = r.json()['candidates'][0]['content']['parts'][0]['text'].strip().upper()
            print(f"🔍 Gemini OCR result: {result}")
            return "YES" in result
        else:
            print(f"⚠️ Gemini OCR API error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Error during contains_russian_text OCR: {e}")
        
    return False

async def generate_ai_image(post_text, channel_type, save_path):
    """
    Generates a stunning unique visual using Gemini to write the prompt 
    and Pollinations.ai (Flux) to render the image.
    Applies the brand frame at the end.
    """
    clean_text = re.sub(r'<[^>]+>', '', post_text)
    
    api_key = config.GEMINI_API_KEY
    if channel_type == 'ai':
        api_key = getattr(config, 'GEMINI_AI_API_KEY', config.GEMINI_API_KEY)
    elif channel_type == 'psy':
        api_key = getattr(config, 'GEMINI_PSY_API_KEY', config.GEMINI_API_KEY)
        
    if not api_key or api_key.startswith('AQ.'):
        api_key = config.GEMINI_API_KEY
        
    if not api_key:
        print("⚠️ Gemini API key not found. Skipping image generation.")
        return False
        
    style_guideline = ""
    if channel_type == 'trading':
        style_guideline = "Style: premium 3D render, trading/charts/financial concept illustration, dark mode theme with elegant gold/green accents, clean studio lighting, 8k resolution."
    elif channel_type == 'ai':
        style_guideline = "Style: futuristic high-tech 3D render illustration, abstract artificial intelligence, glowing cybernetic lines, deep purple and electric cyan accents, cyberpunk vibe, 8k resolution."
    else: # psy
        style_guideline = "Style: serene minimalist 3D rendering, pastel and calming warm tones, human mind/mindfulness/self-reflection concept illustration, organic fluid shapes, soft studio shadows."

    prompt = (
        f"Based on this Ukrainian article, generate a highly descriptive visual prompt for an AI image generator (Stable Diffusion/Flux) in English.\n\n"
        f"Article content:\n{clean_text[:1200]}\n\n"
        f"Instructions:\n"
        f"1. Generate a descriptive visual scene representing the main idea of this article.\n"
        f"2. {style_guideline}\n"
        f"3. CRITICAL: The image must be purely visual. It must have NO text, NO words, NO letters, NO labels, NO typography. It should have absolutely empty spaces where text would be.\n"
        f"4. Output ONLY the English prompt string. DO NOT wrap in quotes, DO NOT write any markdown, introduction, or explanations. Just the prompt text itself."
    )
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        print(f"🎨 Asking Gemini to create image prompt for '{channel_type}'...")
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            gemini_prompt = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            gemini_prompt = re.sub(r'^["\'`]+|["\'`]+$', '', gemini_prompt)
            gemini_prompt += ", clean, modern digital art, vibrant colors, studio lighting, highly detailed, octane render, 8k, no text, no words, no letters, no typography, no logos"
            
            print(f"🔮 Prompt: {gemini_prompt[:150]}...")
            
            encoded_prompt = urllib.parse.quote(gemini_prompt)
            gen_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            
            print(f"🚀 Generating image via Pollinations.ai (Flux)...")
            img_resp = requests.get(gen_url, timeout=45)
            if img_resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(img_resp.content)
                print("💾 Image successfully generated and saved!")
                apply_brand_frame(save_path, channel_type)
                return True
            else:
                print(f"⚠️ Pollinations API error: {img_resp.status_code}")
        else:
            print(f"⚠️ Gemini API error during prompt generation: {r.status_code}")
    except Exception as e:
        print(f"❌ Failed to generate AI image: {e}")
        
    return False


def get_used_donors_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials
    
    SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
    
    try:
        ws = sh.worksheet('USED_DONORS')
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title='USED_DONORS', rows='10000', cols='3')
        headers = ["donor_channel", "message_id", "used_at"]
        ws.append_row(headers)
    return ws

def get_used_donors():
    """Повертає set кортежів (donor_channel, message_id) вже використаних донорських постів."""
    try:
        ws = get_used_donors_worksheet()
        rows = ws.get_all_values()
        used = set()
        if len(rows) > 1:
            for row in rows[1:]:
                if len(row) >= 2:
                    used.add((str(row[0]).strip(), str(row[1]).strip()))
        return used
    except Exception as e:
        print(f"⚠️ Помилка читання листа USED_DONORS: {e}")
        return set()

def mark_donor_as_used(donor_channel, message_id):
    """Додає новий рядок у лист USED_DONORS для позначення поста як використаного."""
    try:
        ws = get_used_donors_worksheet()
        now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')
        ws.append_row([str(donor_channel), str(message_id), now_str])
        print(f"✅ Донорський пост @{donor_channel} ID {message_id} позначено як використаний.")
    except Exception as e:
        print(f"⚠️ Помилка запису в USED_DONORS: {e}")

def is_ad_or_invalid_psy_post(text):
    if not text:
        return True
    text_lower = text.lower()
    # Маркери рекламних постів
    ad_keywords = [
        "реклама", "промокод", "скидка", "снижка", "акція", "акция", 
        "купить", "придбати", "ціна", "цена", "подписывайтесь", "підписуйтесь",
        "канал", "чат", "переходи", "жми", "клик", "click", "подпишись", "підпишись",
        "запис на", "консультація", "платна"
    ]
    for kw in ad_keywords:
        if kw in text_lower:
            return True
            
    # Перевіряємо посилання t.me на інші канали
    telegram_links = re.findall(r't\.me/([a-zA-Z0-9_]+)', text_lower)
    for link in telegram_links:
        if link.lower() not in ['ncux_olo_guy', 'cem_copok', 'te_shoo_treba', 'librar_ian_bot', 'l_ibrar_y', 'bbig333_bot']:
            return True
    return False

def sanitize_post_text(text, channel_type):
    """Замінює будь-які сторонні згадки/посилання на наші власні ресурси."""
    if not text:
        return text
        
    allowed_handles = ['cem_copok', 'ncux_olo_guy', 'te_shoo_treba', 'librar_ian_bot', 'l_ibrar_y', 'bbig333_bot']
    
    def replace_mention(match):
        handle = match.group(1)
        if handle.lower() in allowed_handles:
            return f"@{handle}"
        else:
            if channel_type == 'psy': return "@ncux_olo_guY"
            elif channel_type == 'ai': return "@te_shoo_treba"
            else: return "@cem_copok"
                
    text = re.sub(r'@([a-zA-Z0-9_]+)', replace_mention, text)
    
    def replace_tme_link(match):
        full_url = match.group(0)
        handle = match.group(1)
        if handle.lower() in allowed_handles:
            return full_url
        else:
            if channel_type == 'psy': return "https://t.me/ncux_olo_guY"
            elif channel_type == 'ai': return "https://t.me/te_shoo_treba"
            else: return "https://t.me/cem_copok"
                
    text = re.sub(r'https?://t\.me/([a-zA-Z0-9_]+)', replace_tme_link, text)
    return text

def auto_replace_links(text):
    if not text: return text
    pattern = r'https?://t\.me/l_ibrar_y/(\d+)'
    return re.sub(pattern, r'https://t.me/librar_ian_bot?start=\1', text)


def get_posts_queue_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials
    
    SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
    
    try:
        ws = sh.worksheet('POSTS_QUEUE')
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title='POSTS_QUEUE', rows='1000', cols='9')
        headers = ["id", "channel", "category", "post_text", "photo_path", "status", "created_at", "published_at", "post_link"]
        ws.append_row(headers)
    return ws

async def fill_daily_queue(client):
    """
    Called once a day (at night, e.g. 03:00) to populate the POSTS_QUEUE 
    for the next 24 hours. Pre-generates and pre-frames AI images.
    """
    print("🌙 [QUEUE] Starting nightly queue population...")
    os.makedirs("media_queue", exist_ok=True)
    
    ws = get_posts_queue_worksheet()
    data = ws.get_all_values()
    
    # 1. Clean up unused images from disk that are no longer pending
    pending_images = set()
    if len(data) > 1:
        for row in data[1:]:
            if len(row) > 5 and row[5] == 'pending' and row[4]:
                pending_images.add(os.path.basename(row[4]))
                
    if os.path.exists("media_queue"):
        for f in os.listdir("media_queue"):
            if f not in pending_images:
                try:
                    os.remove(os.path.join("media_queue", f))
                    print(f"🗑️ Cleaned up old image: {f}")
                except Exception:
                    pass

    # Determine next available ID
    next_id = 1
    if len(data) > 1:
        try:
            ids = [int(row[0]) for row in data[1:] if row[0].isdigit()]
            if ids:
                next_id = max(ids) + 1
        except Exception:
            next_id = len(data)

    # 2. Check and fill AI slots
    ai_categories = ["AI News & Web3 Tech", "AI Productivity & Work", "AI Finance & Dev Tools", "AI Media & Creative"]
    existing_pending = {}
    if len(data) > 1:
        for row in data[1:]:
            if len(row) > 5 and row[5] == 'pending':
                chan, cat = row[1], row[2]
                existing_pending[(chan, cat)] = True

    now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')

    # Fetch AI candidates once
    ai_posts = []
    try:
        ai_posts = await get_latest_ai_posts(client)
    except Exception as e:
        print(f"⚠️ Error fetching AI posts for queue: {e}")

    used_donor_posts = set()

    for cat in ai_categories:
        if ('ai', cat) in existing_pending:
            print(f"⏭️ AI slot '{cat}' already has a pending post. Skipping.")
            continue
            
        if not ai_posts:
            continue
            
        # Filter out already used candidates in the same run to prevent duplicate images/sources
        candidates = [item for item in ai_posts if (item['channel'], item['message_id']) not in used_donor_posts]
        if not candidates:
            print(f"⚠️ No fresh AI candidates left for slot '{cat}'.")
            continue
            
        print(f"📦 Preparing AI post for category '{cat}'...")
        post_text, chosen_item, extracted_prompt = select_and_rewrite_ai_with_gemini(candidates, cat)
        if post_text and chosen_item:
            # Mark candidate as used
            used_donor_posts.add((chosen_item['channel'], chosen_item['message_id']))
            
            final_text = post_text
            if extracted_prompt:
                final_text += f"\n\n📋 <b>Промпт для генерації:</b>\n<code>{extracted_prompt}</code>"
                
            final_text = auto_replace_links(final_text)
            
            photo_filename = f"media_queue/ai_{next_id}.jpg"
            img_ok = await generate_ai_image(final_text, "ai", photo_filename)
            if not img_ok:
                if chosen_item and chosen_item["has_photo"]:
                    try:
                        photo_filename = await client.download_media(chosen_item["message_obj"], file=photo_filename)
                        if contains_russian_text(photo_filename):
                            print("🚫 Скачана картинка містить російський текст! Відхиляємо та пробуємо примусово перегенерувати через ШІ...")
                            try: os.remove(photo_filename)
                            except Exception: pass
                            photo_filename = f"media_queue/ai_{next_id}.jpg"
                            img_ok = await generate_ai_image(final_text, "ai", photo_filename)
                        else:
                            apply_brand_frame(photo_filename, "ai")
                            img_ok = True
                    except Exception:
                        photo_filename = ""
                else:
                    photo_filename = ""
            
            row = [str(next_id), "ai", cat, final_text, photo_filename if img_ok else "", "pending", now_str, "", ""]
            ws.append_row(row)
            print(f"✅ AI post '{cat}' queued with ID {next_id}!")
            next_id += 1
            await asyncio.sleep(2.0)

    # 3. Check and fill PSY slots
    psy_categories = ["Morning Motivation", "Practical Psychology", "Mindfulness & Relationships"]
    psy_posts = []
    try:
        psy_posts = await get_latest_psy_posts(client)
    except Exception as e:
        print(f"⚠️ Error fetching PSY posts for queue: {e}")

    for cat in psy_categories:
        if ('psy', cat) in existing_pending:
            print(f"⏭️ PSY slot '{cat}' already has a pending post. Skipping.")
            continue
            
        if not psy_posts:
            continue
            
        # Filter out already used candidates in the same run to prevent duplicate images/sources
        candidates = [item for item in psy_posts if (item['channel'], item['message_id']) not in used_donor_posts]
        if not candidates:
            print(f"⚠️ No fresh PSY candidates left for slot '{cat}'.")
            continue
            
        print(f"📦 Preparing PSY post for category '{cat}'...")
        post_text, chosen_item = select_and_rewrite_psy_with_gemini(candidates, cat)
        if post_text and chosen_item:
            # Mark candidate as used
            used_donor_posts.add((chosen_item['channel'], chosen_item['message_id']))
            
            final_text = auto_replace_links(post_text)
            photo_filename = f"media_queue/psy_{next_id}.jpg"
            
            img_ok = await generate_ai_image(final_text, "psy", photo_filename)
            if not img_ok:
                if chosen_item and chosen_item["has_photo"]:
                    try:
                        photo_filename = await client.download_media(chosen_item["message_obj"], file=photo_filename)
                        if contains_russian_text(photo_filename):
                            print("🚫 Скачана картинка містить російський текст! Відхиляємо та пробуємо примусово перегенерувати через ШІ...")
                            try: os.remove(photo_filename)
                            except Exception: pass
                            photo_filename = f"media_queue/psy_{next_id}.jpg"
                            img_ok = await generate_ai_image(final_text, "psy", photo_filename)
                        else:
                            apply_brand_frame(photo_filename, "psy")
                            img_ok = True
                    except Exception:
                        photo_filename = ""
                else:
                    photo_filename = ""
                    
            if not img_ok and cat == "Morning Motivation" and os.path.exists("psy_default.png"):
                import shutil
                shutil.copy("psy_default.png", photo_filename)
                apply_brand_frame(photo_filename, "psy")
                img_ok = True

            row = [str(next_id), "psy", cat, final_text, photo_filename if img_ok else "", "pending", now_str, "", ""]
            ws.append_row(row)
            print(f"✅ PSY post '{cat}' queued with ID {next_id}!")
            next_id += 1
            await asyncio.sleep(2.0)
            
    print("🌅 [QUEUE] Nightly queue population finished successfully!")

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
        
        # Генерація картинки через ІІ з накладенням рамки
        photo_path = "news_photo.jpg"
        generated_ok = await generate_ai_image(post_text, "trading", photo_path)
        if not generated_ok:
            # Запасний варіант: якщо у донора є фото, скачуємо його та рамкуємо
            if chosen_item and chosen_item["has_photo"]:
                try:
                    photo_path = await client.download_media(chosen_item["message_obj"], file="news_photo.jpg")
                    if contains_russian_text(photo_path):
                        print("🚫 Скачана картинка містить російський текст! Відхиляємо та пробуємо примусово перегенерувати через ШІ...")
                        try: os.remove(photo_path)
                        except Exception: pass
                        photo_path = "news_photo.jpg"
                        generated_ok = await generate_ai_image(post_text, "trading", photo_path)
                    else:
                        apply_brand_frame(photo_path, "trading")
                        generated_ok = True
                except Exception as e:
                    print(f"⚠️ Помилка скачування оригінальної картинки: {e}")
                    photo_path = None
            else:
                photo_path = None
        
        if not generated_ok:
            photo_path = None


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
        # 1. Спробуємо знайти пост у черзі в Google Таблиці
        try:
            ws = get_posts_queue_worksheet()
            rows = ws.get_all_values()
            queued_post = None
            row_idx = -1
            
            if len(rows) > 1:
                for idx, row in enumerate(rows[1:], start=2):
                    if len(row) > 5 and row[1] == 'ai' and row[2] == category_name and row[5] == 'pending':
                        queued_post = row
                        row_idx = idx
                        break
                        
            if queued_post:
                print(f"🎯 [QUEUE] Знайдено запланований пост з ID {queued_post[0]} для категорії '{category_name}'!")
                final_post_text = queued_post[3]
                photo_path = queued_post[4]
                
                msg = None
                if photo_path and os.path.exists(photo_path):
                    msg = await client.send_message(entity=config.AI_TARGET_CHANNEL, message=final_post_text, file=photo_path, parse_mode='html')
                    try: os.remove(photo_path)
                    except Exception: pass
                else:
                    msg = await client.send_message(entity=config.AI_TARGET_CHANNEL, message=final_post_text, parse_mode='html')
                
                now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')
                channel_username = config.AI_TARGET_CHANNEL.replace('@', '')
                post_link = f"https://t.me/{channel_username}/{msg.id}" if msg else ""
                
                ws.update_cell(row_idx, 6, "published")
                ws.update_cell(row_idx, 8, now_str)
                ws.update_cell(row_idx, 9, post_link)
                
                print(f"✅ [QUEUE] Пост {queued_post[0]} успішно опубліковано з черги!")
                return
        except Exception as e:
            print(f"⚠️ [QUEUE] Помилка роботи з чергою Google Таблиць: {e}. Переходжу до живого автопостингу...")

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

        # Генерація картинки через ІІ з накладенням рамки
        photo_path = "temp_ai_post.jpg"
        generated_ok = await generate_ai_image(final_post_text, "ai", photo_path)
        if not generated_ok:
            # Запасний варіант: якщо у донора є фото, скачуємо його та рамкуємо
            if chosen_item and chosen_item["has_photo"]:
                try:
                    photo_path = await client.download_media(chosen_item["message_obj"], file="temp_ai_post.jpg")
                    if contains_russian_text(photo_path):
                        print("🚫 Скачана картинка містить російський текст! Відхиляємо та пробуємо примусово перегенерувати через ШІ...")
                        try: os.remove(photo_path)
                        except Exception: pass
                        photo_path = "temp_ai_post.jpg"
                        generated_ok = await generate_ai_image(final_post_text, "ai", photo_path)
                    else:
                        apply_brand_frame(photo_path, "ai")
                        generated_ok = True
                except Exception as e:
                    print(f"⚠️ Помилка скачування оригінальної картинки: {e}")
                    photo_path = None
            else:
                photo_path = None
        
        if not generated_ok:
            photo_path = None


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
        
        # Генерація картинки через ІІ з накладенням рамки
        photo_path = "digest_photo.jpg"
        generated_ok = await generate_ai_image(digest_text, "trading", photo_path)
        if not generated_ok:
            # Запасний варіант: шукаємо першу ліпшу картинку серед донорів
            for item in news_items:
                if item["has_photo"]:
                    try:
                        photo_path = await client.download_media(item["message_obj"], file="digest_photo.jpg")
                        apply_brand_frame(photo_path, "trading")
                        generated_ok = True
                        break
                    except Exception:
                        continue
                        
        # Якщо не вийшло згенерувати і немає у донорів, спробуємо дефолтні малюнки
        if not generated_ok and (not photo_path or not os.path.exists(photo_path)):
            if os.path.exists("sunday_digest_default.png"):
                import shutil
                shutil.copy("sunday_digest_default.png", "digest_photo.png")
                photo_path = "digest_photo.png"
                generated_ok = True
            elif os.path.exists("morning_default.png"):
                import shutil
                shutil.copy("morning_default.png", "digest_photo.png")
                photo_path = "digest_photo.png"
                apply_brand_frame(photo_path, "trading")
                generated_ok = True
            else:
                photo_path = None
        
        if not generated_ok:
            photo_path = None

                
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
    """Збирає якісні корисні пости з психології з глибини історії каналів-донорів"""
    news_list = []
    print("📥 Збираю корисні пости з глибини історії психології...")
    for channel in PSY_CHANNELS:
        try:
            print(f"📡 Зчитую канал @{channel} (до 150 постів)...")
            async for message in client.iter_messages(channel, limit=150):
                text = message.text or message.message
                if text and len(text.strip()) > 50:
                    if not is_ad_or_invalid_psy_post(text):
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
    if not api_key or api_key.startswith('AQ.'):
        api_key = config.GEMINI_API_KEY
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
        # 1. Спробуємо знайти пост у черзі в Google Таблиці
        try:
            ws = get_posts_queue_worksheet()
            rows = ws.get_all_values()
            queued_post = None
            row_idx = -1
            
            if len(rows) > 1:
                for idx, row in enumerate(rows[1:], start=2):
                    if len(row) > 5 and row[1] == 'psy' and row[2] == category_name and row[5] == 'pending':
                        queued_post = row
                        row_idx = idx
                        break
                        
            if queued_post:
                print(f"🎯 [QUEUE] Знайдено запланований пост з ID {queued_post[0]} для категорії '{category_name}'!")
                final_post_text = queued_post[3]
                photo_path = queued_post[4]
                
                # Публікуємо через Telethon (від імені користувача Клава)
                if photo_path and os.path.exists(photo_path):
                    await client.send_message(entity=config.PSY_TARGET_CHANNEL, message=final_post_text, file=photo_path, parse_mode='html')
                    try: os.remove(photo_path)
                    except Exception: pass
                else:
                    await client.send_message(entity=config.PSY_TARGET_CHANNEL, message=final_post_text, parse_mode='html')
                
                now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')
                
                # Отримуємо ID останнього надісланого повідомлення в каналі для формування лінку
                post_link = ""
                try:
                    async for msg in client.iter_messages(config.PSY_TARGET_CHANNEL, limit=1):
                        channel_username = config.PSY_TARGET_CHANNEL.replace('@', '')
                        post_link = f"https://t.me/{channel_username}/{msg.id}"
                        break
                except Exception:
                    pass
                
                ws.update_cell(row_idx, 6, "published")
                ws.update_cell(row_idx, 8, now_str)
                ws.update_cell(row_idx, 9, post_link)
                
                print(f"✅ [QUEUE] Пост {queued_post[0]} успішно опубліковано з черги!")
                return
        except Exception as e:
            print(f"⚠️ [QUEUE] Помилка роботи з чергою Google Таблиць: {e}. Переходжу до живого автопостингу...")

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

        # Генерація картинки через ІІ з накладенням рамки
        photo_path = "temp_psy_post.jpg"
        generated_ok = await generate_ai_image(final_post_text, "psy", photo_path)
        if not generated_ok:
            # Запасний варіант: якщо у донора є фото, скачуємо його та рамкуємо
            if chosen_item and chosen_item["has_photo"]:
                try:
                    photo_path = await client.download_media(chosen_item["message_obj"], file="temp_psy_post.jpg")
                    if contains_russian_text(photo_path):
                        print("🚫 Скачана картинка містить російський текст! Відхиляємо та пробуємо примусово перегенерувати через ШІ...")
                        try: os.remove(photo_path)
                        except Exception: pass
                        photo_path = "temp_psy_post.jpg"
                        generated_ok = await generate_ai_image(final_post_text, "psy", photo_path)
                    else:
                        apply_brand_frame(photo_path, "psy")
                        generated_ok = True
                except Exception as e:
                    print(f"⚠️ Помилка скачування оригінальної картинки: {e}")
                    photo_path = None
            else:
                photo_path = None
                
        # Дефолтний дежурний малюнок, якщо нічого не підібрали і ІІ не спрацював
        if not generated_ok and (not photo_path or not os.path.exists(photo_path)):
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
