import time
import requests
import random
import re
import os
import json

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
        
    def json(self):
        return self.json_data

def translate_gemini_to_openai(json_payload):
    """Translates Gemini API payload format to OpenAI/Groq compatible chat messages list."""
    messages = []
    
    # 1. System instruction translation
    sys_inst = json_payload.get("systemInstruction")
    if sys_inst:
        parts = sys_inst.get("parts", [])
        if parts and parts[0].get("text"):
            messages.append({"role": "system", "content": parts[0]["text"]})
            
    # 2. Messages (contents) translation
    contents = json_payload.get("contents", [])
    if isinstance(contents, list):
        for item in contents:
            role = item.get("role", "user")
            if role == "model":
                role = "assistant"
            parts = item.get("parts", [])
            content_text = ""
            if isinstance(parts, list):
                content_text = "\n".join([p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")])
            elif isinstance(parts, str):
                content_text = parts
            messages.append({"role": role, "content": content_text})
    elif isinstance(contents, dict):
        parts = contents.get("parts", [])
        content_text = ""
        if isinstance(parts, list):
            content_text = "\n".join([p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")])
        messages.append({"role": "user", "content": content_text})
        
    return messages

def _attempt_groq_fallback(json_payload):
    import config
    try:
        groq_key = getattr(config, 'GROQ_API_KEY', None)
        if not groq_key:
            parent_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
            if os.path.exists(parent_config_path):
                with open(parent_config_path, "r") as f:
                    parent_cfg = json.load(f)
                    groq_key = parent_cfg.get("api_key")
                    
        if groq_key:
            groq_url = 'https://api.groq.com/openai/v1/chat/completions'
            headers_groq = {
                'Authorization': f'Bearer {groq_key}',
                'Content-Type': 'application/json'
            }
            
            messages = translate_gemini_to_openai(json_payload)
            groq_payload = {
                'model': 'llama-3.3-70b-versatile',
                'messages': messages
            }
            
            print("🔌 [Gemini Client] Attempting Groq request (Llama-3.3)...")
            groq_resp = requests.post(groq_url, json=groq_payload, headers=headers_groq, timeout=30)
            
            if groq_resp.status_code == 200:
                groq_text = groq_resp.json()['choices'][0]['message']['content'].strip()
                print("✅ [Gemini Client] Groq request successful!")
                
                gemini_compatible_json = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": groq_text
                                    }
                                ]
                            }
                        }
                    ]
                }
                return MockResponse(gemini_compatible_json, 200)
            else:
                print(f"❌ [Gemini Client] Groq request failed with code {groq_resp.status_code}: {groq_resp.text}")
        else:
            print("❌ [Gemini Client] No Groq API Key found.")
    except Exception as e:
        print(f"❌ [Gemini Client] Exception during Groq request: {e}")
    return None

def _attempt_omnirouter_request(json_payload):
    import config
    try:
        omni_key = getattr(config, 'OMNIROUTER_API_KEY', None)
        omni_url = getattr(config, 'OMNIROUTER_BASE_URL', 'http://localhost:20128/v1')
        if omni_key:
            url = f"{omni_url.rstrip('/')}/chat/completions"
            headers = {
                'Authorization': f'Bearer {omni_key}',
                'Content-Type': 'application/json'
            }
            
            messages = translate_gemini_to_openai(json_payload)
            payload = {
                'model': 'auto/chat',
                'messages': messages,
                'stream': False
            }
            
            print(f"🔌 [Gemini Client] Attempting OmniRouter request: {url}...")
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                ai_text = resp.json()['choices'][0]['message']['content'].strip()
                print("✅ [Gemini Client] OmniRouter request successful!")
                
                gemini_compatible_json = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": ai_text
                                    }
                                ]
                            }
                        }
                    ]
                }
                return MockResponse(gemini_compatible_json, 200)
            else:
                print(f"❌ [Gemini Client] OmniRouter request failed with code {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ [Gemini Client] Exception during OmniRouter request: {e}")
    return None

def gemini_post_with_retry(url, headers, json_payload, timeout=30, retries=3, initial_backoff=2, prefer_groq=False):
    """
    Performs a requests.post call to the Gemini API with exponential backoff retries.
    Rotates both API keys (from config) and model versions to prevent 503 and 429 errors.
    If prefer_groq is True, attempts Groq request first.
    If all Gemini keys fail (e.g. 429 Out of Quota), automatically falls back to Groq Llama-3.3.
    """
    import config
    
    # Спершу пробуємо OmniRouter, якщо ключ налаштований
    omni_key = getattr(config, 'OMNIROUTER_API_KEY', None)
    if omni_key:
        print("🌟 [Gemini Client] OmniRouter key configured. Trying OmniRouter first...")
        omni_res = _attempt_omnirouter_request(json_payload)
        if omni_res is not None and omni_res.status_code == 200:
            return omni_res
        print("⚠️ [Gemini Client] OmniRouter failed. Falling back to original Gemini/Groq cascade...")
        
    if prefer_groq:
        print("🌟 [Gemini Client] prefer_groq=True specified. Trying Groq first...")
        groq_res = _attempt_groq_fallback(json_payload)
        if groq_res is not None and groq_res.status_code == 200:
            return groq_res
        print("⚠️ [Gemini Client] Groq failed or was not configured. Falling back to Gemini key rotation...")
        
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
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.5-pro"]
    
    # Identify the current model in the url
    current_model = "gemini-2.5-flash"
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
            else:
                print(f"⚠️ [Gemini Client] API returned status {r.status_code} on attempt {attempt}: {r.text[:200]}")
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            print(f"⚠️ [Gemini Client] Connection error / timeout on attempt {attempt}: {e}")
            
        if attempt < total_attempts:
            sleep_time = (initial_backoff * (2 ** ((attempt - 1) // len(api_keys)))) / 2.0 + random.uniform(0.5, 1.5)
            print(f"⏳ [Gemini Client] Waiting {sleep_time:.2f} seconds before retrying...")
            time.sleep(sleep_time)
            
    # Final fallback to Groq if Gemini did not return a successful 200 response
    if last_response is None or last_response.status_code != 200:
        print("🚨 [Gemini Client] Gemini failed or returned non-200. Falling back to Groq...")
        groq_res = _attempt_groq_fallback(json_payload)
        if groq_res is not None and groq_res.status_code == 200:
            return groq_res
            
    # Final fallback attempt using original URL if last_response is still None and Groq failed
    if last_response is None:
        try:
            return requests.post(url, headers=headers, json=json_payload, timeout=timeout)
        except Exception as e:
            print(f"❌ [Gemini Client] Final fallback request failed: {e}")
            return None
            
    return last_response

