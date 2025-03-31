# Python 버전 선택 (여기서는 Python 3.10을 사용)
FROM python:3.10-slim

# 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 시스템 패키지 설치 (git 포함)
RUN apt-get update && apt-get install -y git build-essential

# 작업 디렉토리 설정
WORKDIR /app

# 로컬 파일 복사 (현재 디렉토리의 모든 파일을 컨테이너의 /app으로 복사)
COPY . .

# pip 업그레이드 및 의존성 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 앱 실행 명령 (Cloud Run에서의 포트 번호는 자동으로 설정되므로, 환경 변수로 받아옴)
CMD streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
