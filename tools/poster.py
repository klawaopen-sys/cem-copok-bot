import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from aiogram import Bot
import config
from tools.crypto_parser import (
    get_crypto_prices, get_forex_rates, get_market_data,
    get_cmc_news, get_btc_levels, get_gemini_trader_advice,
    apply_referral_links
)
from datetime import datetime
import pytz
import os
import requests
import gspread
from google.oauth2.service_account import Credentials
import google.auth.transport.requests
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

MONTHS_UA = {
    1:"січня", 2:"лютого", 3:"березня", 4:"квітня", 5:"травня", 6:"червня",
    7:"липня", 8:"серпня", 9:"вересня", 10:"жовтня", 11:"листопада", 12:"грудня"
}

def fmt(val, prefix='$', decimals=2):
    if val is None:
        return "—"
    if decimals == 0:
        return f"{prefix}{int(round(val)):,}"
    return f"{prefix}{val:,.{decimals}f}"

def build_morning_post(crypto, forex, market, news_text):
    btc_change = crypto['BTC']['change'] if crypto and 'BTC' in crypto else 0
    if btc_change > 1:
        mood = "🟢 Настрої на ринку: позитивні"
    elif btc_change < -1:
        mood = "🔴 Настрої на ринку: негативні"
    else:
        mood = "🟡 Настрої на ринку: нейтральні"

    btc_price = crypto['BTC']['price'] if crypto and 'BTC' in crypto else None
    support, resist = get_btc_levels(btc_price)

    def line(sym, label):
        if not crypto or sym not in crypto:
            return f"{label}: —"
        p = crypto[sym]['price']
        ch = crypto[sym]['change']
        em = "🟢" if ch > 0 else "🔴"
        return f"{label}: ${p:,.2f} {em} {ch:+.2f}%"

    advice = get_gemini_trader_advice(crypto, forex, market)

    post = (
        f"🌅 <b>Ранковий фінансовий огляд</b>\n\n"
        f"{mood}\n\n"
        f"📰 <b>Головні новини:</b>\n{news_text}\n\n"
        f"💰 <b>Криптовалюти:</b>\n"
        f"{line('BTC','BTC')}\n"
        f"{line('ETH','ETH')}\n"
        f"{line('SOL','SOL')}\n"
        f"{line('BNB','BNB')}\n"
        f"{line('XRP','XRP')}\n\n"
        f"💵 <b>Форекс:</b>\n"
        f"USD/UAH: ₴{forex.get('USD/UAH') or '—'}\n"
        f"EUR/UAH: ₴{forex.get('EUR/UAH') or '—'}\n"
        f"EUR/USD: ${forex.get('EUR/USD') or '—'}\n\n"
        f"📈 <b>Індекси:</b>\n"
        f"S&P 500: {fmt(market.get('SP500'), '', 2)}\n"
        f"Nasdaq 100: {fmt(market.get('NASDAQ'), '', 2)}\n"
        f"Dow Jones: {fmt(market.get('DOW'), '', 2)}\n\n"
        f"🪙 <b>Товарні активи:</b>\n"
        f"Золото: {fmt(market.get('GOLD'))}\n"
        f"Нафта Brent: {fmt(market.get('BRENT'))}\n\n"
        f"🔑 <b>Ключові рівні BTC:</b>\n"
        f"Підтримка: {support or '—'}\n"
        f"Опір: {resist or '—'}\n\n"
        f"💡 <b>Порада трейдеру:</b>\n"
        f"{advice}\n\n"
        f"#Крипта #Трейдинг #Фінанси"
    )
    return post

def get_media_info_from_sheets():
    """Reads MEDIA sheet and returns (telegram_file_id, drive_file_id)"""
    try:
        print("📁 Отримую інформацію про медіа з листа MEDIA...")
        SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
        media_ws = sh.worksheet('MEDIA')
        media_data = media_ws.get_all_values()
        
        telegram_file_id = None
        drive_file_id = None
        
        for row in media_data[1:]:
            if len(row) > 6 and row[2] == 'MORNING_REVIEW' and row[6] == 'ACTIVE':
                drive_file_id = row[3]
                telegram_file_id = row[4]
                break
        
        if not drive_file_id and not telegram_file_id and len(media_data) > 1:
            drive_file_id = media_data[1][3]
            telegram_file_id = media_data[1][4]
            
        return telegram_file_id, drive_file_id
    except Exception as e:
        print(f"⚠️ Помилка отримання даних медіа з таблиці: {e}")
        return None, None

