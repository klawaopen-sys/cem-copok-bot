import requests
import config
from datetime import datetime
from translator import translate_to_ukrainian

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
