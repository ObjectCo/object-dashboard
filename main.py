import streamlit as st
import pandas as pd
import gspread
import openai
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from authlib.integrations.requests_client import OAuth2Session
from streamlit.web.server.websocket_headers import _get_websocket_headers

# --- 기본 설정 ---
st.set_page_config(page_title="Object Dashboard Pro", layout="wide")
st.markdown("## 💼 Object 실시간 업무 대시보드")

# 환경변수에서 클라이언트 정보 불러오기
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")  # 예: "https://object-dashboard-xyz12345-uc.a.run.app"
token_url = os.getenv("TOKEN_URL", "https://oauth2.googleapis.com/token")
st.write("✅ token_url:", token_url)  # ← 이 줄 추가
st.write("🔍 client_id:", client_id)
st.write("🔍 client_secret:", client_secret)
st.write("🔍 redirect_uri:", redirect_uri)


# ⛔ 방어 코드 추가: token_url 없을 때 멈춤
if not token_url or not token_url.startswith("http"):
    st.error("❌ token_url이 비어있거나 잘못됨. 환경변수 'TOKEN_URL' 확인 필요.")
    st.stop()

# 로그인 URL 구성
authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"

# 인증 세션 생성
oauth = OAuth2Session(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="openid email profile"
)

# 로그인 요청
if "code" not in st.query_params:
    auth_url, state = oauth.create_authorization_url(authorize_url)
    st.markdown(f"[🔐 Google 계정으로 로그인]({auth_url})", unsafe_allow_html=True)
    st.stop()

# ✅ 콜백 처리 (Cloud Run 호환)
code = st.query_params.get("code", [None])[0]
st.write("🔐 code:", code)

if not code:
    st.error("❌ OAuth 인증 코드가 없습니다. 다시 로그인해 주세요.")
    st.stop()

# ✅ current_url 대신 redirect_uri + code 조합
authorization_response = f"{redirect_uri}?code={code}"
st.write("🔁 authorization_response:", authorization_response)

st.write("🔥 DEBUG - client_secret before fetch_token:", client_secret)
# 🔐 토큰 요청
token = oauth.fetch_token(
    token_url=token_url,
    code=code,
    authorization_response=authorization_response,
    client_secret=client_secret  # ✅ 직접 명시
)


# ✅ 인증 완료 후 쿼리파라미터 정리
st.experimental_set_query_params()

# 사용자 정보 요청
resp = oauth.get(userinfo_url)
user_info = resp.json()
email = user_info.get("email", "")

# 도메인 체크
if not email.endswith("@object-tex.com"):
    st.error("🚫 접근 권한 없음: @object-tex.com 이메일만 허용됩니다.")
    st.stop()

st.success(f"👤 로그인됨: `{email}`")

# --- GPT API 키 환경변수로 설정 ---
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- GSheet 인증: 서비스 계정 JSON 문자열 환경변수로 전달 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "{}"))
credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scope)
gc = gspread.authorize(credentials)

# --- 구글 스프레드시트 ID 환경변수에서 불러옴 ---
spreadsheet_id = os.getenv("SPREADSHEET_ID")

# --- 시트 탭 정의 ---
sheet_map = {
    "기본문의": "25.03 기본문의(자동화)",
    "스와치": "25.03 스와치(자동화)",
    "ORDER LIST": "25.03 ORDER LIST",
    "HOLDING LIST": "25 Holding list"
}

tabs = st.tabs([f"📁 {label}" for label in sheet_map])

# --- 유틸 함수 (상태 컬러 강조) ---
def highlight_status(val):
    if isinstance(val, str):
        if "완료" in val or "회신" in val:
            return "background-color: #d0f0c0"
        elif "보류" in val or "HOLD" in val:
            return "background-color: #ffd1d1"
        else:
            return "background-color: #fff5cc"
    return ""

# --- 특이사항 GPT 요약 ---
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

# --- 재문의 GPT 문장 ---
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

# --- Gmail 회신 체크 ---
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

# --- 탭별 시트 데이터 로딩 ---
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