def download_image_by_drive_id(drive_file_id):
    try:
        if drive_file_id:
            print(f"📥 Завантажую картинку з Google Drive (ID: {drive_file_id})...")
            SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            token = creds.token
            
            url = f'https://www.googleapis.com/drive/v3/files/{drive_file_id}?alt=media'
            headers = {'Authorization': f'Bearer {token}'}
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                with open('photo.jpg', 'wb') as f:
                    f.write(r.content)
                print("✅ Картинку успішно завантажено та збережено як photo.jpg!")
                return True
            else:
                print(f"⚠️ Не вдалося завантажити картинку з Drive: HTTP {r.status_code}")
    except Exception as e:
        print(f"⚠️ Помилка завантаження картинки з Google Drive: {e}")
    return False

def log_post_to_sheets(post_text, crypto, forex, market, message_id, post_link):
    try:
        print("📝 Записую опублікований пост до листа MORNING_REVIEWS...")
        SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
        ws = sh.worksheet('MORNING_REVIEWS')
        
        data = ws.get_all_values()
        next_id = 1
        if len(data) > 1:
            try:
                ids = []
                for row in data[1:]:
                    if row[0].isdigit():
                        ids.append(int(row[0]))
                if ids:
                    next_id = max(ids) + 1
            except Exception:
                next_id = len(data)
        
        now_str = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M:%S')
        
        btc_p = fmt(crypto.get('BTC', {}).get('price')) if crypto and 'BTC' in crypto else ''
        eth_p = fmt(crypto.get('ETH', {}).get('price')) if crypto and 'ETH' in crypto else ''
        sol_p = fmt(crypto.get('SOL', {}).get('price')) if crypto and 'SOL' in crypto else ''
        bnb_p = fmt(crypto.get('BNB', {}).get('price')) if crypto and 'BNB' in crypto else ''
        xrp_p = fmt(crypto.get('XRP', {}).get('price')) if crypto and 'XRP' in crypto else ''
        
        usd_uah = forex.get('USD/UAH')
        eur_usd = forex.get('EUR/USD')
        
        sp500 = market.get('SP500')
        nasdaq = market.get('NASDAQ')
        dowjones = market.get('DOW')
        gold = market.get('GOLD')
        brent = market.get('BRENT')
        
        btc_change = crypto['BTC']['change'] if crypto and 'BTC' in crypto else 0
        sentiment = "🟢" if btc_change > 1 else ("🔴" if btc_change < -1 else "🟡")
        
        row_to_append = [
            str(next_id),
            now_str, # publish_at
            'published',
            post_text,
            btc_p,
            eth_p,
            sol_p,
            bnb_p,
            xrp_p,
            f"₴{usd_uah}" if usd_uah else "",
            f"${eur_usd}" if eur_usd else "",
            "", # dxy
            fmt(sp500, '', 2) if sp500 else "",
            fmt(nasdaq, '', 2) if nasdaq else "",
            fmt(dowjones, '', 2) if dowjones else "",
            fmt(gold) if gold else "",
            fmt(brent) if brent else "",
            sentiment,
            str(message_id),
            post_link,
            now_str, # published_at
            "" # error
        ]
        
        while len(row_to_append) < 22:
            row_to_append.append("")
        row_to_append = row_to_append[:22]
        
        ws.append_row(row_to_append)
        print("✅ Запис успішно додано в Google Таблицю!")
    except Exception as e:
        print(f"⚠️ Не вдалося записати пост до Google Таблиці: {e}")

