import os
import sys
import time
import datetime
import threading
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SHEET_ID = '1paefPw7TChWjwMv2g1ZPgbU5Qbd4f4nuHF0tzzhpEs8'
CREDENTIALS_FILE = 'klava-assistant-496912-07d33b419253.json'

class InstanceLock:
    def __init__(self):
        self.gc = None
        self.sh = None
        self.ws = None
        self.instance_id = "VPS" if sys.platform != "win32" else f"Local-{os.environ.get('COMPUTERNAME', 'PC')}"
        self.stop_event = threading.Event()
        self.heartbeat_thread = None

    def _connect(self):
        # Resolve path relative to Cem_copok directory
        bot_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        creds_path = os.path.join(bot_root, CREDENTIALS_FILE)
        
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(SHEET_ID)
        
        # Get or create BOT_LOCK worksheet
        try:
            self.ws = self.sh.worksheet('BOT_LOCK')
        except gspread.exceptions.WorksheetNotFound:
            self.ws = self.sh.add_worksheet(title='BOT_LOCK', rows=10, cols=5)
            self.ws.append_row(['instance_id', 'status', 'last_heartbeat_utc', 'info'])

    def acquire(self):
        """Checks if another instance is running. If so, exits. Otherwise, acquires lock."""
        print(f"🔒 [InstanceLock] Перевірка блокування для інстансу: {self.instance_id}...")
        try:
            self._connect()
        except Exception as e:
            print(f"⚠️ [InstanceLock] Не вдалося підключитися до Google Sheets для перевірки блокування: {e}")
            print("⚠️ Пропускаємо перевірку блокування через помилку мережі.")
            return

        try:
            rows = self.ws.get_all_records()
        except Exception as e:
            print(f"⚠️ [InstanceLock] Помилка читання BOT_LOCK: {e}. Спробуємо очистити та створити заново.")
            self.ws.clear()
            self.ws.append_row(['instance_id', 'status', 'last_heartbeat_utc', 'info'])
            rows = []

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Check if there is an active running instance
        active_instances = []
        for r in rows:
            inst = r.get('instance_id')
            status = r.get('status')
            hb_str = r.get('last_heartbeat_utc')
            
            if inst and status == 'RUNNING' and inst != self.instance_id:
                try:
                    hb_time = datetime.datetime.fromisoformat(hb_str)
                    # If heartbeat was updated less than 90 seconds ago, instance is alive
                    diff_seconds = (now_utc - hb_time).total_seconds()
                    if diff_seconds < 90:
                        active_instances.append((inst, diff_seconds))
                except Exception:
                    pass

        if active_instances:
            other_inst, sec_ago = active_instances[0]
            print("\n" + "=" * 60)
            print(f"❌ ПОМИЛКА: ЗАПУСК ЗАБЛОКОВАНО!")
            print(f"   Інший інстанс бота ({other_inst}) вже запущений!")
            print(f"   Останній сигнал активності (heartbeat) від нього був {int(sec_ago)} сек. тому.")
            print("=" * 60)
            print("👉 Будь ласка, спочатку зупиніть активний бот на сервері (PM2) або інший локальний процес.")
            print("====================================================\n")
            sys.exit(1)

        # No active instance, write our lock
        print(f"🔓 [InstanceLock] Захоплення блокування для {self.instance_id}...")
        self._update_lock('RUNNING')

        # Start heartbeat thread
        self.stop_event.clear()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def release(self):
        """Releases the lock by setting status to STOPPED."""
        print(f"🔒 [InstanceLock] Звільнення блокування для {self.instance_id}...")
        self.stop_event.set()
        try:
            self._update_lock('STOPPED')
        except Exception as e:
            print(f"⚠️ [InstanceLock] Не вдалося звільнити блокування в Google Sheets: {e}")

    def _update_lock(self, status):
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Find if our row already exists
        try:
            rows = self.ws.get_all_values()
        except Exception:
            return
            
        row_num = None
        for idx, r in enumerate(rows):
            if r and r[0] == self.instance_id:
                row_num = idx + 1
                break

        if row_num:
            self.ws.update_cell(row_num, 2, status)
            self.ws.update_cell(row_num, 3, now_str)
            self.ws.update_cell(row_num, 4, f"Updated by code at {datetime.datetime.now()}")
        else:
            self.ws.append_row([self.instance_id, status, now_str, f"Created by code at {datetime.datetime.now()}"])

    def _heartbeat_loop(self):
        while not self.stop_event.wait(30):
            try:
                self._update_lock('RUNNING')
            except Exception as e:
                print(f"⚠️ [InstanceLock] Помилка оновлення сигналу активності (heartbeat): {e}")

# Global lock instance
lock = InstanceLock()
