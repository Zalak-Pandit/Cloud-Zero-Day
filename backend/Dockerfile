FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install only what's actually needed (no torch, no torch-geometric)
COPY requirements-slim.txt .
RUN pip install --no-cache-dir -r requirements-slim.txt

COPY app/ ./app/
RUN mkdir -p /app/models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]