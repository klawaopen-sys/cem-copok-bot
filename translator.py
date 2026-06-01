import requests
import urllib.parse

def translate_to_ukrainian(text):
    if not text:
        return ""
    try:
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=uk&dt=t&q={encoded_text}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            res = r.json()
            # Extract and join parts in case of multi-sentence text
            translated = "".join([part[0] for part in res[0] if part[0]])
            return translated
    except Exception as e:
        print(f"Ошибка перевода: {e}")
    return text
