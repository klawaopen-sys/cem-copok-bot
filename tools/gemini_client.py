import time
import requests
import random
import re

def gemini_post_with_retry(url, headers, json_payload, timeout=30, retries=3, initial_backoff=2):
    """
    Performs a requests.post call to the Gemini API with exponential backoff retries.
    Rotates both API keys (from config) and model versions to prevent 503 and 429 errors.
    """
    import config
    
    # Collect all available API keys, starting with the original one in the URL
    original_key_match = re.search(r'key=([^&]+)', url)
    original_key = original_key_match.group(1) if original_key_match else ""
    
    api_keys = []
    if original_key:
        api_keys.append(original_key)
        
    for key_name in ['GEMINI_API_KEY', 'GEMINI_PSY_API_KEY', 'GEMINI_AI_API_KEY']:
        k_val = getattr(config, key_name, None)
        if k_val and k_val not in api_keys:
            api_keys.append(k_val)
            
    # List of valid active model names on the API
    # ВАЖЛИВО: gemini-3.5-flash та gemini-3.1-flash-lite НЕ ІСНУЮТЬ → 404 → прибрано
    # gemini-flash-latest — застарілий аліас, замінено на конкретні версії
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.5-pro"]
    
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
    total_attempts = retries * len(api_keys)
    
    for attempt in range(1, total_attempts + 1):
        key_to_use = api_keys[(attempt - 1) % len(api_keys)]
        model_to_use = model_queue[((attempt - 1) // len(api_keys)) % len(model_queue)]
        
        target_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={key_to_use}"
        
        try:
            print(f"🔌 [Gemini Client] Attempt {attempt}/{total_attempts} using model {model_to_use} with key {key_to_use[:8]}...")
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
            
        if attempt < total_attempts:
            # Scale backoff based on attempts, but divide by number of keys since changing key might avoid rate limit instantly
            sleep_time = (initial_backoff * (2 ** ((attempt - 1) // len(api_keys)))) / 2.0 + random.uniform(0.5, 1.5)
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

