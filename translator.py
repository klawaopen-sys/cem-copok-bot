from googletrans import Translator

def translate_to_ukrainian(text):
    if not text:
        return ""
    translator = Translator()
    try:
        result = translator.translate(text, dest='uk')
        return result.text
    except Exception as e:
        print(f"Ошибка перевода: {e}")
        return text
