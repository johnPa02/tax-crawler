# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc \
    g++ \
    curl \
    wget \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    # Fonts
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Install playwright browsers (required for crawl4ai)
ENV PLAYWRIGHT_BROWSERS_PATH=/app/browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p templates data

# Non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8102

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8102/ || exit 1

# Run with single worker for in-memory progress store
# Use --workers 1 to avoid issues with SSE and progress tracking
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8102", "--workers", "1"]

