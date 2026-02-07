# Dockerfile for Constitution Accountability Agent
# This builds a container image that runs the FastAPI application

# ===== Base Image =====
# Use official Python 3.11 slim image (lighter than full Python image)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# ===== System Dependencies =====
# Install system packages needed by Python libraries
# Phase 3F additions:
# - fontconfig, fonts-dejavu-core: For matplotlib font rendering
# - libfreetype6: Font library for matplotlib
# - libjpeg62-turbo, zlib1g: Image libraries for Pillow
RUN apt-get update && apt-get install -y \
    curl \
    fontconfig \
    fonts-dejavu-core \
    libfreetype6 \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# ===== Python Dependencies =====
# Copy requirements.txt first (for Docker layer caching)
# Phase 2 dependencies (includes Vertex AI for Gemini)
# If requirements.txt doesn't change, Docker reuses this layer (faster builds)
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't cache pip packages (smaller image)
RUN pip install --no-cache-dir -r requirements.txt

# ===== Application Code =====
# Copy entire application
COPY . .

# ===== Environment Variables =====
# These will be set by Cloud Run
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# ===== Expose Port =====
# Cloud Run will set PORT environment variable (typically 8080)
# EXPOSE is just documentation, actual port comes from $PORT
EXPOSE 8080

# ===== Health Check =====
# Cloud Run has its own health checks, so disable Docker healthcheck
# (it was checking wrong port anyway)
# HEALTHCHECK NONE

# ===== Run Application =====
# Use exec form (not shell form) for better signal handling
# Cloud Run sets $PORT environment variable
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
