# ==========================================
# STAGE 1: BASE IMAGE
# ==========================================
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# ==========================================
# STAGE 2: INSTALL SYSTEM DEPENDENCIES
# ==========================================
# gcc, libpq-dev => required for psycopg2 (PostgreSQL driver)
# curl => for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# STAGE 3: INSTALL PYTHON DEPENDENCIES
# ==========================================
# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ==========================================
# STAGE 4: COPY APPLICATION CODE
# ==========================================
COPY . .

# Create a non-root user (SECURITY BEST PRACTICE)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# ==========================================
# STAGE 5: EXPOSE PORT & RUN
# ==========================================
EXPOSE 8000

# Health check (Docker will auto-restart if this fails)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]