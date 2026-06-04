import os
import sys
import sqlite3
import asyncio
import urllib.request
import urllib.parse

# Додаємо батьківську директорію до шляху імпорту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import config

async def main():
    db_path = "klava.session"
    if not os.path.exists(db_path):
        print(f"Помилка: Файл {db_path} не знайдено.")
        return

    print("====================================================")
    print("🤖 АВТОРИЗАЦІЯ TELETHON ЧЕРЕЗ QR-КОД")
    print("====================================================")

    # Очищуємо недійсний ключ авторизації
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions")
        cursor.execute("DELETE FROM update_state")
        conn.commit()
        conn.close()
        print("✅ Старий недійсний ключ успішно видалено з klava.session!")
    except Exception as e:
        print(f"⚠️ Помилка при очищенні бази сесії: {e}")

    client = TelegramClient('klava', config.API_ID, config.API_HASH)
    
    print("\n🚀 Підключення до Telegram...")
    await client.connect()

    print("⏳ Ініціалізація запиту QR-коду...")
    qr_login = await client.qr_login()
    
    # Створюємо папку .tmp, якщо її немає
    os.makedirs(".tmp", exist_ok=True)
    qr_image_path = os.path.join(".tmp", "qr.png")

    while True:
        # Отримуємо URL для сканування (формат tg://login?token=...)
        url = qr_login.url
        print(f"\n🔗 Отримано лінк для QR: {url}")
        
        # Завантажуємо зображення QR-коду через публічний API
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?data={urllib.parse.quote(url)}&size=300x300"
        try:
            print("⏳ Завантажуємо зображення QR-коду...")
            urllib.request.urlretrieve(api_url, qr_image_path)
            abs_path = os.path.abspath(qr_image_path)
            print("====================================================")
            print(f"🎉 QR-КОД ЗГЕНЕРОВАНО ТА ЗБЕРЕЖЕНО!")
            print(f"👉 Відкрийте файл зображення:")
            print(f"   [qr.png](file:///{abs_path.replace(os.sep, '/')})")
            print("====================================================")
            print("📱 Як сканувати:")
            print("1. Відкрийте Telegram на вашому телефоні.")
            print("2. Перейдіть у Налаштування > Пристрої > Підключити пристрій (Settings > Devices > Link Desktop Device).")
            print("3. Наведіть камеру на відкритий файл qr.png.")
            print("====================================================")
            print("⏳ Очікуємо на сканування (дійсний протягом 60 секунд)...")
        except Exception as e:
            print(f"❌ Не вдалося зберегти QR-код: {e}")
            await client.disconnect()
            return

        try:
            # Очікуємо на сканування
            user = await qr_login.wait(timeout=60)
            print("\n====================================================")
            print("✅ Успішно авторизовано через QR-код!")
            print(f"Увійшли як: {user.first_name} (@{user.username})")
            print("====================================================")
            break
        except asyncio.TimeoutError:
            print("\n⏰ Час дії QR-коду закінчився. Генеруємо новий...")
            qr_login = await client.qr_login()
        except SessionPasswordNeededError:
            # Якщо увімкнено двофакторну аутентифікацію (2FA Cloud Password)
            print("\n🔑 Сканування пройшло успішно, але потрібен пароль двофакторної аутентифікації.")
            password = input("Введіть ваш хмарний пароль (2FA): ").strip()
            try:
                user = await client.sign_in(password=password)
                print("====================================================")
                print("✅ Успішна авторизація з паролем 2FA!")
                print(f"Увійшли як: {user.first_name} (@{user.username})")
                print("====================================================")
                break
            except Exception as p_err:
                print(f"❌ Помилка вводу пароля: {p_err}")
                await client.disconnect()
                return
        except Exception as e:
            print(f"❌ Сталася помилка під час авторизації: {e}")
            await client.disconnect()
            return

    await client.disconnect()

if __name__ == "__main__":
    # Переходимо в робочу директорію бота, щоб сесія створювалась/оновлювалась там
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
