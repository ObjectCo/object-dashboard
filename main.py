# main.py (Streamlit SaaS 대시보드 – 통합 완성형)
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os

# --- 사용자 인증 ---
email = st.experimental_user.email if hasattr(st.experimental_user, "email") else None
allowed_domain = os.getenv("EMAIL_DOMAIN", "object-tex.com")

if not email or not email.endswith(f"@{allowed_domain}"):
    st.error(f"접근 권한이 없습니다. 회사 이메일(@{allowed_domain})로 로그인해주세요.")
    st.stop()

# --- Google Sheets 연결 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

spreadsheet_id = os.getenv("SPREADSHEET_ID")
sheet_map = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)",
    "ORDER LIST": "25.03 ORDER LIST",
    "HOLDING LIST": "25 Holding list"
}

# --- Streamlit 설정 ---
st.set_page_config(page_title="Object Dashboard", layout="wide")
st.markdown("## 📊 Object 실시간 업무 대시보드")
st.caption(f"접속자: `{email}`")

tabs = st.tabs([f"📁 {label}" for label in sheet_map])

for i, (label, sheet_name) in enumerate(sheet_map.items()):
    with tabs[i]:
        try:
            worksheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
            df = pd.DataFrame(worksheet.get_all_records())
        except Exception as e:
            st.error(f"❌ 시트 로딩 오류: {e}")
            continue

        st.markdown(f"### 🗂️ {label} (담당자: `{email}`)")

        if "C 담당자" not in df.columns:
            st.warning("C 담당자 열이 없습니다.")
            continue

        user_df = df[df["C 담당자"].astype(str).str.lower() == email.split("@")[0].lower()]

        status_col = next((col for col in df.columns if "회신" in col or "메일 발송" in col), df.columns[-1])
        total = len(user_df)
        replied = user_df[user_df[status_col].astype(str).str.contains("회신|완료", na=False)]
        holding = user_df[user_df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
        pending = user_df[~user_df.index.isin(replied.index.union(holding.index))]

        # KPI
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총건수", total)
        col2.metric("회신 완료", len(replied))
        col3.metric("보류", len(holding))
        col4.metric("미회신", len(pending))

        # 진행률 바
        if total > 0:
            progress = int(len(replied) / total * 100)
            st.progress(progress, text=f"{progress}% 회신 완료")

        # 검색 필터
        search = st.text_input("🔍 키워드 검색", key=f"search_{i}")
        if search:
            user_df = user_df[user_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

        # 상태 강조
        def highlight_status(val):
            if isinstance(val, str):
                if "완료" in val or "회신" in val:
                    return "background-color: #d0f0c0"
                elif "보류" in val or "HOLD" in val:
                    return "background-color: #ffd1d1"
                else:
                    return "background-color: #fff5cc"
            return ""

        styled_df = user_df.style.applymap(highlight_status, subset=[status_col])
        st.dataframe(styled_df, use_container_width=True)

        # CSV 다운로드
        st.download_button(
            label="⬇️ CSV 다운로드",
            data=user_df.to_csv(index=False),
            file_name=f"{label}_{email}.csv",
            mime="text/csv"
        )

        # 오래된 문의 강조
        if "A 날짜" in user_df.columns:
            try:
                user_df["A 날짜"] = pd.to_datetime(user_df["A 날짜"], errors='coerce')
                overdue = user_df[user_df["A 날짜"] < datetime.now() - timedelta(days=3)]
                if not overdue.empty:
                    st.markdown("#### ⏱ 3일 이상 미회신 건")
                    st.dataframe(overdue)
            except:
                st.info("A 날짜 형식 오류")
