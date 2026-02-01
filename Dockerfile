# Dockerfile for Constitution Accountability Agent
# This builds a container image that runs the FastAPI application

# ===== Base Image =====
# Use official Python 3.11 slim image (lighter than full Python image)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# ===== System Dependencies =====
# Install system packages needed by Python libraries
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===== Python Dependencies =====
# Copy requirements-phase1.txt first (for Docker layer caching)
# Phase 1 dependencies only (no LangChain conflicts)
# If requirements-phase1.txt doesn't change, Docker reuses this layer (faster builds)
COPY requirements-phase1.txt .

# Install Python dependencies
# --no-cache-dir: Don't cache pip packages (smaller image)
RUN pip install --no-cache-dir -r requirements-phase1.txt

# ===== Application Code =====
# Copy entire application
COPY . .

# ===== Environment Variables =====
# These can be overridden by Cloud Run
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV ENVIRONMENT=production

# ===== Expose Port =====
# Document which port the app listens on
EXPOSE 8000

# ===== Health Check =====
# Docker can periodically check if container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ===== Run Application =====
# Use exec form (not shell form) for better signal handling
# Cloud Run sets $PORT environment variable
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
