import streamlit as st
from auth import check_user_auth
from sheets import load_sheet_data, filter_by_user, calculate_kpi, render_table
from reminder_scheduler import run_reminder_check
from ai_summary import generate_summary
from email_utils import check_replies

st.set_page_config(page_title="Object Dashboard Pro", layout="wide")

# 🔐 사용자 로그인 체크
user_email = check_user_auth()

st.markdown(f"## 💼 Object 실시간 업무 대시보드")
st.caption(f"접속자: `{user_email}`")

# 📊 리마인더 자동 체크 실행 (비동기 가능)
run_reminder_check()

# 📄 시트 목록
sheet_map = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)",
    "ORDER LIST": "25.03 ORDER LIST",
    "HOLDING LIST": "25 Holding list"
}

tabs = st.tabs([f"📁 {name}" for name in sheet_map])

for i, (tab_name, sheet_name) in enumerate(sheet_map.items()):
    with tabs[i]:
        df = load_sheet_data(sheet_name)
        if df.empty:
            st.warning("📄 시트에 데이터가 없습니다.")
            continue

        # ✅ 담당자별 필터
        user_df = filter_by_user(df, user_email)

        # ✅ KPI
        kpi = calculate_kpi(user_df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총건수", kpi["total"])
        col2.metric("회신 완료", kpi["replied"])
        col3.metric("보류", kpi["holding"])
        col4.metric("미회신", kpi["pending"])

        # ✅ 테이블 출력
        render_table(user_df, user_email, tab_name)
