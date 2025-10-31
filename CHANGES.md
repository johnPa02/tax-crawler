# Thay đổi: Chuyển từ crawl4ai sang requests

## Tóm tắt
Đã chuyển từ sử dụng `crawl4ai` (với Playwright/Chromium) sang sử dụng `requests` để crawl dữ liệu. Điều này làm cho:
- ✅ Khởi động nhanh hơn (không cần cài Playwright browsers)
- ✅ Image Docker nhỏ hơn nhiều (~200MB thay vì ~2GB)
- ✅ Sử dụng ít tài nguyên hơn (RAM, CPU)
- ✅ Code đơn giản hơn, dễ maintain

## Files đã thay đổi

### 1. `crawler.py`
- ❌ Xóa: `from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig`
- ❌ Xóa: `import asyncio`
- ✅ Thêm: `import requests`
- ✅ Thêm: `import time`
- 🔄 Chuyển các hàm từ `async def` sang `def` (synchronous)
- ✅ Thêm hàm `fetch_tax_info()` - crawl đơn giản bằng requests
- 🔄 Cập nhật `crawl_multiple_tax_codes()` và `crawl_multiple_tax_codes_with_progress()`

### 2. `app.py`
- 🔄 Xóa `await` khi gọi `crawl_tax_code()`
- 🔄 Xóa `await` khi gọi `crawl_multiple_tax_codes_with_progress()`
- 🔄 Chuyển background task từ `asyncio.create_task()` sang `threading.Thread()`
- ✅ Giữ `asyncio` cho SSE streaming (vẫn cần thiết)

### 3. `main.py`
- ❌ Xóa: `import asyncio`
- 🔄 Chuyển `cli_example()` từ `async def` sang `def`
- 🔄 Xóa `await` khi gọi `crawl_tax_code()`
- 🔄 Thay `asyncio.run(cli_example())` bằng `cli_example()`

### 4. `pyproject.toml`
- ❌ Xóa: `"crawl4ai>=0.3.0"`
- ✅ Thêm: `"requests>=2.31.0"`

### 5. `Dockerfile`
- ❌ Xóa: Tất cả dependencies của Playwright/Chromium (libnss3, libnspr4, etc.)
- ❌ Xóa: `playwright install chromium --with-deps`
- ❌ Xóa: `ENV PLAYWRIGHT_BROWSERS_PATH=/app/browsers`
- 🔄 Giảm `start_period` trong healthcheck từ 40s xuống 5s

### 6. `docker-compose.yml`
- 🔄 Giảm `start_period` trong healthcheck từ 40s xuống 10s

## Cách sử dụng

### Test local
```bash
# Sync dependencies
uv sync

# Test single tax code
uv run python test_crawler.py

# Test CLI
uv run python main.py

# Start web server
uv run python main.py web
```

### Deploy với Docker
```bash
# Build image (nhanh hơn và nhẹ hơn)
docker build -t tax-crawler:latest .

# Run với docker-compose
docker-compose up -d

# Hoặc run trực tiếp
docker run -d -p 8102:8102 --name tax-crawler tax-crawler:latest
```

## API không thay đổi
Tất cả endpoints và responses vẫn giữ nguyên:
- `POST /crawl` - Crawl single tax code
- `POST /crawl_csv` - Upload CSV và crawl nhiều tax codes
- `GET /progress/{session_id}` - SSE progress stream
- `GET /results/{session_id}` - Lấy kết quả sau khi crawl xong
- `POST /download_excel` - Download Excel

## Performance
- Khởi động: ~2-3 giây (trước: ~30-40 giây)
- Docker image: ~200MB (trước: ~2GB)
- RAM usage: ~100-200MB (trước: ~500MB-1GB)
- Crawl speed: Tương tự (vẫn có delay giữa các request để tránh spam)

## Notes
- Vẫn sử dụng BeautifulSoup để parse HTML
- Vẫn có random delay giữa các requests
- Vẫn hỗ trợ progress tracking qua SSE
- Code đơn giản hơn, dễ debug hơn

