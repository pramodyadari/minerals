# ==============================================================================
# AI Mineral Exploration & Intelligence System — Production Multi-Stage Dockerfile
# Optimized for Railway, Render, and Google Cloud Run
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build React/Vite Frontend
# ------------------------------------------------------------------------------
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Python 3.11 Runtime with Geospatial GDAL & PyTorch CPU
# ------------------------------------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install native GDAL, PROJ, and system build libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure GDAL environment variables for rasterio
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install PyTorch CPU-only (drastically cuts image size from ~2.5GB to ~200MB)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application, models, and data assets
COPY backend/ ./backend/
COPY models/ ./models/
COPY data/ ./data/

# Copy built frontend assets into the distribution directory for static mounting
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose default port (Railway automatically injects $PORT at runtime)
EXPOSE 8001
ENV PORT=8001

# Start Uvicorn bound to Railway dynamic $PORT (or 8001 by default)
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8001}
