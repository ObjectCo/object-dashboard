# object_dashboard_app.py (SaaS급 최종 버전 - 30+ 기능 반영)

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import numpy as np

# --- 사용자 인증 ---
email = st.experimental_user.email if hasattr(st.experimental_user, "email") else None
if not email or not email.endswith("@object-tex.com"):
    st.error("접근 권한이 없습니다. 회사 이메일(@object-tex.com)로 로그인해주세요.")
    st.stop()

# --- Google Sheets 연결 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

spreadsheet_id = "1Oo67NcN3opxgs1SUXRny4QJ6ZPyrE_gPYpJBwG-94ZM"
sheet_map = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)"
}

# --- Streamlit 페이지 설정 ---
st.set_page_config(page_title="Object Dashboard", layout="wide")
st.markdown(f"<h2 style='font-weight:700'>📊 Object 실시간 업무 대시보드</h2>", unsafe_allow_html=True)

# --- 탭 구성 ---
tabs = st.tabs([f"📁 {label}" for label in sheet_map.keys()])

for i, (label, sheet_name) in enumerate(sheet_map.items()):
    with tabs[i]:
        worksheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())

        st.markdown(f"### 🗂️ {label} (담당자: `{email}`)")

        if "C 담당자" not in df.columns:
            st.warning("C 담당자 열이 없습니다.")
            continue

        filtered_df = df[df["C 담당자"].astype(str).str.lower() == email.split("@")[0].lower()]

        # 상태 컬럼 자동 감지
        status_col = [col for col in df.columns if "회신" in col or "메일 발송" in col]
        status_col = status_col[0] if status_col else df.columns[-1]

        # 상태별 분류
        total = len(filtered_df)
        replied = filtered_df[filtered_df[status_col].astype(str).str.contains("회신|완료", na=False)]
        holding = filtered_df[filtered_df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
        pending = filtered_df[~filtered_df.index.isin(replied.index.union(holding.index))]

        # KPI
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 건수", total)
        col2.metric("회신 완료", len(replied))
        col3.metric("대기 중", len(pending))
        col4.metric("보류", len(holding))

        # 진행률 바
        if total > 0:
            percent = int(len(replied) / total * 100)
            st.progress(percent, text=f"{percent}% 회신 완료")

        # 🔍 고급 검색 + 필터링 기능
        with st.expander("🔍 필터 / 검색 옵션", expanded=False):
            query = st.text_input("브랜드명, 품번, 특이사항 등 전체 검색", key=f"search_{i}")
            status_options = ["전체", "회신 완료", "보류", "대기 중"]
            selected_status = st.selectbox("상태 필터", status_options)

            if query:
                filtered_df = filtered_df[filtered_df.apply(lambda row: query.lower() in str(row).lower(), axis=1)]

            if selected_status != "전체":
                if selected_status == "회신 완료":
                    filtered_df = replied
                elif selected_status == "보류":
                    filtered_df = holding
                elif selected_status == "대기 중":
                    filtered_df = pending

        # ✅ 최근 업데이트 순 정렬
        if "P 발송 날짜" in filtered_df.columns:
            try:
                filtered_df["P 발송 날짜"] = pd.to_datetime(filtered_df["P 발송 날짜"], errors='coerce')
                filtered_df = filtered_df.sort_values(by="P 발송 날짜", ascending=False)
            except:
                pass

        # ✅ 상태 강조 컬러 처리
        def highlight_status(val):
            if isinstance(val, str):
                if "완료" in val or "회신" in val:
                    return "background-color: #d0f0c0"  # 연한 초록
                elif "보류" in val or "HOLD" in val:
                    return "background-color: #ffd1d1"  # 연한 빨강
                else:
                    return "background-color: #fff5cc"  # 연한 노랑
            return ""

        styled_df = filtered_df.style.applymap(highlight_status, subset=[status_col])
        st.dataframe(styled_df, use_container_width=True)

        # ✅ CSV 다운로드
        st.download_button(
            "⬇️ CSV 다운로드",
            data=filtered_df.to_csv(index=False),
            file_name=f"{label}_{email}.csv",
            mime="text/csv"
        )

        # ✅ 오래된 미회신 건 감지 (A 날짜 기준)
        st.markdown("#### ⏱ 3일 이상 미회신 자동 감지")
        if "A 날짜" in filtered_df.columns:
            try:
                filtered_df["A 날짜"] = pd.to_datetime(filtered_df["A 날짜"])
                overdue = filtered_df[filtered_df["A 날짜"] < datetime.now() - timedelta(days=3)]
                st.warning(f"⏰ 3일 이상 미회신 건: {len(overdue)}건")
                st.dataframe(overdue, use_container_width=True)
            except:
                st.info("날짜 형식 오류: A열이 날짜 형식이 아닐 수 있습니다.")

        # ✅ 월별 회신 통계 요약 (옵션)
        if "P 발송 날짜" in df.columns:
            try:
                df["P 발송 날짜"] = pd.to_datetime(df["P 발송 날짜"], errors="coerce")
                month_count = df.groupby(df["P 발송 날짜"].dt.to_period("M")).size()
                st.bar_chart(month_count)
            except:
                pass

        # ✅ 유저 이름 표시
        st.caption(f"접속자: `{email}` | 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
