import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime, timedelta

# 서비스 계정 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = "1Oo67NcN3opxgs1SUXRny4QJ6ZPyrE_gPYpJBwG-94ZM"

def load_sheet_data(sheet_name):
    try:
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ 시트 불러오기 오류: {e}")
        return pd.DataFrame()

def filter_by_user(df, email):
    if "C 담당자" not in df.columns:
        return df  # 전체 보기 허용
    user_id = email.split("@")[0].lower()
    return df[df["C 담당자"].astype(str).str.lower() == user_id]

def calculate_kpi(df):
    status_col = next((c for c in df.columns if "회신" in c or "메일 발송" in c), df.columns[-1])
    replied = df[df[status_col].astype(str).str.contains("회신|완료", na=False)]
    holding = df[df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
    pending = df[~df.index.isin(replied.index.union(holding.index))]
    return {
        "total": len(df),
        "replied": len(replied),
        "holding": len(holding),
        "pending": len(pending)
    }

def render_table(df, email, tab_name):
    status_col = next((c for c in df.columns if "회신" in c or "메일 발송" in c), df.columns[-1])
    df[status_col] = df[status_col].astype(str)

    def highlight_status(val):
        if "완료" in val or "회신" in val:
            return "background-color: #d0f0c0"
        elif "보류" in val or "HOLD" in val:
            return "background-color: #ffd1d1"
        else:
            return "background-color: #fff5cc"

    df["A 날짜"] = pd.to_datetime(df.get("A 날짜", pd.NaT), errors='coerce')
    overdue = df[df["A 날짜"] < datetime.now() - timedelta(days=3)]

    search = st.text_input("🔍 검색", key=f"{tab_name}_search")
    if search:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    st.dataframe(df.style.applymap(highlight_status, subset=[status_col]), use_container_width=True)

    st.download_button("⬇️ CSV 다운로드", df.to_csv(index=False), file_name=f"{tab_name}_{email}.csv")

    if not overdue.empty:
        st.markdown("#### ⏱ 오래된 미회신 건")
        st.dataframe(overdue)
