
FROM python:3.9-slim   

WORKDIR /app

# Install build tools only if you need them
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure expected dirs exist
RUN mkdir -p static templates

EXPOSE 8000  

ENV PYTHONUNBUFFERED=1

# ---- START COMMAND ----
# Cloud Run sets $PORT; default to 8000 for local dev
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
# ----  END  COMMAND  ----
