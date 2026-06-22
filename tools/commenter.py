import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import requests
from telethon import events
import asyncio
import random
import re
import os
from PIL import Image

# Завантаження налаштувань
TARGET_CHANNELS = getattr(config, 'COMMENT_CHANNELS', [])
TRADING_DONOR_CHANNELS = getattr(config, 'TRADING_DONOR_CHANNELS', [])
PSY_DONOR_CHANNELS = getattr(config, 'PSY_DONOR_CHANNELS', [])
REAL_ESTATE_CHANNELS = getattr(config, 'REAL_ESTATE_CHANNELS', [])
MANICURE_CHANNELS = getattr(config, 'MANICURE_CHANNELS', [])

def get_gemini_real_estate_comment(post_text):
    """Генерує розумний коментар до поста про нерухомість через Gemini"""
    if not config.GEMINI_API_KEY:
        return "Цікавий об'єкт, варто придивитися! 👀"
    try:
        post_text = post_text[:2000] if post_text else ""
        prompt = (
            "Ти — досвідчений і доброзичливий ріелтор, спеціаліст з нерухомості та інвестор.\n"
            "Напиши короткий, змістовний і природний коментар (1-2 речення) до наступного поста про нерухомість.\n\n"
            "ВАЖЛИВО:\n"
            "1. Якщо вихідний пост написаний АНГЛІЙСЬКОЮ мовою, НЕ пиши коментар взагалі. Натомість поверни ТІЛЬКИ одне слово: SKIP.\n"
            "2. Якщо пост написаний іншою мовою (українська, російська тощо) — напиши коментар ТІЄЮ Ж МОВОЮ, якою написаний сам пост. Коментар має виглядати так, ніби його написала жива людина в Telegram-чаті (простий, розмовний і вільний стиль без зайвої офіційності).\n\n"
            "КРИТИЧНО ВАЖЛИВЕ ПРАВИЛО (якщо не повернуто SKIP):\n"
            "Обов'язково закінчуй свій коментар коротким, природним та залучаючим питанням до учасників чату ТІЄЮ Ж МОВОЮ про нерухомість, ціни, ремонт чи оренду, щоб спровокувати обговорення "
            "(наприклад, якщо пишеш українською: 'Як думаєте, ціна адекватна для цього району чи завищена?', якщо російською: 'Как думаете, цена адекватная для этого района или завышена?').\n\n"
            "Суворі обмеження:\n"
            "- НЕ використовуй хештеги, привітання або будь-які формальності.\n"
            "- Не пиши ніякої реклами, посилань чи закликів підписуватись.\n"
            "- Текст коментаря має бути коротким, живим та ємним.\n\n"
            f"Текст поста:\n{post_text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        from tools.gemini_client import gemini_post_with_retry
        r = gemini_post_with_retry(url, headers, payload, timeout=15)
        if r.status_code == 200:
            comment = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]
            if comment.startswith('«') and comment.endswith('»'):
                comment = comment[1:-1]
            return comment
        else:
            print(f"Помилка Gemini API в коментарях про нерухомість: {r.status_code}")
    except Exception as e:
        print(f"Помилка генерації коментаря про нерухомість: {e}")
    return "Цікавий варіант, треба обдумати! 👀"

