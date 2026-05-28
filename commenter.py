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
            "Ти — досвідчений крипто-трейдер та інвестор. "
            "Напиши короткий, змістовний і максимально природний коментар (1-2 речення українською) до наступного поста. "
            "Коментар має виглядати так, ніби його написала реальна людина в Telegram-чаті. "
            "НЕ використовуй хештеги, привітання, чи формальності. Не пиши ніякої реклами чи посилань. "
            "Просто суть, твоя думка або реакція на новину.\n\n"
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

def register_commenter(client):
    """Реєструє обробник подій для автокомментування"""
    
    print(f"📡 Автокоментатор налаштовано для каналів: {TARGET_CHANNELS}")
    
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
                
            # Імітуємо поведінку людини: затримка на читання та друкування (від 15 до 45 секунд)
            delay = random.uniform(15.0, 45.0)
            print(f"⏳ [@{channel_name}] Очікую {delay:.1f} сек для природності перед відправкою...")
            await asyncio.sleep(delay)
            
            # Відправляємо коментар
            try:
                await client.send_message(entity=event.chat_id, message=comment, comment_to=event.message)
                print(f"✅ [@{channel_name}] Коментар успішно опубліковано: {comment}")
            except Exception as send_err:
                print(f"❌ [@{channel_name}] Помилка при відправці коментаря: {send_err}")
                print(f"👉 ПІДКАЗКА: Переконайтеся, що ваш юзербот вступив у чат обговорення (group/chat) для каналу @{channel_name}!")
            
        except Exception as e:
            print(f"❌ Не вдалося обробити новий пост: {e}")

