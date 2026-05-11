FROM python:3.10-slim

WORKDIR /app

# psycopg2-binary bundles libpq so no extra system deps needed
RUN rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Cloud Run injects PORT at runtime (default: 8080).
# The default here must match the container_port declared in terraform/cloud_run.tf.
ENV PORT=8080

# Use the PORT env var so the binding stays in sync with Cloud Run's injected value
# and with the container_port declared in Terraform.  Previously this was hardcoded
# to 8080 while Terraform declared container_port=5000, causing Cloud Run's ingress
# to forward requests to an unbound port and return 502 responses with no CORS headers.
CMD gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 120 app:app
