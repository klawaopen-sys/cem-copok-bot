import time
import requests
import random
import re

def gemini_post_with_retry(url, headers, json_payload, timeout=30, retries=4, initial_backoff=2):
    """
    Performs a requests.post call to the Gemini API with exponential backoff retries.
    Handles read timeout, connection errors, and HTTP status codes: 429 (rate limits) and 503 (service unavailable).
    Also tries fallback models if the primary model fails.
    """
    models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-latest"]
    
    # Extract API key
    key_match = re.search(r'key=([^&]+)', url)
    api_key = key_match.group(1) if key_match else ""
    
    # Identify the current model in the url
    current_model = "gemini-flash-latest"
    model_match = re.search(r'/models/([^:]+):', url)
    if model_match:
        current_model = model_match.group(1)
        
    model_queue = [current_model]
    for m in models:
        if m != current_model:
            model_queue.append(m)
            
    last_response = None
    for attempt in range(1, retries + 1):
        model_to_use = model_queue[(attempt - 1) % len(model_queue)]
        target_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={api_key}"
        
        try:
            print(f"🔌 [Gemini Client] Attempt {attempt}/{retries} using {model_to_use}...")
            r = requests.post(target_url, headers=headers, json=json_payload, timeout=timeout)
            last_response = r
            
            if r.status_code == 200:
                return r
            elif r.status_code in [429, 503, 504, 529]:
                print(f"⚠️ [Gemini Client] API returned status {r.status_code} ({r.reason}) on attempt {attempt}.")
            else:
                print(f"❌ [Gemini Client] API returned non-retryable status {r.status_code}: {r.text}")
                return r
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            print(f"⚠️ [Gemini Client] Connection error / timeout on attempt {attempt}: {e}")
            
        if attempt < retries:
            sleep_time = initial_backoff * (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
            print(f"⏳ [Gemini Client] Waiting {sleep_time:.2f} seconds before retrying...")
            time.sleep(sleep_time)
            
    # Final fallback attempt using original URL if last_response is still None
    if last_response is None:
        try:
            return requests.post(url, headers=headers, json=json_payload, timeout=timeout)
        except Exception as e:
            print(f"❌ [Gemini Client] Final fallback request failed: {e}")
            return None
            
    return last_response
