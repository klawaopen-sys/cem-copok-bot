import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tools.gemini_client import gemini_post_with_retry
from main import get_gemini_streaming_reply

async def test_all():
    print("🤖 Starting OmniRouter test...")
    print(f"Base URL: {config.OMNIROUTER_BASE_URL}")
    print(f"API Key: {config.OMNIROUTER_API_KEY[:15]}...")
    
    # 1. Test normal post completions
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=dummy"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": "Say 'OmniRouter Text OK'"}]}]
    }
    
    print("\n--- Test 1: Normal completions ---")
    
    # Спробуємо зробити запит до OmniRouter вручну з дебаг-виводом
    import requests
    omni_url = f"{config.OMNIROUTER_BASE_URL.rstrip('/')}/chat/completions"
    omni_headers = {
        "Authorization": f"Bearer {config.OMNIROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    from tools.gemini_client import translate_gemini_to_openai
    omni_payload = {
        "model": "auto/chat",
        "messages": translate_gemini_to_openai(payload),
        "stream": False
    }
    
    print(f"Sending POST to {omni_url} with stream=False...")
    print(f"Headers: {omni_headers}")
    print(f"Payload: {omni_payload}")
    
    try:
        r = requests.post(omni_url, json=omni_payload, headers=omni_headers, timeout=15)
        print(f"Response status: {r.status_code}")
        print(f"Response headers: {dict(r.headers)}")
        print(f"Response text: {r.text}")
    except Exception as ex:
        print(f"Request failed with exception: {ex}")

    resp = gemini_post_with_retry(url, headers, payload)
    if resp and resp.status_code == 200:
        print("Response raw:")
        print(resp.text)
        print("Parsed text:", resp.json()['candidates'][0]['content']['parts'][0]['text'])
        print("✅ Test 1 Passed!")
    else:
        print("❌ Test 1 Failed!")
        if resp:
            print(f"Status: {resp.status_code}, Text: {resp.text}")
            
    # 2. Test streaming completions
    print("\n--- Test 2: Streaming completions ---")
    history = [{"role": "user", "parts": [{"text": "Say 'OmniRouter Stream OK'"}]}]
    
    import main
    original_draft = main.send_rich_message_draft_http
    original_final = main.send_rich_message_http
    
    async def mock_draft(token, chat_id, draft_id, html):
        print(f"[Mock Draft] {html}")
    async def mock_final(token, chat_id, html, reply_markup=None):
        print(f"[Mock Final] {html}")
        
    main.send_rich_message_draft_http = mock_draft
    main.send_rich_message_http = mock_final
    
    try:
        reply = await get_gemini_streaming_reply(
            api_key="dummy",
            history=history,
            system_prompt="You are a helpful assistant.",
            chat_id=123456,
            bot_token="dummy_token"
        )
        print("Stream Reply:", reply)
        if reply and "OK" in reply:
            print("✅ Test 2 Passed!")
        else:
            print("❌ Test 2 Failed!")
    finally:
        main.send_rich_message_draft_http = original_draft
        main.send_rich_message_http = original_final

if __name__ == "__main__":
    asyncio.run(test_all())
