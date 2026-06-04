import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from pyrogram import Client
import config

async def main():
    print("====================================================")
    print("🔑 Запуск авторизації юзербота 'Клава'...")
    print("Вам потрібно буде ввести ваш номер телефону та код з Telegram.")
    print("====================================================")
    
    # Инициализируем клиент pyrogram
    app = Client("klava", api_id=config.API_ID, api_hash=config.API_HASH, workdir=".")
    
    await app.start()
    
    print("====================================================")
    print("✅ Авторизація успішна! Файл 'klava.session' створено.")
    print("Тепер ви можете закрити це вікно.")
    print("====================================================")
    
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
