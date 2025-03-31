# object_dashboard_app.py

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

email = st.experimental_user.email if hasattr(st.experimental_user, "email") else None
if not email or not email.endswith("@object-tex.com"):
    st.error("접근 권한이 없습니다. 회사 이메일(@object-tex.com)로 로그인해주세요.")
    st.stop()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

spreadsheet_id = "1Oo67NcN3opxgs1SUXRny4QJ6ZPyrE_gPYpJBwG-94ZM"
sheet_map = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)"
}

st.set_page_config(page_title="Object Dashboard", layout="wide")
st.markdown("<h2 style='font-weight:700'>📊 Object 실시간 업무 대시보드</h2>", unsafe_allow_html=True)
tabs = st.tabs([f"📁 {label}" for label in sheet_map.keys()])

for i, (label, sheet_name) in enumerate(sheet_map.items()):
    with tabs[i]:
        worksheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())

        st.markdown(f"### 🗂️ {label} (담당자: `{email}`)")
        if "C 담당자" not in df.columns:
            st.warning("C 담당자 열이 없습니다.")
            continue

        filtered_df = df[df["C 담당자"].astype(str).str.lower() == email.split('@')[0].lower()]
        status_col = [col for col in df.columns if "회신" in col or "메일 발송" in col]
        status_col = status_col[0] if status_col else df.columns[-1]

        total = len(filtered_df)
        replied = filtered_df[filtered_df[status_col].astype(str).str.contains("회신|완료", na=False)]
        holding = filtered_df[filtered_df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
        pending = filtered_df[~filtered_df.index.isin(replied.index.union(holding.index))]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 건수", total)
        col2.metric("회신 완료", len(replied))
        col3.metric("대기 중", len(pending))
        col4.metric("보류", len(holding))

        st.markdown("### 📋 업무 리스트")
        search = st.text_input("🔍 키워드 검색", key=f"search_{i}")
        if search:
            filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        st.dataframe(filtered_df, use_container_width=True)
        st.download_button("⬇️ CSV 다운로드", data=filtered_df.to_csv(index=False), file_name=f"{label}_{email}.csv", mime="text/csv")

