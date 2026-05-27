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

# Одноразові тестові функції для вечірнього тесту за запитом користувача
def temp_morning_job():
    print("⏰ Тимчасовий тестовий ранковий пост (20:31) запущено!")
    try:
        run_poster()
    except Exception as e:
        print(f"Помилка під час тестового ранкового поста: {e}")
    return schedule.CancelJob

def temp_noon_job():
    print("⏰ Тимчасовий тестовий денний пост (20:45) запущено!")
    try:
        run_news_poster()
    except Exception as e:
        print(f"Помилка під час тестового денного поста: {e}")
    return schedule.CancelJob

# Запуск кожен день по Києву (з явним вказанням часового поясу Europe/Kyiv)
schedule.every().day.at(config.MORNING_POST_TIME, "Europe/Kyiv").do(morning_job)
schedule.every().day.at("12:00", "Europe/Kyiv").do(noon_job)

# Тимчасові ОДНОРАЗОВІ тестові запуски ввечері (о 20:31 та 20:45 за Києвом)
schedule.every().day.at("20:31", "Europe/Kyiv").do(temp_morning_job)
schedule.every().day.at("20:45", "Europe/Kyiv").do(temp_noon_job)

if __name__ == "__main__":
    print("=" * 45)
    print("   🤖 КРИПТО-БОТ ЗАПУЩЕНО")
    print("=" * 45)
    print(f"📅 Розклад ранковий: щодня о {config.MORNING_POST_TIME} (Київ)")
    print("📅 Розклад денний:   щодня о 12:00 (Київ)")
    print("📅 Тестовий запуск:   сьогодні ввечері о 20:31 та 20:45 (Київ) [Одноразово]")
    print(f"📢 Канал: {config.TARGET_CHANNEL}")
    print("⏳ Очікую часу публікації...")
    print("   (Щоб зупинити бота, закрийте це вікно)")
    print("-" * 45)

    while True:
        schedule.run_pending()
        time.sleep(30)
