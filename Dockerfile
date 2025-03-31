FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Cloud Run은 PORT 환경변수를 전달해주므로 그걸 streamlit에 넘겨야 함
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
