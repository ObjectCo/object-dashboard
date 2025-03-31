# object_dashboard_app.py (최종 끝판왕 버전)

import streamlit as st
import pandas as pd
from datetime import datetime

# 파일 경로 및 시트명 설정
EXCEL_FILE = "/mnt/data/25 Object Order list (업무공유) (1).xlsx"
SHEETS = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)"
}

# Streamlit 설정
st.set_page_config(page_title="OBJECT 업무 대시보드", layout="wide")
st.markdown("""
    <style>
    .big-font {font-size:28px !important; font-weight:600;}
    .kpi-card {
        border-radius: 12px;
        padding: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
    }
    .status-green {color: green; font-weight: bold;}
    .status-red {color: red; font-weight: bold;}
    .status-yellow {color: orange; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# 데이터 로딩 함수
def load_sheet(sheet_name):
    return pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)

# 탭 구성
tabs = st.tabs(["📁 기본문의 대시보드", "🎨 스와치 대시보드"])

for i, (label, sheet) in enumerate(SHEETS.items()):
    with tabs[i]:
        df = load_sheet(sheet)
        df.columns = df.columns.astype(str)

        st.markdown(f"<div class='big-font'>{label} 현황</div>", unsafe_allow_html=True)

        # 담당자 필터링
        handlers = df["C 담당자"].dropna().unique().tolist()
        selected_handler = st.selectbox("담당자 선택", handlers, key=f"handler_{i}")
        filtered_df = df[df["C 담당자"] == selected_handler].copy()

        # 상태 분류 키워드 (기본문의를 기준으로 작성, 없으면 컬럼명 수정)
        if "Q 서플라이어 회신" in filtered_df.columns:
            status_col = "Q 서플라이어 회신"
        elif "O 메일 발송 여부" in filtered_df.columns:
            status_col = "O 메일 발송 여부"
        else:
            status_col = filtered_df.columns[-1]  # 마지막 열 fallback

        total = len(filtered_df)
        replied = filtered_df[filtered_df[status_col].astype(str).str.contains("회신|완료", na=False)]
        holding = filtered_df[filtered_df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
        pending = filtered_df[~filtered_df.index.isin(replied.index.union(holding.index))]

        # KPI 영역
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f"""<div class='kpi-card'>🔎 총 건수<br><span class='big-font'>{total}</span></div>""", unsafe_allow_html=True)
        col2.markdown(f"""<div class='kpi-card'>✅ 회신 완료<br><span class='status-green'>{len(replied)}</span></div>""", unsafe_allow_html=True)
        col3.markdown(f"""<div class='kpi-card'>🕒 대기 중<br><span class='status-yellow'>{len(pending)}</span></div>""", unsafe_allow_html=True)
        col4.markdown(f"""<div class='kpi-card'>📌 보류 건<br><span class='status-red'>{len(holding)}</span></div>""", unsafe_allow_html=True)

        st.markdown("---")

        # 상세 테이블 필터 및 출력
        with st.expander("📋 업무 상세 보기", expanded=True):
            search_keyword = st.text_input("🔍 키워드 검색 (브랜드명, 품번 등 포함)", "", key=f"search_{i}")
            if search_keyword:
                filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_keyword, case=False).any(), axis=1)]

            st.dataframe(filtered_df, use_container_width=True, height=500)

        # 다운로드
        with st.expander("⬇️ CSV 다운로드"):
            st.download_button(
                label="CSV 저장",
                data=filtered_df.to_csv(index=False),
                file_name=f"{label}_filtered_{selected_handler}.csv",
                mime="text/csv"
            )
