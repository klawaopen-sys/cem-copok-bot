import os
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")

async def search_tavily_news(query: str, max_results: int = 3) -> list:
    """
    Выполняет поиск свежих новостей через Tavily API.
    Возвращает список словарей: [{'title': ..., 'url': ..., 'snippet': ...}]
    """
    if not TAVILY_API_KEY:
        logger.warning("[Tavily] TAVILY_API_KEY не установлен.")
        return []
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=12) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    items = []
                    for r in results:
                        items.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "snippet": r.get("content", r.get("snippet", ""))
                        })
                    logger.info(f"[Tavily] Успешно найдено {len(items)} результатов по запросу: '{query}'")
                    return items
                else:
                    err = await response.text()
                    logger.error(f"[Tavily] Ошибка {response.status}: {err[:200]}")
                    return []
    except Exception as e:
        logger.error(f"[Tavily] Исключение при поиске: {e}")
        return []
