import config
import requests
from telethon import events
import asyncio
import random

# Завантажуємо список каналів з конфігурації
TARGET_CHANNELS = getattr(config, 'COMMENT_CHANNELS', ['doubletop', 'Binance_UA_official'])

def get_gemini_comment(post_text):
    if not config.GEMINI_API_KEY:
        return "Цікаво, будемо спостерігати за ринком! 👀"
    try:
        # Обрізаємо дуже довгі тексти, щоб не витрачати токени
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
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            comment = data['candidates'][0]['content']['parts'][0]['text'].strip()
            # Видаляємо зайві лапки, якщо нейромережа їх додала
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

async def send_safe_reaction(client, chat_id, message_id, emoticon=None):
    """Безпечно надсилає реакцію на повідомлення, ігноруючи помилки обмежень каналу"""
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
        print(f"✅ Реакцію '{emoticon}' успішно встановлено на повідомлення {message_id}!")
        return True
    except Exception as e:
        print(f"⚠️ Не вдалося встановити реакцію '{emoticon}': {e}")
        return False

def register_commenter(client):
    """Реєструє обробники подій для автокомментування та автореакцій"""
    
    print(f"📡 Автокоментатор налаштовано для каналів: {TARGET_CHANNELS}")
    
    # 1. Реакції на нові пости у нашому власному каналі (@cem_copok)
    @client.on(events.NewMessage(chats=[config.TARGET_CHANNEL]))
    async def own_channel_handler(event):
        try:
            print(f"🔔 Новий пост у нашому каналі {config.TARGET_CHANNEL}! Готуюсь поставити лайк...")
            # Імітуємо перегляд поста людиною (затримка від 5 до 15 секунд)
            delay = random.uniform(5.0, 15.0)
            await asyncio.sleep(delay)
            
            # Вибираємо випадкову яскраву позитивну емодзі
            emoticon = random.choice(['🔥', '👍', '❤️', '🚀', '👏', '🤩'])
            await send_safe_reaction(client, event.chat_id, event.message.id, emoticon)
        except Exception as e:
            print(f"❌ Помилка в обробнику нашого каналу: {e}")

    # 2. Автокоментарі та реакції для чужих цільових каналів
    @client.on(events.NewMessage(chats=TARGET_CHANNELS))
    async def handler(event):
        try:
            # Отримуємо назву каналу
            chat = await event.get_chat()
            channel_name = chat.username if chat.username else str(chat.id)
            
            post_text = event.raw_text
            
            # Пропускаємо порожні або занадто короткі повідомлення (опитування, стікери, картини без тексту)
            if not post_text or len(post_text.strip()) < 15:
                print(f"⏭️ [@{channel_name}] Пост занадто короткий або порожній. Пропускаю.")
                return
                
            print(f"📝 [{event.date}] Новий пост у каналі @{channel_name}! Генерую розумний коментар...")
            
            # Виконуємо синхронний запит до Gemini у фоновому потоці, щоб не блокувати Telethon
            loop = asyncio.get_event_loop()
            comment = await loop.run_in_executor(None, get_gemini_comment, post_text)
            
            if not comment:
                print("⚠️ Не вдалося згенерувати коментар через Gemini.")
                return
                
            if comment.strip().upper() == "SKIP":
                print(f"🇬🇧 [@{channel_name}] Пост англійською мовою. Коментар пропускаємо, але ставимо реакцію...")
                # Імітуємо перегляд людиною
                await asyncio.sleep(random.uniform(5.0, 12.0))
                emoticon = random.choice(['👍', '🔥', '❤️', '🚀', '👏', '🤩'])
                await send_safe_reaction(client, event.chat_id, event.message.id, emoticon)
                return
                
            # Імітуємо поведінку людини: затримка на читання та друкування (від 15 до 45 секунд)
            delay = random.uniform(15.0, 45.0)
            print(f"⏳ [@{channel_name}] Очікую {delay:.1f} сек для природності перед відправкою...")
            await asyncio.sleep(delay)
            
            # Відправляємо коментар
            try:
                await client.send_message(entity=event.chat_id, message=comment, comment_to=event.message)
                print(f"✅ [@{channel_name}] Коментар успішно опубліковано: {comment}")
                
                # Відправляємо лайк/реакцію на пост каналу через 1-3 секунди після відправки коментаря
                await asyncio.sleep(random.uniform(1.0, 3.0))
                emoticon = random.choice(['👍', '🔥', '❤️', '🚀', '👏', '🤩'])
                print(f"👍 [@{channel_name}] Ставлю лайк/реакцію на пост...")
                await send_safe_reaction(client, event.chat_id, event.message.id, emoticon)
                
            except Exception as send_err:
                print(f"❌ [@{channel_name}] Помилка при відправці коментаря: {send_err}")
                print(f"👉 ПІДКАЗКА: Переконайтеся, що ваш юзербот вступив у чат обговорення (group/chat) для каналу @{channel_name}!")
            
        except Exception as e:
            print(f"❌ Не вдалося обробити новий пост: {e}")


