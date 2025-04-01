import streamlit as st
import os
import pandas as pd
import gspread
import openai
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- 페이지 설정 ---
st.set_page_config(page_title="Object Dashboard Pro", layout="wide")
st.markdown("## 💼 Object 실시간 업무 대시보드")

# 로그인 여부 확인
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 로그인 화면
if not st.session_state["logged_in"]:
    email = st.text_input("✉️ 이메일을 입력하세요")
    password = st.text_input("🔒 비밀번호", type="password")

    if st.button("로그인"):
        # 이메일 도메인 확인 및 비밀번호 체크
        if email.endswith("@object-tex.com") and password == "your-secret-password":  # 비밀번호는 예시로 넣은 값
            st.session_state["logged_in"] = True
            st.success("🎉 로그인 성공")
        else:
            st.error("🚫 로그인 실패")

# 로그인 후 페이지 내용
if st.session_state["logged_in"]:
    # ✅ IAP 인증된 사용자 이메일 가져오기
    email = _get_websocket_headers().get("X-Goog-Authenticated-User-Email", "")
    email = email.replace("accounts.google.com:", "")  # 이메일 주소만 추출

    # ✅ 이메일 출력 (디버깅용)
    st.write(f"👤 로그인됨: `{email}`")

    # ✅ 도메인 제한
    ALLOWED_DOMAINS = ["object-tex.com", "anotherdomain.com"]  # 허용할 도메인 추가
    if not any(email.endswith(domain) for domain in ALLOWED_DOMAINS):
        st.error(f"🚫 접근 권한 없음: {', '.join(ALLOWED_DOMAINS)} 이메일만 허용됩니다.")
        st.stop()

    # ✅ GPT API 키 설정
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # ✅ 서비스 계정 인증
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    service_account_info = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "{}"))
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scope)
    gc = gspread.authorize(credentials)

    # ✅ 스프레드시트 ID
    spreadsheet_id = os.getenv("SPREADSHEET_ID")

    # ✅ 탭 설정
    sheet_map = {
        "기본문의": "25.03 기본문의(자동화)",
        "스와치": "25.03 스와치(자동화)",
        "ORDER LIST": "25.03 ORDER LIST",
        "HOLDING LIST": "25 Holding list"
    }

    tabs = st.tabs([f"📁 {label}" for label in sheet_map])

    # ✅ 상태 색상 강조 함수
    def highlight_status(val):
        if isinstance(val, str):
            if "완료" in val or "회신" in val:
                return "background-color: #d0f0c0"
            elif "보류" in val or "HOLD" in val:
                return "background-color: #ffd1d1"
            else:
                return "background-color: #fff5cc"
        return ""

    # ✅ GPT 요약
    def generate_summary(text):
        prompt = f"""Please summarize the following Korean business sentence into polite English suitable for emailing suppliers. Remove unnecessary detail:\n\n\"{text}\""""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[GPT ERROR] {e}"

    # ✅ GPT 재문의
    def generate_followup(context):
        prompt = f"""Write a follow-up email in English asking the supplier to kindly reply as soon as possible. Context: {context}"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[GPT ERROR] {e}"

    # ✅ Gmail 회신 여부 확인
    def check_recent_gmail(subject_keyword, days=7):
        try:
            delegated_user = email
            creds = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                subject=delegated_user
            )
            service = build("gmail", "v1", credentials=creds)
            query = f"subject:{subject_keyword} newer_than:{days}d"
            response = service.users().messages().list(userId='me', q=query).execute()
            messages = response.get("messages", [])
            return len(messages) > 0
        except:
            return False

    # ✅ 탭별 처리
    for i, (tab_name, sheet_name) in enumerate(sheet_map.items()):
        with tabs[i]:
            try:
                worksheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
                df = pd.DataFrame(worksheet.get_all_records())
            except Exception as e:
                st.error(f"❌ 시트 불러오기 실패: {e}")
                continue

            if "C 담당자" not in df.columns:
                st.warning("⚠️ 'C 담당자' 열이 없습니다.")
                continue

            user_id = email.split("@")[0].lower()
            df = df[df["C 담당자"].astype(str).str.lower() == user_id]

            status_col = next((col for col in df.columns if "회신" in col or "메일 발송" in col), df.columns[-1])
            total = len(df)
            replied = df[df[status_col].astype(str).str.contains("회신|완료", na=False)]
            holding = df[df[status_col].astype(str).str.contains("보류|HOLD", na=False)]
            pending = df[~df.index.isin(replied.index.union(holding.index))]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("총건수", total)
            k2.metric("회신 완료", len(replied))
            k3.metric("보류", len(holding))
            k4.metric("미회신", len(pending))

            if total > 0:
                progress = int(len(replied) / total * 100)
                st.progress(progress, f"{progress}% 회신 완료")

            search = st.text_input("🔍 키워드 검색", key=f"search_{i}")
            if search:
                df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

            st.dataframe(df.style.applymap(highlight_status, subset=[status_col]), use_container_width=True)

            st.download_button(
                "⬇️ CSV 다운로드",
                data=df.to_csv(index=False),
                file_name=f"{tab_name}_{email}.csv",
                mime="text/csv"
            )

            if "A 날짜" in df.columns:
                try:
                    df["A 날짜"] = pd.to_datetime(df["A 날짜"], errors="coerce")
                    overdue = df[df["A 날짜"] < datetime.now() - timedelta(days=3)]
                    if not overdue.empty:
                        st.markdown("#### ⏱ 3일 이상 미회신 건")
                        st.dataframe(overdue, use_container_width=True)
                except:
                    st.info("A 날짜 형식 오류")

            if "N 특이사항" in df.columns:
                st.markdown("### 🤖 특이사항 자동 요약")
                for idx, row in df.iterrows():
                    note = str(row.get("N 특이사항", "")).strip()
                    if note:
                        summary = generate_summary(note)
                        st.write(f"• `{row.get('G ITEM NO.', '')}`: {summary}")

            if "R 추가 문의" in df.columns:
                st.markdown("### ✉️ GPT 재문의 문장 생성")
                for idx, row in df.iterrows():
                    q = str(row.get("R 추가 문의", "")).strip()
                    if q:
                        prompt = f"{row.get('F BRAND NAME', '')} - {row.get('G ITEM NO.', '')}: {q}"
                        followup = generate_followup(prompt)
                        st.write(f"• `{row.get('G ITEM NO.', '')}`: {followup}")