async def post_morning_report():
    bot = Bot(token=config.BOT_TOKEN)
    try:
        # 1. Get media info from Sheets
        telegram_file_id, drive_file_id = get_media_info_from_sheets()

        # 2. Fetch all required parameters
        print("📊 Отримую ціни криптовалют...")
        crypto = get_crypto_prices()
        print("💱 Отримую курси валют (НБУ)...")
        forex  = get_forex_rates()
        print("📈 Отримую дані ринків (Yahoo Finance)...")
        market = get_market_data()
        print("📰 Отримую новини (CoinMarketCap)...")
        news   = get_cmc_news()

        # 3. Build post text
        post_text = build_morning_post(crypto, forex, market, news)
        post_text = apply_referral_links(post_text)
        
        # Додаємо сигнатуру трейдингу
        signature = "\n\n📊 <b>НЕ ВСТИГАЄТЕ ЗАПИСУВАТИ ДУМКИ ПІД ЧАС ТОРГІВЛІ?</b>"
        post_text += signature

        # Якщо пост досі перевищує 1024 символи, спробуємо його трохи скоротити, щоб він помістився в один пост з фото
        if len(post_text) > 1024:
            print(f"⚠️ Довжина поста {len(post_text)} перевищує ліміт Telegram (1024). Скорочуємо...")
            parts = post_text.split("💡 <b>Порада трейдеру:</b>\n")
            if len(parts) == 2:
                sub_parts = parts[1].split("\n\n#Крипта")
                if len(sub_parts) >= 2:
                    advice_text = sub_parts[0]
                    tags_and_signature = "\n\n#Крипта" + "\n\n#Крипта".join(sub_parts[1:])
                    # Обрізаємо пораду так, щоб загальна довжина стала <= 1020
                    current_len_without_advice = len(parts[0]) + len("💡 <b>Порада трейдеру:</b>\n") + len(tags_and_signature)
                    max_advice_len = 1020 - current_len_without_advice
                    if max_advice_len > 10:
                        advice_text = advice_text[:max_advice_len - 3] + "..."
                        parts[1] = advice_text + tags_and_signature
                        post_text = "💡 <b>Порада трейдеру:</b>\n".join(parts)
            
            # Якщо все ще більше 1024, жорстко обрізаємо до 1021 символу з трьома крапками
            if len(post_text) > 1024:
                post_text = post_text[:1021] + "..."
        
        # Створюємо клавіатуру з кнопкою завантаження віджета
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="завантажити🎙️VOICE WIDGE", url="https://t.me/te_shoo_treba/194")]
        ])

        # 4. Publish to Telegram
        print("🚀 Публікую пост у канал...")
        message_id = None
        
        local_img = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.tmp', 'morning_default.png')
        if os.path.exists(local_img):
            try:
                print(f"📤 Відправляю локальну картинку: {local_img}...")
                if len(post_text) <= 1024:
                    msg = await bot.send_photo(
                        chat_id=config.TARGET_CHANNEL,
                        photo=FSInputFile(local_img),
                        caption=post_text,
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    message_id = msg.message_id
                else:
                    msg_photo = await bot.send_photo(
                        chat_id=config.TARGET_CHANNEL,
                        photo=FSInputFile(local_img)
                    )
                    msg = await bot.send_message(
                        chat_id=config.TARGET_CHANNEL,
                        text=post_text,
                        parse_mode='HTML',
                        reply_to_message_id=msg_photo.message_id,
                        reply_markup=reply_markup
                    )
                    message_id = msg.message_id
                print("✅ Успішно надіслано!")
            except Exception as e:
                print(f"⚠️ Не вдалося відправити картинку: {e}")
                
        # Hard fallback to text-only if everything else fails
        if not message_id:
            print("⚠️ Відправляю пост як звичайний текст...")
            msg = await bot.send_message(
                chat_id=config.TARGET_CHANNEL,
                text=post_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            message_id = msg.message_id
            print("✅ Надіслано як звичайний текст.")
        
        print("✅ Ранковий огляд успішно опублікований!")
        
        # Build Telegram link
        channel_username = config.TARGET_CHANNEL.replace('@', '')
        post_link = f"https://t.me/{channel_username}/{message_id}" if message_id else ""
        
        # 5. Log post back to Google Sheets
        log_post_to_sheets(post_text, crypto, forex, market, message_id or "", post_link)

    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback; traceback.print_exc()
    finally:
        await bot.session.close()

def run_poster():
    asyncio.run(post_morning_report())

if __name__ == "__main__":
    run_poster()
