FROM python:3.10-slim

# 환경변수 미리 설정 (권장)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리
WORKDIR /app

# 의존성 설치를 위한 system package 업데이트 (권장)
RUN apt-get update && apt-get install -y build-essential

# 코드 복사
COPY . .

# pip 업그레이드 & 패키지 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt  # 이곳에 'authlib' 포함된 파일 사용

# 포트에 맞게 실행
CMD streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
