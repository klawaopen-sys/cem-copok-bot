import urllib.request
import re
import os
import sys
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials

# Import config from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

def check_telegram_channel(channel_username):
    """
    Checks the last post time of a public Telegram channel by parsing its preview page.
    Returns the datetime of the last post in Kyiv timezone, or None if failed.
    """
    url = f"https://t.me/s/{channel_username.replace('@', '')}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            
        # Find all datetime attributes of time tags: <time datetime="2026-06-03T11:16:35+03:00">
        datetimes = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
        if not datetimes:
            return None
            
        # Parse the latest datetime string
        latest_dt_str = datetimes[-1]
        # Example format: 2026-06-03T11:16:35+03:00
        # Parse timezone offset manually if needed, or use simple ISO parser
        dt = datetime.fromisoformat(latest_dt_str)
        # Convert to Europe/Kyiv timezone
        kyiv_tz = pytz.timezone('Europe/Kyiv')
        return dt.astimezone(kyiv_tz)
    except Exception as e:
        print(f"⚠️ Error checking channel {channel_username}: {e}")
        return None

def check_google_sheets():
    """
    Checks if Google Sheets can be accessed and reads status.
    Returns the sheet object or None.
    """
    try:
        SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(config.GOOGLE_SHEET_ID)
        return sh
    except Exception as e:
        print(f"⚠️ Google Sheets connection failed: {e}")
        return None

def run_diagnostics():
    print("=" * 50)
    print(f"🔍 BOT SYSTEM DIAGNOSTICS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(kyiv_tz)
    has_errors = False

    # 1. Check Telegram Channels activity
    print("\n--- 1. TELEGRAM CHANNELS ACTIVITY ---")
    channels = {
        "Trading": config.TARGET_CHANNEL,
        "AI": config.AI_TARGET_CHANNEL,
        "Psychology": config.PSY_TARGET_CHANNEL
    }
    
    for label, username in channels.items():
        last_post_time = check_telegram_channel(username)
        if last_post_time:
            diff = now - last_post_time
            diff_hours = diff.total_seconds() / 3600.0
            print(f"✅ {label} ({username}): Last post at {last_post_time.strftime('%Y-%m-%d %H:%M:%S')} ({diff_hours:.1f} hours ago)")
            
            # Warn if no posts for more than 24 hours (or 16 hours for active channels)
            max_hours = 24.0 if label == "Trading" else 16.0
            if diff_hours > max_hours:
                print(f"❌ Alert: {label} has not posted for {diff_hours:.1f} hours!")
                has_errors = True
        else:
            print(f"❌ Failed to fetch latest post for {label} ({username})")
            has_errors = True

    # 2. Check Google Sheets connection
    print("\n--- 2. GOOGLE SHEETS INTEGRATION ---")
    sh = check_google_sheets()
    if sh:
        print(f"✅ Successfully connected to Google Sheet: '{sh.title}'")
        
        # 3. Check Queue Health
        print("\n--- 3. CONTENT QUEUE STATUS ---")
        try:
            ws = sh.worksheet('POSTS_QUEUE')
            rows = ws.get_all_values()
            
            pending_count = 0
            if len(rows) > 1:
                for row in rows[1:]:
                    if len(row) > 5 and row[5] == 'pending':
                        pending_count += 1
                        
            print(f"📝 Pending posts in queue: {pending_count}")
            if pending_count == 0:
                print("⚠️ Warning: Content queue is empty! No posts scheduled.")
                has_errors = True
        except Exception as e:
            print(f"❌ Failed to check queue sheet: {e}")
            has_errors = True
    else:
        print("❌ Google Sheets diagnostics FAILED.")
        has_errors = True

    # 4. Check Local Git Status
    print("\n--- 4. LOCAL REPOSITORY STATUS ---")
    # Check if there are modified untracked files
    import subprocess
    try:
        git_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=os.path.dirname(os.path.abspath(__file__))).decode('utf-8')
        if git_status.strip():
            print("⚠️ Local files have uncommitted changes:")
            print(git_status)
        else:
            print("✅ Local repository is clean and matches git head.")
    except Exception as e:
        print(f"⚠️ git command failed: {e}")

    print("\n" + "=" * 50)
    if has_errors:
        print("❌ DIAGNOSTICS STATUS: FAILURE (Action required)")
        sys.exit(1)
    else:
        print("✅ DIAGNOSTICS STATUS: ALL SYSTEMS NORMAL")
        sys.exit(0)

if __name__ == "__main__":
    run_diagnostics()
