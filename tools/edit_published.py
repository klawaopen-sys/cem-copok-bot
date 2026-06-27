import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import aiohttp
import json
import config
from tools.post_glossary import GLOSSARY_HTML

async def edit_rich_message_http(bot_token: str, chat_id: str, message_id: int, html_content: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {
            "html": html_content
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

async def main():
    print("🛠️ Редагування вже надісланих повідомлень словника...")
    
    # 1. Редагуємо в каналі @cem_copok (ID: 855)
    print(f"📡 Редагування повідомлення 855 в {config.TARGET_CHANNEL}...")
    res_channel = await edit_rich_message_http(config.BOT_TOKEN, config.TARGET_CHANNEL, 855, GLOSSARY_HTML)
    print(f"Результат каналу: {json.dumps(res_channel, indent=2, ensure_ascii=False)}")
    
    # 2. Редагуємо в бібліотеці @l_ibrar_y (ID: 39)
    library_chat = "@l_ibrar_y"
    print(f"📡 Редагування повідомлення 39 в {library_chat}...")
    res_library = await edit_rich_message_http(config.LIBRARIAN_BOT_TOKEN, library_chat, 39, GLOSSARY_HTML)
    print(f"Результат бібліотеки: {json.dumps(res_library, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(main())
