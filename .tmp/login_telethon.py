import os
import sys
import sqlite3
import asyncio

# Додаємо батьківську директорію до шляху імпорту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import config

async def main():
    db_path = "klava.session"
    if not os.path.exists(db_path):
        print(f"Помилка: Файл {db_path} не знайдено в поточній робочій директорії.")
        return

    print("====================================================")
    print("🤖 РЕАВТОРИЗАЦІЯ TELETHON ЮЗЕРБОТА 'КЛАВА'")
    print("====================================================")

    # Очищуємо недійсний ключ авторизації, зберігаючи саму структуру файлу
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

    # Запуск процесу авторизації
    client = TelegramClient('klava', config.API_ID, config.API_HASH)
    
    print("\n🚀 Підключення до Telegram...")
    await client.connect()
    
    phone = input("\nВведіть номер телефону (наприклад, +380992785867): ").strip()
    
    # Спробуємо надіслати код. Спочатку пробуємо force_sms=True. 
    # Якщо Telegram видасть помилку, спробуємо звичайний запит (який надходить у додаток).
    sent_code = None
    try:
        print("⏳ Запитуємо код через SMS (force_sms=True)...")
        sent_code = await client.send_code_request(phone, force_sms=True)
        print("✅ Telegram прийняв запит. Код надіслано в SMS!")
    except Exception as sms_err:
        print(f"⚠️ Не вдалося надіслати SMS (помилка: {sms_err}). Спробуємо надіслати код у додаток Telegram...")
        try:
            sent_code = await client.send_code_request(phone, force_sms=False)
            print("✅ Telegram прийняв запит. Код надіслано у додаток Telegram (перевірте активні сесії)!")
        except Exception as app_err:
            print(f"❌ Помилка при запиті коду: {app_err}")
            await client.disconnect()
            return

    code = input("\nВведіть отриманий код: ").strip()
    
    try:
        await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        print("====================================================")
        print("✅ Успішна авторизація! Новий сесійний ключ збережено у 'klava.session'.")
        me = await client.get_me()
        print(f"Увійшли як: {me.first_name} (@{me.username})")
        print("====================================================")
    except SessionPasswordNeededError:
        # Якщо увімкнено двофакторну аутентифікацію (2FA Cloud Password)
        password = input("\nВведіть ваш хмарний пароль (двофакторна аутентифікація): ").strip()
        try:
            await client.sign_in(password=password)
            print("====================================================")
            print("✅ Успішна авторизація з паролем 2FA!")
            me = await client.get_me()
            print(f"Увійшли як: {me.first_name} (@{me.username})")
            print("====================================================")
        except Exception as p_err:
            print(f"❌ Помилка вводу пароля: {p_err}")
    except Exception as e:
        print(f"❌ Помилка авторизації: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # Переходимо в робочу директорію бота, щоб сесія створювалась/оновлювалась там
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
