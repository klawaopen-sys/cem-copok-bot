import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import config
from datetime import datetime
from tools.translator import translate_to_ukrainian

def get_crypto_prices():
    """Получает цены с CoinMarketCap через бесплатное API"""
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    symbols = 'BTC,ETH,SOL,BNB,XRP'
    headers = {'X-CMC_PRO_API_KEY': config.CMC_API_KEY, 'Accepts': 'application/json'}
    params = {'symbol': symbols, 'convert': 'USD'}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()['data']
        prices = {}
        for sym in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']:
            price = data[sym]['quote']['USD']['price']
            change = data[sym]['quote']['USD']['percent_change_24h']
            prices[sym] = {'price': price, 'change': change}
        return prices
    except Exception as e:
        print(f"Помилка CoinMarketCap: {e}")
        return None

def get_cmc_news():
    """Берет свежие новости с CoinMarketCap"""
    url = 'https://pro-api.coinmarketcap.com/v1/content/latest'
    headers = {'X-CMC_PRO_API_KEY': config.CMC_API_KEY, 'Accepts': 'application/json'}
    params = {'limit': 5}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        if 'data' in data and len(data['data']) > 0:
            # Берем первые 3 заголовка новостей
            news_items = []
            for item in data['data'][:3]:
                title = item.get('title', '')
                if title:
                    translated_title = translate_to_ukrainian(title)
                    news_items.append(f"- {translated_title}")
            return "\n".join(news_items)
    except Exception as e:
        print(f"Помилка новин CMC: {e}")
    return "- Ринок відкрився стабільно\n- Інвестори відстежують макроекономічні показники"

def get_forex_rates():
    """Получает курсы валют через бесплатный API НБУ и exchangerate-api"""
    rates = {}
    # Курс НБУ (USD/UAH и EUR/UAH) - полностью бесплатно
    try:
        r = requests.get('https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json', timeout=10)
        nbu = r.json()
        for item in nbu:
            if item['cc'] == 'USD':
                rates['USD/UAH'] = round(item['rate'], 2)
            if item['cc'] == 'EUR':
                rates['EUR/UAH'] = round(item['rate'], 2)
    except Exception as e:
        print(f"Помилка НБУ: {e}")
        rates['USD/UAH'] = None
        rates['EUR/UAH'] = None

    # EUR/USD через бесплатный exchangerate
    try:
        r = requests.get('https://open.er-api.com/v6/latest/EUR', timeout=10)
        data = r.json()
        rates['EUR/USD'] = round(data['rates']['USD'], 4)
    except Exception as e:
        print(f"Помилка EUR/USD: {e}")
        rates['EUR/USD'] = None

    return rates

def get_market_data():
    """Получает данные по индексам и commodities через Yahoo Finance (бесплатно)"""
    tickers = {
        'SP500':   '^GSPC',
        'NASDAQ':  '^NDX',
        'DOW':     '^DJI',
        'GOLD':    'GC=F',
        'BRENT':   'BZ=F',
    }
    results = {}
    for name, ticker in tickers.items():
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            results[name] = round(price, 2)
        except Exception as e:
            print(f"Помилка Yahoo Finance {name}: {e}")
            results[name] = None
    return results

def get_btc_levels(btc_price):
    """Розраховуємо рівні підтримки/опору BTC відносно поточної ціни"""
    if not btc_price:
        return None, None
    support1 = round(btc_price * 0.985, -2)
    support2 = round(btc_price * 0.975, -2)
    resist = round(btc_price * 1.015, -2)
    return f"{int(support1):,} / {int(support2):,}", f"{int(resist):,}"

def get_gemini_trader_advice(crypto, forex, market):
    """Генерує розумну пораду трейдеру за допомогою Google Gemini API"""
    if not config.GEMINI_API_KEY:
        return "Контролюйте ризики, ринок волатильний."
        
    try:
        btc_price = crypto.get('BTC', {}).get('price') if crypto and 'BTC' in crypto else None
        btc_change = crypto.get('BTC', {}).get('change') if crypto and 'BTC' in crypto else 0
        usd_uah = forex.get('USD/UAH') if forex else None
        sp500 = market.get('SP500') if market else None
        gold = market.get('GOLD') if market else None
        brent = market.get('BRENT') if market else None
        
        prompt = (
            "Ти — професійний фінансовий аналітик та досвідчений крипто-трейдер. "
            "На основі наступних ринкових даних напиши коротку, корисну та реалістичную пораду для трейдерів на сьогодні (1-2 речення українською мовою). "
            "Порада має бути конкретною, практичною, без банальностей типу 'ринок волатильний' чи 'контролюйте ризики'. "
            "Вона повинна спиратися на поточні рухи цін:\n"
            f"- Ціна BTC: {f'${btc_price:,.2f}' if btc_price else '—'} (зміна за 24г: {btc_change:+.2f}%)\n"
            f"- Курс USD/UAH (НБУ): {f'₴{usd_uah}' if usd_uah else '—'}\n"
            f"- Індекс S&P 500: {sp500 if sp500 else '—'}\n"
            f"- Золото: {f'${gold}' if gold else '—'}\n"
            f"- Нафта Brent: {f'${brent}' if brent else '—'}\n\n"
            "Напиши тільки сам текст поради, без будь-яких вступних слів, лапок чи привітань. Порада має починатися одразу з суті."
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={config.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        from tools.gemini_client import gemini_post_with_retry
        r = gemini_post_with_retry(url, headers, payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            advice = data['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean up potential leading/trailing quotes
            if advice.startswith('"') and advice.endswith('"'):
                advice = advice[1:-1]
            if advice.startswith('«') and advice.endswith('»'):
                advice = advice[1:-1]
            return advice
        else:
            print(f"Помилка Gemini API: HTTP {r.status_code}, {r.text}")
    except Exception as e:
        print(f"Помилка генерації поради Gemini: {e}")
        
    return "Контролюйте ризики, ринок волатильний."

def apply_referral_links(text):
    """Шукає згадки Bybit, Binance, TradingView тощо та перетворює їх на реферальні посилання"""
    import re
    if not hasattr(config, 'REFERRAL_LINKS'):
        return text
        
    for name, url in config.REFERRAL_LINKS.items():
        if url and url.strip():
            # Шукаємо збіг цілого слова з ігноруванням регістру
            pattern = re.compile(rf'\b{re.escape(name)}\b', re.IGNORECASE)
            
            def replace_func(match):
                start = match.start()
                # Перевіряємо, чи це не частина URL-адреси (щоб не зламати посилання)
                preceding_text = text[max(0, start-20):start]
                if "http" in preceding_text or "www" in preceding_text or "/" in preceding_text:
                    return match.group(0)
                
                matched_word = match.group(0)
                return f'<a href="{url}"><b>{matched_word}</b></a>'
                
            text = pattern.sub(replace_func, text)
    return text
