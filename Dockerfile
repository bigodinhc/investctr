# Dockerfile for Railway deployment
# Builds the FastAPI backend from the monorepo

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini .

# Expose port
EXPOSE 8000

# Railway sets PORT dynamically
ENV PORT=8000

# Run the application with shell to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
