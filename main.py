import streamlit as st
import os
from authlib.integrations.requests_client import OAuth2Session

# ✅ 환경변수 가져오기
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")  # 예: https://your-app-id.a.run.app
token_url = "https://oauth2.googleapis.com/token"
authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"

# ✅ 기본 UI
st.set_page_config(layout="centered")
st.title("🔐 Google OAuth 최소 예제")

# ✅ OAuth 세션
oauth = OAuth2Session(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope="openid email profile"
)

# ✅ 인증되지 않았으면 로그인 URL 생성
if "code" not in st.query_params:
    auth_url, state = oauth.create_authorization_url(authorize_url)
    st.markdown(f"[👉 Google 로그인]({auth_url})", unsafe_allow_html=True)
    st.stop()

# ✅ 콜백 처리
code = st.query_params["code"][0]
st.write("✅ 인증 코드:", code)

authorization_response = f"{redirect_uri}?code={code}"

# ✅ 토큰 발급
try:
    token = oauth.fetch_token(
        url=token_url,
        code=code,
        authorization_response=authorization_response,
        client_secret=client_secret,
        include_client_id=True
    )
    st.success("✅ 토큰 발급 성공")
    st.json(token)

    # ✅ 사용자 정보 요청
    userinfo = oauth.get(userinfo_url).json()
    st.write("👤 사용자 정보:", userinfo)

except Exception as e:
    st.error(f"❌ 토큰 발급 실패: {e}")
