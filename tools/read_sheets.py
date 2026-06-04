import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('klava-assistant-496912-07d33b419253.json', scopes=SCOPES)
gc = gspread.authorize(creds)

SHEET_ID = '1paefPw7TChWjwMv2g1ZPgbU5Qbd4f4nuHF0tzzhpEs8'
sh = gc.open_by_key(SHEET_ID)

for ws in sh.worksheets():
    print(f"\n{'='*50}")
    print(f"ЛИС: {ws.title} (строк: {ws.row_count}, колонок: {ws.col_count})")
    print(f"{'='*50}")
    data = ws.get_all_values()
    for i, row in enumerate(data[:30]):
        if any(cell.strip() for cell in row):
            print(f"  [{i+1}] {row}")
