import os
import json
import re
import urllib.request
import html
from datetime import datetime

def normalize_text(text: str) -> str:
    """Нормалізує текст для надійного порівняння дублікатів"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)  # Видаляємо HTML
    clean = re.sub(r'[^\w\s]', '', clean) # Видаляємо пунктуацію
    clean = re.sub(r'\s+', '', clean)    # Видаляємо пробіли
    return clean.lower()

def clean_and_sanitize_final_post(text: str) -> str:
    """
    Повністю очищає текст від будь-яких мета-вступів, привітань редактора та маркдаун-зірочок:
    - Видаляє: "Доброго дня...", "Я главный редактор...", "Новый пост:", "RESPONSE_STATUS:...", "POST_TEXT:"
    - Замінює **жирний** на <b>жирний</b> та видаляє залишкові зірочки
    """
    if not text:
        return ""

    # 1. Видаляємо системні мітки
    text = re.sub(r'(?i)RESPONSE_STATUS:\s*\w+', '', text)
    text = re.sub(r'(?i)POST_TEXT:\s*', '', text)
    text = re.sub(r'(?i)IMAGE_PROMPT:.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i)INDEX:\s*\d+', '', text)

    # 2. Видаляємо мета-вступи від редактора та фрази типу "Новый пост:" / "Новий пост:"
    meta_patterns = [
        r'(?i)^[^\n]*я\s+(головний|главный)\s+редактор[^\n]*\n?',
        r'(?i)^[^\n]*(доброго?\s+дня|добрый\s+день|доброго\s+ранку|доброе\s+утро|доброго\s+вечора|добрый\s+вечер)[^\n]*\n?',
        r'(?i)^[^\n]*я\s+(переглянув|просмотрел)[^\n]*\n?',
        r'(?i)^[^\n]*(проаналізувавши|проанализировав)[^\n]*\n?',
        r'(?i)^[^\n]*(новий|новый)\s+пост:?\s*\n?',
        r'(?i)^[^\n]*ось\s+(новий|новый)\s+пост:?\s*\n?',
    ]
    for pat in meta_patterns:
        text = re.sub(pat, '', text).strip()

    # 3. Конвертуємо Markdown **жирний** у HTML <b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)

    # 4. Видаляємо поодинокі залишкові зірочки
    text = text.replace('**', '').replace('*', '')

    # 5. Очищаємо пробіли
    text = text.strip()
    return text

def fetch_channel_history_web(channel_username: str, limit: int = 30) -> list:
    """Зчитує чистий текст останніх постів з публічної веб-версії t.me/s/"""
    if not channel_username:
        return []
    username = str(channel_username).lstrip('@')
    url = f"https://t.me/s/{username}"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8')
            
        posts = []
        pattern = re.compile(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', re.DOTALL)
        matches = pattern.findall(html_content)
        
        for match in matches[-limit:]:
            clean_text = re.sub(r'<[^>]+>', '', match).strip()
            clean_text = html.unescape(clean_text)
            if clean_text:
                posts.append(clean_text)
        return posts
    except Exception as e:
        print(f"⚠️ [dedup_engine] Помилка веб-скрейпера t.me/s/{username}: {e}")
        return []

def get_history_file_path(tmp_dir: str) -> str:
    os.makedirs(tmp_dir, exist_ok=True)
    return os.path.join(tmp_dir, "published_history.json")

def load_local_history(tmp_dir: str) -> list:
    """Завантажує локальну історію постів з JSON-файлу"""
    filepath = get_history_file_path(tmp_dir)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("posts", [])
    except Exception as e:
        print(f"⚠️ [dedup_engine] Помилка зчитування локальної історії: {e}")
    return []

def save_to_local_history(tmp_dir: str, post_text: str, title: str = "", link: str = ""):
    """Зберігає опублікований пост у локальний JSON-кєш"""
    filepath = get_history_file_path(tmp_dir)
    history = load_local_history(tmp_dir)
    
    entry = {
        "title": title,
        "link": link,
        "text": post_text[:500],
        "norm": normalize_text(post_text[:300]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    norm_entry = entry["norm"]
    if norm_entry and not any(normalize_text(h.get("text", "")) == norm_entry for h in history):
        history.append(entry)
        if len(history) > 300:
            history = history[-300:]
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"posts": history}, f, ensure_ascii=False, indent=2)
            print(f"💾 [dedup_engine] Пост збережено в локальний кєш ({filepath})")
        except Exception as e:
            print(f"⚠️ [dedup_engine] Помилка запису в локальну історію: {e}")

async def get_combined_history(client, channel_name: str, tmp_dir: str, limit: int = 80) -> list:
    """
    Формує об'єднану історію постів з 3 джерел:
    1. Telethon (якщо активний)
    2. Web-скрейпер t.me/s/
    3. Локальний JSON-кєш `.tmp/published_history.json`
    """
    combined_texts = []
    seen_norms = set()

    def add_item(t):
        if not t:
            return
        norm = normalize_text(t)
        if norm and norm not in seen_norms:
            seen_norms.add(norm)
            combined_texts.append(t.strip())

    # 1. Telethon
    if client:
        try:
            if not client.is_connected():
                await client.connect()
            async for message in client.iter_messages(channel_name, limit=limit):
                txt = message.text or message.message
                if txt:
                    add_item(txt)
            print(f"✅ [dedup_engine] Telethon зчитав {len(combined_texts)} постів.")
        except Exception as e:
            print(f"⚠️ [dedup_engine] Telethon error: {e}")

    # 2. Веб-скрейпер fallback
    web_posts = fetch_channel_history_web(channel_name, limit=40)
    for wp in web_posts:
        add_item(wp)

    # 3. Локальний JSON-кєш
    local_posts = load_local_history(tmp_dir)
    for lp in local_posts:
        if isinstance(lp, dict):
            add_item(lp.get("text", ""))
            if lp.get("title"):
                add_item(lp.get("title"))
        elif isinstance(lp, str):
            add_item(lp)

    print(f"📊 [dedup_engine] Разом сформовано {len(combined_texts)} унікальних записів історії.")
    return combined_texts[:limit]

def is_news_duplicate(news_item: dict, history_texts: list) -> bool:
    """Перевіряє, чи є конкретна новина з RSS дублікатом згідно історії"""
    title = news_item.get("title", "")
    link = news_item.get("link", "")
    title_norm = normalize_text(title)
    link_norm = normalize_text(link)
    
    if not title_norm:
        return False
        
    for h_text in history_texts:
        h_norm = normalize_text(h_text)
        if not h_norm:
            continue
        if title_norm in h_norm or (len(title_norm) > 15 and title_norm[:30] in h_norm):
            return True
        if link_norm and len(link_norm) > 10 and link_norm in h_norm:
            return True
            
    return False

def filter_unique_news_pool(news_list: list, history_texts: list) -> list:
    """Фільтрує пул новин з RSS, видаляючи дублікати ДО запиту в Gemini"""
    unique_news = []
    dropped_count = 0
    for item in news_list:
        if is_news_duplicate(item, history_texts):
            dropped_count += 1
            print(f"🚫 [dedup_engine] Відхилено дублікат RSS: \"{item.get('title', '')[:50]}...\"")
        else:
            unique_news.append(item)
            
    if dropped_count > 0:
        print(f"🧹 [dedup_engine] Відфільтровано {dropped_count} дублікатів з RSS-пулу.")
    return unique_news
