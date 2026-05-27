import schedule
import time
import asyncio
import threading
from poster import run_poster
from news_poster import run_news_poster
from commenter import register_commenter
from telethon import TelegramClient
import config
import os

client = TelegramClient('klava', config.API_ID, config.API_HASH)
main_loop = None

def morning_job():
    print(f"⏰ Час {config.MORNING_POST_TIME}! Запускаю ранковий фінансовий огляд...")
    try:
        run_poster()
    except Exception as e:
        print(f"Помилка ранкового поста: {e}")

def noon_job():
    print("⏰ Час 12:00! Запускаю денний огляд новин...")
    try:
        if main_loop and client:
            run_news_poster(client, main_loop)
    except Exception as e:
        print(f"Помилка денного поста: {e}")

def schedule_thread_func():
    """Фоновий потік для перевірки розкладу"""
    while True:
        schedule.run_pending()
        time.sleep(30)

async def main():
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    print("=" * 45)
    print("   🤖 КРИПТО-БОТ (POSTER + COMMENTER)")
    print("=" * 45)
    
    if not os.path.exists("klava.session"):
        print("❌ Файл klava.session не знайдено! Юзербот не зможе працювати.")
        return

    await client.start()
    print("✅ Telethon юзербот підключено успішно!")
    
    # Реєструємо автокомментатор
    register_commenter(client)
    print("✅ Автокомментатор запущено (Слухаємо цільові канали)!")
    
    # Налаштовуємо розклад
    schedule.every().day.at(config.MORNING_POST_TIME, "Europe/Kyiv").do(morning_job)
    schedule.every().day.at("12:00", "Europe/Kyiv").do(noon_job)
    
    print(f"📅 Розклад ранковий: щодня о {config.MORNING_POST_TIME} (Київ)")
    print("📅 Розклад денний:   щодня о 12:00 (Київ)")
    print(f"📢 Канал: {config.TARGET_CHANNEL}")
    
    # Запускаємо розклад у фоновому потоці
    threading.Thread(target=schedule_thread_func, daemon=True).start()
    
    print("⏳ Очікую подій та часу публікації...")
    # Тримаємо програму відкритою і слухаємо Telethon події
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
