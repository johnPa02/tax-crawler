# Tax Crawler — API Documentation

Base URL: `http://<host>:8102`

Swagger UI: `http://<host>:8102/docs`

---

## 1. Tra cứu 1 MST

```
GET /api/lookup/{tax_code}
```

**Response** `200 OK`:
```json
{
  "status": "success",
  "data": {
    "Tên": "CÔNG TY TNHH ABC",
    "MST": "0318735609",
    "Địa chỉ": "...",
    "Người đại diện": "...",
    "Tình trạng": "Đang hoạt động",
    "Ngày hoạt động": "01/01/2020",
    "Quản lý bởi": "Chi cục Thuế ...",
    "Loại hình DN": "Công ty TNHH",
    "Ngành nghề kinh doanh": "..."
  }
}
```

**Error** `500`:
```json
{ "status": "error", "message": "..." }
```

---

## 2. Upload CSV — Đồng bộ (Sync)

Gửi file CSV, chờ crawl xong, nhận thẳng file Excel.

> ⚠️ Phù hợp cho danh sách nhỏ (≤ 20 MST). Request sẽ block cho đến khi crawl xong.

```
POST /api/lookup_csv
Content-Type: multipart/form-data
```

| Field  | Type | Mô tả |
|--------|------|--------|
| `file` | file | File CSV, phải có cột `dinh_danh_doanh_nghiep` |

**CSV mẫu:**
```csv
dinh_danh_doanh_nghiep
0318735609
0200837003
```

**Response** `200 OK`: file `.xlsx` (binary download)

**Error** `400`:
```json
{ "status": "error", "message": "CSV phải có cột 'dinh_danh_doanh_nghiep'" }
```

### Ví dụ curl

```bash
curl -X POST http://localhost:8102/api/lookup_csv \
  -F "file=@danh_sach_mst.csv" \
  -o ket_qua.xlsx
```

### Ví dụ Python

```python
import requests

with open("danh_sach_mst.csv", "rb") as f:
    resp = requests.post(
        "http://localhost:8102/api/lookup_csv",
        files={"file": ("mst.csv", f, "text/csv")}
    )

if resp.status_code == 200:
    with open("ket_qua.xlsx", "wb") as out:
        out.write(resp.content)
    print("Tải Excel thành công!")
else:
    print("Lỗi:", resp.json())
```

---

## 3. Upload CSV — Bất đồng bộ (Async)

Gửi CSV, nhận `session_id` ngay, sau đó poll tiến độ và lấy kết quả.

> ✅ Phù hợp cho danh sách lớn. Không block request.

### Bước 1: Upload CSV

```
POST /api/lookup_csv/async
Content-Type: multipart/form-data
```

| Field  | Type | Mô tả |
|--------|------|--------|
| `file` | file | File CSV, phải có cột `dinh_danh_doanh_nghiep` |

**Response** `200 OK`:
```json
{
  "session_id": "685b6a71-cd71-4188-a5a1-89abb748df97",
  "status": "started",
  "total": 10
}
```

### Bước 2: Theo dõi tiến độ (SSE)

```
GET /api/progress/{session_id}
Accept: text/event-stream
```

Server gửi **Server-Sent Events**. Mỗi event:

```
data: {"status":"processing","total":10,"completed":3,"current":"0319025785","message":"Crawling 0319025785...","percentage":30}

data: {"status":"completed","total":10,"completed":10,"message":"Crawling completed!","percentage":100}
```

| `status` | Ý nghĩa |
|----------|---------|
| `waiting` | Session chưa sẵn sàng |
| `processing` | Đang crawl |
| `completed` | Xong, có thể lấy kết quả |
| `error` | Lỗi |

> Stream tự đóng khi `status` là `completed` hoặc `error`.

### Bước 3a: Tải kết quả Excel

```
GET /api/results/{session_id}/excel
```

