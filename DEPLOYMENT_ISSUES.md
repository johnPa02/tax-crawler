# 🚨 Vấn đề khi Deploy lên Server

## ⚠️ Các vấn đề chính

### 1. **SSE (Server-Sent Events) - VẤN ĐỀ LỚN NHẤT**

#### 🐛 Vấn đề:

**A. Reverse Proxy Timeout:**
```
Browser → Nginx/Apache → App
          ↑
      Timeout sau 60s!
```

- **Nginx**: Default timeout = 60s
- **Apache**: Default timeout = 300s  
- **Load Balancer**: Có thể timeout sau 30-60s
- **SSE connection** cần giữ mở lâu (vài phút)

**B. Buffering:**
- Nginx/Apache buffer responses mặc định
- SSE cần real-time streaming
- Progress updates bị buffer → User không thấy progress!

**C. HTTP/2 và Multiplexing:**
- Một số reverse proxy xử lý SSE trên HTTP/2 không tốt
- Connection bị đóng bất ngờ

#### ✅ Giải pháp:

**Cấu hình Nginx:**
```nginx
location /progress/ {
    proxy_pass http://localhost:8102;
    
    # Disable buffering for SSE
    proxy_buffering off;
    proxy_cache off;
    
    # Increase timeouts
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    
    # SSE headers
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding on;
    
    # Disable gzip
    gzip off;
}
```

**Cấu hình Apache:**
```apache
<Location /progress/>
    ProxyPass http://localhost:8102/progress/
    ProxyPassReverse http://localhost:8102/progress/
    
    # Disable buffering
    SetEnv proxy-nokeepalive 1
    SetEnv proxy-sendchunked 1
    
    # Timeout
    ProxyTimeout 300
</Location>
```

---

### 2. **AsyncIO Background Tasks**

#### 🐛 Vấn đề:

```python
# app.py - CURRENT CODE
asyncio.create_task(crawl_in_background())
return {"session_id": session_id}
```

**Issues:**
- Task có thể bị **garbage collected** nếu không giữ reference
- Khi deploy với **multiple workers** (Gunicorn/uvicorn), task chỉ chạy trên 1 worker
- **Worker restart** → Task bị mất giữa chừng
- **No persistence** → Session data mất khi restart

#### ✅ Giải pháp:

**Option 1: Giữ task references**
```python
# app.py
background_tasks = set()

async def crawl_in_background():
    task = asyncio.current_task()
    try:
        # ... crawl code ...
    finally:
        background_tasks.discard(task)

# When creating task
task = asyncio.create_task(crawl_in_background())
background_tasks.add(task)
```

**Option 2: Sử dụng FastAPI BackgroundTasks (RECOMMENDED)**
```python
from fastapi import BackgroundTasks

@app.post("/crawl_csv")
async def crawl_csv(background_tasks: BackgroundTasks, ...):
    background_tasks.add_task(crawl_in_background)
    return {"session_id": session_id}
```

**Option 3: Redis Queue (BEST for production)**
- Dùng Celery/RQ để queue tasks
- Persistent, scalable, fault-tolerant

---

### 3. **In-Memory Progress Store**

#### 🐛 Vấn đề:

```python
# app.py - CURRENT CODE
progress_store: Dict[str, Dict] = {}
```

**Issues:**
- **Multiple workers**: Mỗi worker có progress_store riêng
- Worker 1 xử lý upload → Worker 2 xử lý SSE → Không thấy progress!
- **Memory leak**: Sessions không cleanup nếu client disconnect
- **Server restart**: Mất hết data

#### ✅ Giải pháp:

**Option 1: Redis (RECOMMENDED)**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def update_progress(session_id, data):
    redis_client.setex(
        f"progress:{session_id}",
        600,  # TTL 10 minutes
        json.dumps(data)
    )

def get_progress(session_id):
    data = redis_client.get(f"progress:{session_id}")
    return json.loads(data) if data else None
