import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
import config

async def main():
    print("Testing connection to Telegram...")
    # Use a dummy session name to test connection without touching klava.session
    client = TelegramClient('test_temp_conn', config.API_ID, config.API_HASH)
    try:
        await client.connect()
        print("✅ Connected to Telegram successfully!")
        is_authorized = await client.is_user_authorized()
        print(f"Is user authorized: {is_authorized}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await client.disconnect()
        # Clean up temp file
        if os.path.exists("test_temp_conn.session"):
            os.remove("test_temp_conn.session")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
