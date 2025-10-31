# ---- Base Image ----
FROM python:3.11-slim-bookworm

# ---- Working Dir ----
WORKDIR /app

# ---- Install system dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg \
    build-essential \
    # Browser dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libatspi2.0-0 libwayland-client0 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# ---- Install uv + uvloop ----
RUN pip install --no-cache-dir uv uvloop

# ---- Copy project metadata ----
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system -e .

# ---- Install Playwright Chromium ----
ENV PLAYWRIGHT_BROWSERS_PATH=/app/browsers
RUN playwright install chromium --with-deps

# ---- Copy application code ----
COPY . .

# ---- Optimize AsyncIO ----
ENV PYTHONUNBUFFERED=1
ENV UVICORN_WORKERS=1
ENV UVICORN_PORT=8102
ENV UVLOOP=1

# ---- Create folders ----
RUN mkdir -p templates data

# ---- Add non-root user ----
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ---- Expose Port ----
EXPOSE 8102

# ---- Healthcheck ----
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8102/ || exit 1

# ---- Run Command ----
CMD ["bash", "-c", "python -m uvloop app:app || uvicorn app:app --host 0.0.0.0 --port 8102 --workers 1"]
