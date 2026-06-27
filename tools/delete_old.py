import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import aiohttp
import config

async def delete_message_http(bot_token: str, chat_id: str, message_id: int) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

async def main():
    print("🧹 Видалення застарілих (текстових) повідомлень словника...")
    
    # 1. Видаляємо з каналу @cem_copok (ID: 857)
    print(f"📡 Видалення повідомлення 857 з {config.TARGET_CHANNEL}...")
    res_channel = await delete_message_http(config.BOT_TOKEN, config.TARGET_CHANNEL, 857)
    print(f"Результат каналу: {res_channel}")
    
    # 2. Видаляємо з бібліотеки @l_ibrar_y (ID: 41)
    library_chat = "@l_ibrar_y"
    print(f"📡 Видалення повідомлення 41 з {library_chat}...")
    res_library = await delete_message_http(config.LIBRARIAN_BOT_TOKEN, library_chat, 41)
    print(f"Результат бібліотеки: {res_library}")

if __name__ == "__main__":
    asyncio.run(main())
