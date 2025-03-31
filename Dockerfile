FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
