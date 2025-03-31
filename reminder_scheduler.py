import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = "1Oo67NcN3opxgs1SUXRny4QJ6ZPyrE_gPYpJBwG-94ZM"

def run_reminder_check():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    gc = gspread.authorize(credentials)

    for sheet_name in ["25.03 기본문의(자동화)", "25.03 스와치(자동화)"]:
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        if "P 발송 날짜" not in df.columns or "Q 서플라이어 회신" not in df.columns:
            continue
        df["P 발송 날짜"] = pd.to_datetime(df["P 발송 날짜"], errors='coerce')
        df["Q 서플라이어 회신"] = df["Q 서플라이어 회신"].astype(str)
        now = datetime.now()
        for i, row in df.iterrows():
            if pd.notna(row["P 발송 날짜"]) and row["Q 서플라이어 회신"].strip() == "":
                delta = now - row["P 발송 날짜"]
                if delta.days >= 2:
                    print(f"[리마인더] {sheet_name} - {row.get('D INQ NO.', 'N/A')} → 2일 이상 미회신")
