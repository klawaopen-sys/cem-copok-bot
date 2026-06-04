import os
import sys
import gspread
from google.oauth2.service_account import Credentials

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('klava-assistant-496912-07d33b419253.json', scopes=SCOPES)
    gc = gspread.authorize(creds)
    SHEET_ID = '1paefPw7TChWjwMv2g1ZPgbU5Qbd4f4nuHF0tzzhpEs8'
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet('BOT_LOCK')
    print("Lock values:")
    for row in ws.get_all_values():
        print(row)

if __name__ == "__main__":
    main()
