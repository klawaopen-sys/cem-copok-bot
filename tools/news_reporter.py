import xml.etree.ElementTree as ET
import requests
import re

def fetch_rss_news(rss_urls):
    news_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for url in rss_urls:
        try:
            print(f"📡 Зчитую RSS-стрічку: {url}...")
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                print(f"⚠️ Помилка зчитування RSS з {url}: HTTP {r.status_code}")
                continue
                
            xml_content = r.content
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError:
                decoded = xml_content.decode('utf-8', errors='ignore')
                decoded = re.sub(r'^[^<]*', '', decoded)
                root = ET.fromstring(decoded.encode('utf-8'))
                
            items = root.findall('.//item')
            print(f"✅ Знайдено {len(items)} новин у стрічці {url}")
            for item in items[:15]:
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')
                
                title = title_el.text if title_el is not None else ""
                link = link_el.text if link_el is not None else ""
                desc = desc_el.text if desc_el is not None else ""
                
                # Шукаємо картинку в enclosure
                image_url = ""
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    image_url = enclosure.get('url', '')
                
                # Шукаємо в media:content або за допомогою regex в description
                if not image_url:
                    # Пошук за локальним ім'ям без урахування простору імен
                    for child in item:
                        if child.tag.endswith('content') and child.get('url'):
                            image_url = child.get('url')
                            break
                            
                if not image_url and desc:
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
                    if img_match:
                        image_url = img_match.group(1)
                
                if desc:
                    desc = re.sub(r'<[^>]+>', '', desc)
                    
                if title:
                    news_items.append({
                        "title": title.strip(),
                        "link": link.strip(),
                        "description": desc.strip(),
                        "source": url,
                        "image_url": image_url.strip() if image_url else ""
                    })
        except Exception as e:
            print(f"⚠️ Помилка обробки RSS з {url}: {e}")
            
    return news_items