def get_gemini_manicure_comment(post_text):
    """Генерує розумний коментар до б'юті-посту про манікюр через Gemini"""
    if not config.GEMINI_API_KEY:
        return "Дуже гарний манікюр! 😍"
    try:
        post_text = post_text[:2000] if post_text else ""
        prompt = (
            "Ти — досвідчений nail-майстер (майстер манікюру) або б'юті-ентузіаст, який обожнює стильний та доглянутий манікюр.\n"
            "Напиши короткий, дружній і захоплений коментар (1-2 речення) до наступного поста про манікюр, дизайн чи догляд за руками.\n\n"
            "ВАЖЛИВО:\n"
            "1. Якщо вихідний пост написаний АНГЛІЙСЬКОЮ мовою, НЕ пиши коментар взагалі. Натомість поверни ТІЛЬКИ одне слово: SKIP.\n"
            "2. Якщо пост написаний іншою мовою (українська, російська тощо) — напиши коментар ТІЄЮ Ж МОВОЮ, якою написаний сам пост. Коментар має виглядати так, ніби його написала жива людина в Telegram-чаті (простий, розмовний і вільний стиль без зайвої офіційності, з використанням емодзі).\n\n"
            "КРИТИЧНО ВАЖЛИВЕ ПРАВИЛО (якщо не повернуто SKIP):\n"
            "Обов'язково закінчуй свій коментар коротким, природним та залучаючим питанням про дизайн, вибір кольору чи техніку ТІЄЮ Ж МОВОЮ, щоб спровокувати обговорення "
            "(наприклад, якщо пишеш українською: 'Як вам такий відтінок, ризикнули б зробити собі?', якщо російською: 'Как вам такой оттенок, рискнули бы сделать себе?').\n\n"
            "Суворі обмеження:\n"
            "- НЕ використовуй хештеги, привітання або будь-які формальності.\n"
            "- Не пиши ніякої реклами, посилань чи закликів підписуватись.\n"
            "- Текст коментаря має бути коротким, живим та ніжним.\n\n"
            f"Текст поста:\n{post_text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        from tools.gemini_client import gemini_post_with_retry
        r = gemini_post_with_retry(url, headers, payload, timeout=15)
        if r.status_code == 200:
            comment = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]
            if comment.startswith('«') and comment.endswith('»'):
                comment = comment[1:-1]
            return comment
        else:
            print(f"Помилка Gemini API в коментарях про манікюр: {r.status_code}")
    except Exception as e:
        print(f"Помилка генерації коментаря про манікюр: {e}")
    return "Виглядає просто чудово! 😍"

def get_gemini_comment(post_text):
    """Генерує розумний коментар до трейдинг-посту через Gemini"""
    if not config.GEMINI_API_KEY:
        return "Цікаво, будемо спостерігати за ринком! 👀"
    try:
        post_text = post_text[:2000] if post_text else ""
        prompt = (
            "Ти — досвідчений і трохи іронічний крипто-трейдер та інвестор. "
            "Напиши короткий, змістовний і максимально природний коментар (1-2 речення) до наступного поста.\n\n"
            "ВАЖЛИВО:\n"
            "1. Якщо вихідний пост написаний АНГЛІЙСЬКОЮ мовою, НЕ пиши коментар взагалі. Натомість поверни ТІЛЬКИ одне слово: SKIP.\n"
            "2. Якщо пост написаний іншою мовою (українська, російська тощо) — напиши коментар ТІЄЮ Ж МОВОЮ, якою написаний сам пост. Коментар має виглядати так, ніби його написала жива людина в Telegram-чаті (простий, розмовний і вільний стиль без зайвої офіційності).\n\n"
            "КРИТИЧНО ВАЖЛИВЕ ПРАВИЛО (якщо не повернуто SKIP):\n"
            "Обов'язково закінчуй свій коментар коротким, природним та залучаючим питанням до учасників чату ТІЄЮ Ж МОВОЮ, щоб спровокувати обговорення "
            "(наприклад, якщо пишеш українською: 'Як думаєте, полетимо вище чи це чергова пастка для биків?', якщо російською: 'Как думаете, пойдем выше или это ловушка?').\n\n"
            "Суворі обмеження:\n"
            "- НЕ використовуй хештеги, привітання або будь-які формальності.\n"
            "- Не пиши ніякої реклами, посилань чи закликів підписуватись.\n"
            "- Текст коментаря має бути коротким, живим та ємним.\n\n"
            f"Текст поста:\n{post_text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        from tools.gemini_client import gemini_post_with_retry
        r = gemini_post_with_retry(url, headers, payload, timeout=15)
        if r.status_code == 200:
            comment = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]
            if comment.startswith('«') and comment.endswith('»'):
                comment = comment[1:-1]
            return comment
        else:
            print(f"Помилка Gemini API в коментарях: {r.status_code}")
    except Exception as e:
        print(f"Помилка генерації коментаря: {e}")
    return "Цікаво, подивимось що з цього вийде! 👀"