```

**Option 2: Database (PostgreSQL/MySQL)**
```python
# Store progress in database table
CREATE TABLE progress (
    session_id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Option 3: Single worker mode**
```bash
# Chỉ chạy 1 worker
uvicorn app:app --workers 1 --host 0.0.0.0 --port 8102
```

---

### 4. **Playwright/Browser trong Docker**

#### 🐛 Vấn đề:

```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

**Issues:**
- Chromium cần nhiều dependencies
- File size image lớn (~1-2GB)
- Memory usage cao khi crawl
- Có thể thiếu fonts, libraries

#### ✅ Giải pháp:

**Dockerfile improvements:**
```dockerfile
FROM python:3.11-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set Playwright env vars
ENV PLAYWRIGHT_BROWSERS_PATH=/app/browsers
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
```

---

### 5. **Networking & Ports**

#### 🐛 Vấn đề:

```dockerfile
EXPOSE 8102
```

**Issues:**
- Port conflicts nếu có services khác
- Firewall có thể block
- Load balancer cần cấu hình đúng

#### ✅ Giải pháp:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  tax-crawler:
    build: .
    ports:
      - "8102:8102"
    environment:
      - HOST=0.0.0.0
      - PORT=8102
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - tax-crawler
```

---

### 6. **File Upload Limits**

#### 🐛 Vấn đề:

CSV files có thể lớn, bị limit bởi:
- Nginx: `client_max_body_size` default = 1MB
- FastAPI: Không có default limit nhưng có thể slow

#### ✅ Giải pháp:

**nginx.conf:**
```nginx
http {
    client_max_body_size 10M;  # Allow 10MB uploads
}
```

---

### 7. **CORS (nếu frontend riêng domain)**

#### 🐛 Vấn đề:

SSE từ domain khác bị block

#### ✅ Giải pháp:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 8. **Logging & Monitoring**

#### 🐛 Vấn đề:

`print()` statements không tốt cho production

#### ✅ Giải pháp:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Replace print() with logger
logger.info(f"Processing {len(tax_codes)} tax codes")
```

---

## 🔥 CRITICAL FIXES CẦN LÀM NGAY

### 1. Fix SSE Nginx Config (PRIORITY 1)

```nginx
# /etc/nginx/sites-available/tax-crawler
server {
    listen 80;
    server_name yourdomain.com;
    
    # SSE endpoint - NO BUFFERING
    location /progress/ {
        proxy_pass http://localhost:8102;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        chunked_transfer_encoding on;
    }
    
    # Regular endpoints
    location / {
        proxy_pass http://localhost:8102;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Use Redis for Progress Store (PRIORITY 2)

**Update app.py:**
```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

def update_progress(session_id: str, data: dict):
    redis_client.setex(
        f"progress:{session_id}",
        600,  # 10 minutes TTL
        json.dumps(data)
    )

def get_progress(session_id: str) -> dict:
    data = redis_client.get(f"progress:{session_id}")
    return json.loads(data) if data else None

# Replace progress_store with Redis calls
```

**Update docker-compose.yml:**
```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  tax-crawler:
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
```

### 3. Handle Worker Restarts

**Update app.py:**
```python
from fastapi import BackgroundTasks

@app.post("/crawl_csv")
async def crawl_csv(
    background_tasks: BackgroundTasks,
    request: Request, 
    file: UploadFile = File(...)
):
    # ... validation ...
    
    # Use FastAPI BackgroundTasks
    background_tasks.add_task(
        crawl_and_update_progress,
        session_id,
        tax_codes,
        batch_size,
        delay_range
    )
    
    return {"session_id": session_id}
```

---

## 📋 Deployment Checklist

- [ ] Configure Nginx/Apache for SSE (disable buffering, increase timeout)
- [ ] Add Redis for progress storage (or use single worker)
- [ ] Use FastAPI BackgroundTasks instead of asyncio.create_task
- [ ] Add proper logging (replace print statements)
- [ ] Configure file upload limits
- [ ] Add health checks
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure CORS if needed
- [ ] Add environment variables for config
- [ ] Test SSE with production-like setup
- [ ] Add graceful shutdown handling
- [ ] Configure memory limits in Docker

---

## 🧪 Test SSE on Production

```bash
# Test SSE endpoint
curl -N http://yourdomain.com/progress/test-session-id

# Should see:
data: {"status": "waiting", "message": "..."}
data: {"status": "processing", "completed": 5, ...}
```

---

## 🚀 Recommended Production Setup

```
                 ┌─────────────┐
                 │   Nginx     │
                 │  (Reverse   │
                 │   Proxy)    │
                 └──────┬──────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
   │ Worker1 │    │ Worker2 │    │ Worker3 │
   │ (App)   │    │ (App)   │    │ (App)   │
   └────┬────┘    └────┬────┘    └────┬────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
                  ┌─────▼─────┐
                  │   Redis   │
                  │ (Progress) │
                  └───────────┘
```

**Better: Single Worker for simplicity**
```
     Nginx → Single App Worker → Redis (optional)
```

