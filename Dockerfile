FROM python:3.10-slim

WORKDIR /app
COPY . .

# ✅ 여기서 git 설치 추가
RUN apt-get update && apt-get install -y git

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
