import streamlit as st

def check_user_auth():
    email = st.experimental_user.email if hasattr(st.experimental_user, "email") else None
    if not email or not email.endswith("@object-tex.com"):
        st.error("🚫 접근 권한이 없습니다. 회사 이메일(@object-tex.com)로 로그인해주세요.")
        st.stop()
    return email