def get_gemini_psychology_rewrite(post_text):
    """Використовує Gemini для унікального рерайту психологічного поста українською мовою"""
    if not config.GEMINI_API_KEY:
        return post_text
    try:
        post_text = post_text[:2000] if post_text else ""
        prompt = (
            "Ти — професійний психолог, автор популярного Telegram-каналу про психологію та саморозвиток.\n"
            "Твоє завдання — перекласти та переписати наступний пост українською мовою. Зроби його унікальним, цікавим та легким для сприйняття.\n\n"
            "КРИТИЧНО ВАЖЛИВІ ПРАВИЛА:\n"
            "1. Пост має бути написаний красивою, грамотною українською мовою з професійним, але розмовним і захоплюючим тоном.\n"
            "2. Структуруй текст: використовуй абзаци, списки та доречні емодзі.\n"
            "3. Використовуй ТІЛЬКИ HTML-теги для виділення жирного тексту: <b>жирний текст</b>. НІКОЛИ не використовуй маркдаун із зірочками (** або *).\n"
            "4. Текст має бути лаконічним і СТРОГО до 650-700 символів (разом із пробілами), оскільки він буде підписом до фотографії, ліміт якої в Telegram становить 1024 символи.\n"
            "5. Напиши ТІЛЬКИ текст рерайту без будь-яких вступних слів, привітань, лапок чи завершальних фраз. Починай одразу з суті.\n\n"
            f"Оригінальний пост:\n{post_text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        from tools.gemini_client import gemini_post_with_retry
        r = gemini_post_with_retry(url, headers, payload, timeout=30)
        if r.status_code == 200:
            rewrite = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if rewrite.startswith('"') and rewrite.endswith('"'):
                rewrite = rewrite[1:-1]
            if rewrite.startswith('«') and rewrite.endswith('»'):
                rewrite = rewrite[1:-1]
            return rewrite
    except Exception as e:
        print(f"❌ Помилка під час рерайту через Gemini: {e}")
    return None

async def send_safe_reaction(client, chat_id, message_id, emoticon=None):
    """Безпечно надсилає реакцію на повідомлення"""
    if not emoticon:
        emoticon = random.choice(['👍', '🔥', '❤️', '🚀', '👏', '🤩'])
    try:
        from telethon.tl.functions.messages import SendReactionRequest
        from telethon.tl.types import ReactionEmoji
        await client(SendReactionRequest(
            peer=chat_id,
            msg_id=message_id,
            reaction=[ReactionEmoji(emoticon=emoticon)]
        ))
        return True
    except Exception:
        return False

def apply_watermark(photo_path):
    """Накладає брендований водяний знак logo.jpg на фотографію"""
    try:
        logo_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp", "logo.jpg")
        if photo_path and os.path.exists(photo_path) and os.path.exists(logo_file):
            print("🎨 Накладаю водяний знак бренду...")
            main_img = Image.open(photo_path).convert("RGBA")
            logo = Image.open(logo_file).convert("RGBA")
            
            # Робимо білий фон логотипу прозорим
            datas = logo.getdata()
            new_data = []
            for item in datas:
                if item[0] > 220 and item[1] > 220 and item[2] > 220:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append((item[0], item[1], item[2], int(item[3] * 0.8)))
            logo.putdata(new_data)
            
            # Масштабуємо лого до 12.5% ширини фото
            logo_width = int(main_img.width * 0.125)
            aspect_ratio = logo.height / logo.width
            logo_height = int(logo_width * aspect_ratio)
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            # Позиція внизу праворуч
            padding = int(main_img.width * 0.03)
            position = (main_img.width - logo_width - padding, main_img.height - logo_height - padding)
            
            transparent = Image.new('RGBA', main_img.size, (0,0,0,0))
            transparent.paste(logo, position)
            
            result = Image.alpha_composite(main_img, transparent)
            result.convert("RGB").save(photo_path, "JPEG")
            print("✅ Водяний знак успішно накладено!")
            return True
    except Exception as e:
        print(f"⚠️ Не вдалося накласти водяний знак: {e}")
    return False

def auto_replace_links(text):
    """Автоматично шукає посилання на канал @l_ibrar_y та перетворює їх на посилання на бота-бібліотекаря"""
    if not text:
        return text
    pattern = r'https?://t\.me/l_ibrar_y/(\d+)'
    return re.sub(pattern, r'https://t.me/librar_ian_bot?start=\1', text)

async def register_commenter(client):
    """Реєструє обробники подій Telethon для всієї екосистеми супер-бота"""
    
    # ---------------------------------------------------------------------
    # А. Універсальний глобальний обробник нових постів у всіх підписаних каналах
    # ---------------------------------------------------------------------
    @client.on(events.NewMessage())
    async def global_channel_handler(event):
        # Реагуємо тільки на пости в каналах (ігноруємо приватні діалоги та звичайні групи)
        if not event.is_channel or not event.post:
            return
            
        try:
            chat = await event.get_chat()
            channel_id = event.chat_id
            channel_username = chat.username if chat.username else str(chat.id)
            channel_title = chat.title if hasattr(chat, 'title') else "Канал"
            
            # Визначаємо, чи це наш власний канал
            our_usernames = [
                config.TARGET_CHANNEL.replace('@', '').strip().lower() if hasattr(config, 'TARGET_CHANNEL') else '',
                config.PSY_TARGET_CHANNEL.replace('@', '').strip().lower() if hasattr(config, 'PSY_TARGET_CHANNEL') else '',
                config.AI_TARGET_CHANNEL.replace('@', '').strip().lower() if hasattr(config, 'AI_TARGET_CHANNEL') else ''
            ]
            is_our_channel = (
                channel_username.lower() in our_usernames or 
                str(channel_id) in our_usernames or
                channel_id in [2231119273, 2108752101, 2049134376, 2147858686] # Відомі ID наших каналів
            )
            
            # Визначаємо, чи це канал для коментування трейдингу
            comment_usernames = [c.lower().strip() for c in TARGET_CHANNELS]
            is_comment_channel = (
                channel_username.lower() in comment_usernames or 
                str(channel_id) in comment_usernames
            )
            
            # Визначаємо, чи це канал для коментування нерухомості
            re_usernames = [c.lower().strip() for c in REAL_ESTATE_CHANNELS]
            is_re_channel = (
                channel_username.lower() in re_usernames or 
                str(channel_id) in re_usernames
            )
            
            # Визначаємо, чи це канал для коментування манікюру
            manicure_usernames = [c.lower().strip() for c in MANICURE_CHANNELS]
            is_manicure_channel = (
                channel_username.lower() in manicure_usernames or 
                str(channel_id) in manicure_usernames
            )
            
            # --- 1. АВТОМАТИЧНИЙ ЛАЙК ДЛЯ ВСІХ ПІДПИСАНИХ КАНАЛІВ (Включаючи ті, де Клава адмін або просто підписана) ---
            print(f"👍 [{channel_title} (@{channel_username})] Новий пост! Ставлю автолайк...")
            await asyncio.sleep(random.uniform(2.0, 7.0))
            await send_safe_reaction(client, event.chat_id, event.message.id)
            
            # --- 2. НАШІ КАНАЛИ: Автозаміна посилань на бота-бібліотекаря ---
            if is_our_channel:
                post_text = event.message.text or event.message.message
                if post_text and "t.me/l_ibrar_y/" in post_text:
                    print(f"🔗 Виявлено посилання на бібліотеку в нашому каналі {channel_title}! Замінюю...")
                    new_text = auto_replace_links(post_text)
                    await client.edit_message(
                        entity=event.chat_id,
                        message=event.message.id,
                        text=new_text,
                        parse_mode='html'
                    )
                    print("✅ Посилання успішно замінено на бота-бібліотекаря!")
                    
            # --- 3. ЧУЖІ КАНАЛИ ТРЕЙДИНГУ/НЕРУХОМОСТІ/МАНІКЮРУ: Розумне автокоментування через Gemini ---
            elif is_comment_channel or is_re_channel or is_manicure_channel:
                post_text = event.raw_text
                if not post_text or len(post_text.strip()) < 15:
                    return
                    
                print(f"📝 [{channel_title}] Генерую розумний коментар...")
                loop = asyncio.get_event_loop()
                
                if is_re_channel:
                    comment = await loop.run_in_executor(None, get_gemini_real_estate_comment, post_text)
                elif is_manicure_channel:
                    comment = await loop.run_in_executor(None, get_gemini_manicure_comment, post_text)
                else:
                    comment = await loop.run_in_executor(None, get_gemini_comment, post_text)
                
                if not comment or comment.strip().upper() == "SKIP":
                    return
                    
                # Публікація коментаря з природною затримкою
                delay = random.uniform(15.0, 45.0)
                await asyncio.sleep(delay)
                await client.send_message(entity=event.chat_id, message=comment, comment_to=event.message)
                print(f"✅ [{channel_title}] Коментар опубліковано: {comment}")
                
        except Exception as e:
            print(f"❌ Помилка в глобальному обробнику каналів: {e}")

    # ---------------------------------------------------------------------
    # В. Режим ДОНОРА для акцій Трейдингу (Binance)
    # ---------------------------------------------------------------------
    if TRADING_DONOR_CHANNELS:
        valid_trading_donors = []
        for ch in TRADING_DONOR_CHANNELS:
            try:
                await client.get_input_entity(ch)
                valid_trading_donors.append(ch)
                print(f"✅ Канал-донор трейдингу '{ch}' успішно перевірений та доступний.")
            except Exception as e:
                print(f"⚠️ Канал-донор трейдингу '{ch}' пропущено: {e}")
                
        async def trading_donor_handler(event):
            try:
                chat = await event.get_chat()
                channel_name = chat.username if chat.username else str(chat.id)
                post_text = event.message.text or event.message.message
                if not post_text: return
                
                # Перевіряємо на промо
                post_text_lower = post_text.lower()
                promo_keywords = ["промо", "акція", "акция", "конкурс", "розіграш", "бонус", "заробити", "launchpool", "megadrop"]
                is_promo = any(kw in post_text_lower for kw in promo_keywords) or "binance.com" in post_text_lower
                
                if not is_promo: return
                print(f"📣 [@{channel_name}] Виявлено промо-акцію Binance! Репощу...")
                
                # Підставляємо рефку
                ref_link = config.REFERRAL_LINKS.get("Binance", "")
                if ref_link:
                    post_text = re.sub(r'https?://[^\s)]*binance\.com[^\s)]*', ref_link, post_text)
                
                # Автозаміна посилань на бібліотеку (про всяк випадок)
                post_text = auto_replace_links(post_text)
                
                # Картинка + Водяний знак
                photo_path = None
                if event.message.photo:
                    photo_path = await client.download_media(event.message, file=".tmp/temp_trade_promo.jpg")
                    apply_watermark(photo_path)
                
                from aiogram import Bot
                from aiogram.types import FSInputFile
                bot = Bot(token=config.BOT_TOKEN)
                try:
                    if photo_path and os.path.exists(photo_path):
                        if len(post_text) <= 1024:
                            await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path), caption=post_text, parse_mode='HTML')
                        else:
                            msg_photo = await bot.send_photo(chat_id=config.TARGET_CHANNEL, photo=FSInputFile(photo_path))
                            await bot.send_message(chat_id=config.TARGET_CHANNEL, text=post_text, parse_mode='HTML', reply_to_message_id=msg_photo.message_id)
                    else:
                        await bot.send_message(chat_id=config.TARGET_CHANNEL, text=post_text, parse_mode='HTML')
                    print("✅ Промо-акцію Binance успішно опубліковано через Bot API!")
                finally:
                    await bot.session.close()
                if photo_path and os.path.exists(photo_path): os.remove(photo_path)
            except Exception as e:
                print(f"❌ Помилка донора трейдингу: {e}")

        if valid_trading_donors:
            print(f"📡 Авторепостер трейдингу налаштовано для доступних каналів-донорів: {valid_trading_donors}")
            client.add_event_handler(trading_donor_handler, events.NewMessage(chats=valid_trading_donors))

    # ---------------------------------------------------------------------
    # Г. Авторепостер для Психології (режим ДОНОРА з Gemini рерайтом) - ВИМКНЕНО НА КОРИСТЬ РОЗКЛАДУ
    # ---------------------------------------------------------------------
    # if PSY_DONOR_CHANNELS:
    #     @client.on(events.NewMessage(chats=PSY_DONOR_CHANNELS))
    #     async def psychology_donor_handler(event):
    #         try:
    #             chat = await event.get_chat()
    #             channel_name = chat.username if chat.username else str(chat.id)
    #             post_text = event.message.text or event.message.message
    #             if not post_text or len(post_text.strip()) < 30: return
    #             
    #             print(f"🧠 [@{channel_name}] Новий пост по психології. Надсилаю на рерайт...")
    #             rewritten = await asyncio.get_event_loop().run_in_executor(None, get_gemini_psychology_rewrite, post_text)
    #             if not rewritten: return
    #             
    #             final_text = rewritten + getattr(config, 'PSY_SIGNATURE', '')
    #             final_text = auto_replace_links(final_text)
    #             
    #             # Картинка + Ватермарк
    #             photo_path = None
    #             if event.message.photo:
    #                 photo_path = await client.download_media(event.message, file="temp_psy_post.jpg")
    #                 apply_watermark(photo_path)
    #             
    #             await client.send_message(entity=config.PSY_TARGET_CHANNEL, message=final_text, file=photo_path, parse_mode='html')
    #             print("✅ Психологічний пост опубліковано!")
    #             if photo_path and os.path.exists(photo_path): os.remove(photo_path)
    #         except Exception as e:
    #             print(f"❌ Помилка донора психології: {e}")
