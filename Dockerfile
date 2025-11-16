# Use Python 3.11 slim image
FROM python:3.11-slim

# Set base working directory
WORKDIR /app

# Install system dependencies (cached unless OS packages change)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first (cached unless requirements.txt changes)
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source (this layer rebuilds when code changes)
COPY backend ./backend

# Switch into backend folder so `app.*` imports work
WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Start FastAPI via Uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

