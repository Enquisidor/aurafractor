FROM python:3.10-slim

WORKDIR /app

# Runtime system deps only (psycopg2-binary bundles libpq; no build-essential needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Cloud Run injects PORT; default to 8080
ENV PORT=8080

CMD exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 120 "app:app"