| HTTP Code | Ý nghĩa |
|-----------|---------|
| `200` | File `.xlsx` (binary) — session bị xóa sau khi tải |
| `202` | Đang crawl, thử lại sau (`{"status":"processing","percentage":50}`) |
| `404` | Session không tồn tại hoặc đã hết hạn |
| `500` | Lỗi crawl |

### Bước 3b: Lấy kết quả JSON

```
GET /api/results/{session_id}/json
```

**Response** `200 OK`:
```json
{
  "status": "success",
  "total": 2,
  "data": [
    {
      "Tên": "CÔNG TY TNHH ABC",
      "MST": "0318735609",
      "Địa chỉ": "...",
      ...
    },
    {
      "Tên": "CÔNG TY CP XYZ",
      "MST": "0200837003",
      ...
    }
  ]
}
```

> ⚠️ Session bị **xóa** sau khi gọi `/excel` hoặc `/json`. Chỉ lấy được **một lần**.

### Ví dụ Python — Flow bất đồng bộ

```python
import requests
import sseclient  # pip install sseclient-py
import time

BASE = "http://localhost:8102"

# Bước 1: Upload CSV
with open("danh_sach_mst.csv", "rb") as f:
    resp = requests.post(f"{BASE}/api/lookup_csv/async", files={"file": f})
    data = resp.json()
    session_id = data["session_id"]
    print(f"Session: {session_id}, Total: {data['total']}")

# Bước 2: Theo dõi tiến độ (SSE)
resp = requests.get(f"{BASE}/api/progress/{session_id}", stream=True)
client = sseclient.SSEClient(resp)
for event in client.events():
    import json
    progress = json.loads(event.data)
    print(f"[{progress.get('percentage', 0)}%] {progress.get('message', '')}")
    if progress["status"] in ("completed", "error"):
        break

# Bước 3: Tải Excel
resp = requests.get(f"{BASE}/api/results/{session_id}/excel")
if resp.status_code == 200:
    with open("ket_qua.xlsx", "wb") as f:
        f.write(resp.content)
    print("✅ Tải Excel thành công!")

# Hoặc lấy JSON:
# resp = requests.get(f"{BASE}/api/results/{session_id}/json")
# results = resp.json()["data"]
```

### Ví dụ JavaScript (Node.js)

```javascript
const FormData = require("form-data");
const fs = require("fs");
const axios = require("axios");
const EventSource = require("eventsource");

const BASE = "http://localhost:8102";

async function crawlCSV(csvPath) {
  // Bước 1: Upload
  const form = new FormData();
  form.append("file", fs.createReadStream(csvPath));
  const { data } = await axios.post(`${BASE}/api/lookup_csv/async`, form);
  const { session_id, total } = data;
  console.log(`Session: ${session_id}, Total: ${total}`);

  // Bước 2: SSE progress
  await new Promise((resolve) => {
    const es = new EventSource(`${BASE}/api/progress/${session_id}`);
    es.onmessage = (e) => {
      const p = JSON.parse(e.data);
      console.log(`[${p.percentage || 0}%] ${p.message}`);
      if (p.status === "completed" || p.status === "error") {
        es.close();
        resolve();
      }
    };
  });

  // Bước 3: Download Excel
  const resp = await axios.get(`${BASE}/api/results/${session_id}/excel`, {
    responseType: "arraybuffer",
  });
  fs.writeFileSync("ket_qua.xlsx", resp.data);
  console.log("✅ Done!");
}

crawlCSV("danh_sach_mst.csv");
```

---

## Lưu ý kỹ thuật

- **Progress store**: tiến trình lưu **in-memory** (dict Python). Restart container = mất session.
- **Single worker**: bắt buộc chạy 1 worker (`--workers 1`) để đảm bảo progress store dùng chung.
- **Session tự huỷ**: session bị xóa sau khi client lấy kết quả (gọi `/excel` hoặc `/json`).
- **Rate limit**: crawler delay giữa các request (1–5s tuỳ batch size) để tránh bị block bởi masothue.com.
- **Captcha**: nếu masothue.com bật captcha, kết quả sẽ có `Error: "Bị chặn bởi captcha..."`.
