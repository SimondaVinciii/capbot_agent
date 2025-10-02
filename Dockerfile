# syntax=docker/dockerfile:1

# Base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app

# Install system dependencies
# - build-essential, unixodbc-dev for building pyodbc
# - msodbcsql18 for SQL Server connectivity (matches "ODBC Driver 18 for SQL Server")
# - libgomp1 for sentence-transformers/torch CPU kernels
# - curl, gnupg, ca-certificates for adding Microsoft repository
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       ca-certificates \
       gnupg \
       unixodbc \
       unixodbc-dev \
       libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    # Add Microsoft repository for msodbcsql18 (Debian 12 - bookworm)
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first (better cache)
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default environment variables
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    DEBUG=False \
    CHROMA_DB_PATH=/app/chroma_db \
    # If your DATABASE_URL uses Driver 17, consider updating to Driver 18 inside the container
    DATABASE_URL="mssql+pyodbc://username:password@server/db?driver=ODBC+Driver+18+for+SQL+Server"

# Create writable directory for Chroma DB
RUN mkdir -p /app/chroma_db && chmod -R 775 /app/chroma_db

# Expose service port
EXPOSE 8000

# Basic TCP healthcheck (can be replaced with HTTP /api/v1/health)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

# Run the app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

