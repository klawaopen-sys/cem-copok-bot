import schedule
import time
from poster import run_poster
import config

def job():
    print(f"⏰ Час {config.MORNING_POST_TIME}! Запускаю ранковий фінансовий огляд...")
    run_poster()

# Запуск каждый день в 07:40 по Киеву
schedule.every().day.at(config.MORNING_POST_TIME).do(job)

if __name__ == "__main__":
    print("=" * 45)
    print("   🤖 КРИПТО-БОТ ЗАПУЩЕНО")
    print("=" * 45)
    print(f"📅 Розклад: щодня о {config.MORNING_POST_TIME} (Київ)")
    print(f"📢 Канал: {config.TARGET_CHANNEL}")
    print("⏳ Очікую часу публікації...")
    print("   (Щоб зупинити бота, закрийте це вікно)")
    print("-" * 45)

    while True:
        schedule.run_pending()
        time.sleep(30)
