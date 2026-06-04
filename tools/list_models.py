import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import config

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={config.GEMINI_API_KEY}"
r = requests.get(url)
if r.status_code == 200:
    for m in r.json().get('models', []):
        print(f"Model: {m['name']} (supported methods: {m['supportedGenerationMethods']})")
else:
    print(f"Error {r.status_code}: {r.text}")
