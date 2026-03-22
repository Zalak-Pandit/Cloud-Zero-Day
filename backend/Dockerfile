FROM python:3.11-slim

WORKDIR /app

# System deps for numpy/torch
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Pre-create models dir
RUN mkdir -p /app/models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]