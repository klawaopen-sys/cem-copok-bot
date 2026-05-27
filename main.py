import schedule
import time
from poster import run_poster
from news_poster import run_news_poster
import config

def morning_job():
    print(f"⏰ Час {config.MORNING_POST_TIME}! Запускаю ранковий фінансовий огляд...")
    run_poster()

def noon_job():
    print("⏰ Час 12:00! Запускаю денний огляд новин...")
    run_news_poster()

# Запуск каждый день по Киеву
schedule.every().day.at(config.MORNING_POST_TIME).do(morning_job)
schedule.every().day.at("12:00").do(noon_job)

if __name__ == "__main__":
    print("=" * 45)
    print("   🤖 КРИПТО-БОТ ЗАПУЩЕНО")
    print("=" * 45)
    print(f"📅 Розклад ранковий: щодня о {config.MORNING_POST_TIME} (Київ)")
    print("📅 Розклад денний:   щодня о 12:00 (Київ)")
    print(f"📢 Канал: {config.TARGET_CHANNEL}")
    print("⏳ Очікую часу публікації...")
    print("   (Щоб зупинити бота, закрийте це вікно)")
    print("-" * 45)

    while True:
        schedule.run_pending()
        time.sleep(30)
