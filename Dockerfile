# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Streamlit-specific configs (optional for Cloud Run)
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

CMD ["streamlit", "run", "object_dashboard_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
