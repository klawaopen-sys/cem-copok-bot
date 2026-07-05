import re

def normalize_text(text):
    if not text:
        return ""
    # Remove HTML tags, emojis, non-alphanumeric characters, and extra spaces
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = " ".join(text.lower().split())
    return text

async def run_duplicates_cleanup(client):
    import config
    print("=== STARTING ON-STARTUP DUPLICATES CLEANUP ===")
    for channel_name in [config.AI_TARGET_CHANNEL, config.PSY_TARGET_CHANNEL]:
        print(f"🧹 Scanning channel: {channel_name}...")
        seen_hashes = {}
        duplicates_to_delete = []
        try:
            async for message in client.iter_messages(channel_name, limit=50):
                text = message.text or message.message or ""
                if not text.strip():
                    continue
                norm = normalize_text(text)
                # Use the first 80 characters of normalized text as unique signature
                signature = norm[:80]
                if not signature:
                    continue
                if signature in seen_hashes:
                    original_msg = seen_hashes[signature]
                    print(f"Found duplicate: ID {message.id} is duplicate of ID {original_msg.id} ({text[:50]}...)")
                    duplicates_to_delete.append(message)
                else:
                    seen_hashes[signature] = message
            if duplicates_to_delete:
                ids = [msg.id for msg in duplicates_to_delete]
                print(f"Deleting duplicate messages: {ids}")
                await client.delete_messages(channel_name, ids)
                print("Successfully deleted duplicates!")
            else:
                print("No duplicates found.")
        except Exception as e:
            print(f"Error cleaning {channel_name}: {e}")
    print("=== DUPLICATES CLEANUP COMPLETED ===")
