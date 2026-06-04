import asyncio
import sys
import os

# Add Cem_copok to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from telethon import TelegramClient, functions

client = TelegramClient('klava', config.API_ID, config.API_HASH)

async def main():
    await client.start()
    chat = await client.get_input_entity('@te_shoo_treba')
    full_chat = await client(functions.channels.GetFullChannelRequest(chat))
    print(f"PINNED_MSG_ID: {full_chat.full_chat.pinned_msg_id}")

if __name__ == "__main__":
    asyncio.run(main())
