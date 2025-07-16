# ====================================================================================
# Azure Production Dockerfile
#
# This Dockerfile is optimized for production builds. It focuses on:
#   1. Security: Removing secrets and running as a non-root user.
#   2. Efficiency: Structuring commands to leverage Docker's build cache.
#   3. Minimizing Size: Cleaning up unnecessary files after installation.
#
# ⭐️ BEST PRACTICE: Create a .dockerignore file in your project root to
# prevent files like .git, .env, and venv/ from being copied into the image.
# ====================================================================================

# Use a specific slim image version for reproducible builds
FROM python:3.12.9-slim

# Set environment variables
# - PYTHONUNBUFFERED: Ensures that Python output is sent straight to the terminal.
# - PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app" \
    # Add paths for system utilities
    PATH="/root/.local/bin:${PATH}"

# --- 1. Install System Dependencies ---
# Install all OS packages in a single layer to optimize image size.
# Includes build tools, libraries for Python packages, and utilities.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    gcc \
    make \
    # Python package dependencies
    libffi-dev \
    libjpeg-dev \
    libtiff-dev \
    zlib1g-dev \
    libx11-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    libtesseract-dev \
    libopenjp2-7-dev \
    libfontconfig1-dev \
    libxext-dev \
    libxrender-dev \
    libpng-dev \
    libmagickwand-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    libgl1-mesa-glx \
    # Application dependencies
    tesseract-ocr \
    ocrmypdf \
    poppler-utils \
    ghostscript \
    imagemagick \
    # Utilities
    procps \
    coreutils \
    curl \
    netcat-openbsd \
    postgresql-client \
    file \
    supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- 2. Install Python Dependencies ---
# Copy only the requirements file first to leverage Docker cache.
# This layer is only rebuilt when the requirements file changes.
WORKDIR /app
COPY production_requirements.txt .

# Upgrade pip and install packages from requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r production_requirements.txt

# --- 3. Copy Application Code & Assets ---
# Copy the rest of the application code into the image.
# With a .dockerignore file, this won't include .env, .git, etc.
COPY . .

# --- 4. Configure Application ---
# - Set permissions for entrypoint scripts.
# - Create necessary directories for logs and media files.
# - Run collectstatic to gather all static files for serving.
# - Set ownership of the app directory.
RUN chmod +x /app/entrypoint.sh /app/wait-for-it.sh && \
    mkdir -p /app/media /app/logs /var/log/supervisor && \
    python manage.py collectstatic --noinput && \
    chown -R www-data:www-data /app

# --- 5. Final Configuration ---
# Set the user to a non-root user for better security.
USER www-data

# Expose the port the application runs on.
# In Azure, this internal port will be mapped to the public-facing port (80/443).
EXPOSE 8020

# The entrypoint script will start the application.
ENTRYPOINT ["/app/entrypoint.sh"]

