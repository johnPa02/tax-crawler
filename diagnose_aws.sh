#!/bin/bash

# AWS Server Diagnostic Script
# Run this on your AWS server to check for common issues

echo "================================================"
echo "Tax Crawler - AWS Server Diagnostics"
echo "================================================"

# Check Python version
echo ""
echo "[1] Python Version:"
python3 --version

# Check if crawl4ai is installed
echo ""
echo "[2] Checking crawl4ai installation:"
python3 -c "import crawl4ai; print(f'✓ crawl4ai version: {crawl4ai.__version__}')" 2>&1

# Check Playwright
echo ""
echo "[3] Checking Playwright:"
python3 -c "from playwright.sync_api import sync_playwright; print('✓ Playwright module found')" 2>&1

# Check if Chromium is installed
echo ""
echo "[4] Checking Chromium browser:"
if command -v chromium &> /dev/null || command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium found in PATH"
else
    echo "⚠ Chromium not found in PATH (might be in Playwright's cache)"
fi

# Check Playwright browsers
echo ""
echo "[5] Checking Playwright browsers:"
python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print('✓ Playwright can start'); p.stop()" 2>&1

# Check for common missing dependencies
echo ""
echo "[6] Checking system dependencies:"
DEPS=(
    "libnss3"
    "libnspr4"
    "libatk1.0-0"
    "libatk-bridge2.0-0"
    "libcups2"
    "libdrm2"
    "libxkbcommon0"
    "libxcomposite1"
    "libxdamage1"
    "libxfixes3"
    "libxrandr2"
    "libgbm1"
)

for dep in "${DEPS[@]}"; do
    if dpkg -l | grep -q "^ii.*$dep"; then
        echo "  ✓ $dep"
    else
        echo "  ✗ $dep - MISSING!"
    fi
done

# Check available memory
echo ""
echo "[7] System Resources:"
free -h | grep "Mem:"
echo "CPU cores: $(nproc)"

# Check if X11 display is set (needed for headed mode)
echo ""
echo "[8] Display:"
if [ -z "$DISPLAY" ]; then
    echo "✓ No DISPLAY set (good for headless)"
else
    echo "DISPLAY=$DISPLAY"
fi

# Test actual crawl
echo ""
echo "[9] Testing actual crawl:"
cd /home/ubuntu/tax-crawler 2>/dev/null || cd /app 2>/dev/null || cd .
if [ -f "test_aws_crawl.py" ]; then
    python3 test_aws_crawl.py
else
    echo "⚠ test_aws_crawl.py not found"
fi

echo ""
echo "================================================"
echo "Diagnostics Complete"
echo "================================================"
echo ""
echo "Common fixes:"
echo "1. If Chromium missing: playwright install chromium"
echo "2. If deps missing: playwright install-deps chromium"
echo "3. If permission issues: Check file permissions"
echo "4. If memory issues: Increase instance size"
echo ""

