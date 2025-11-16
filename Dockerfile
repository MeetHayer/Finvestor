# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (cached unless OS packages change)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first (cached unless requirements.txt changes)
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies (cached unless requirements.txt changes)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code (this layer rebuilds when code changes)
COPY backend/app ./backend/app

# Expose port
EXPOSE 8000

# Run the application
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}

