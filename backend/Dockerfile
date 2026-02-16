# ===== Stage 1: Builder =====
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user --extra-index-url https://download.pytorch.org/whl/cpu -e .

# ===== Stage 2: Runtime =====
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home appuser

# Copy installed packages from builder to appuser's home (with ownership set during copy)
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Switch to non-root user
USER appuser

# Ensure scripts are in PATH for appuser
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser backend/src/ ./src/
COPY --chown=appuser:appuser backend/migrations/ ./migrations/
COPY --chown=appuser:appuser backend/data/ ./data/
COPY --chown=appuser:appuser config/ ./config/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
