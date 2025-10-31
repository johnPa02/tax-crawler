# Kỹ thuật tránh bị chặn khi crawl

## Các kỹ thuật đã implement:

### 1. **Batch Processing (Xử lý theo lô)**
- Chia danh sách mã số thuế thành các batch nhỏ (mặc định 3 codes/batch)
- Tránh gửi quá nhiều request cùng lúc
- Có thể điều chỉnh: `batch_size=3`

### 2. **Random Delays (Delay ngẫu nhiên)**
- Thêm delay ngẫu nhiên giữa các batch (mặc định 2-5 giây)
- Tránh pattern đều đặn có thể bị phát hiện
- Có thể điều chỉnh: `delay_range=(2, 5)`

### 3. **Browser Configuration (Cấu hình trình duyệt)**
```python
BrowserConfig(
    headless=True,  # Chạy ẩn
    extra_args=[
        "--disable-blink-features=AutomationControlled",  # Ẩn dấu hiệu automation
        "--disable-dev-shm-usage",  # Tối ưu memory
        "--no-sandbox",  # Tránh lỗi permission
        "--disable-web-security",  # Bypass CORS
    ]
)
```

### 4. **Random Timing**
- `delay_before_return_html=random.uniform(1.5, 3)` - Delay ngẫu nhiên trước khi lấy HTML
- Giống hành vi người dùng thật hơn

## Cách sử dụng:

### Cơ bản (mặc định):
```python
results = await crawl_multiple_tax_codes(tax_codes)
```

### Tùy chỉnh batch size và delay:
```python
# Batch nhỏ hơn, an toàn hơn nhưng chậm hơn
results = await crawl_multiple_tax_codes(
    tax_codes, 
    batch_size=2,      # 2 codes mỗi lần
    delay_range=(3, 7)  # Delay 3-7 giây giữa các batch
)

# Batch lớn hơn, nhanh hơn nhưng rủi ro cao hơn
results = await crawl_multiple_tax_codes(
    tax_codes, 
    batch_size=5,      # 5 codes mỗi lần
    delay_range=(1, 3)  # Delay 1-3 giây
)
```

## Khuyến nghị:

### Nếu bị chặn:
1. **Giảm batch_size**: Từ 3 → 2 hoặc 1
2. **Tăng delay_range**: Từ (2,5) → (5,10)
3. **Thêm proxy** (nếu cần):
   - Sử dụng rotating proxy
   - Hoặc residential proxy

### Nếu crawl số lượng lớn (>100 codes):
```python
# Ví dụ: 500 mã số thuế
results = await crawl_multiple_tax_codes(
    tax_codes, 
    batch_size=2,       # Rất nhỏ để an toàn
    delay_range=(5, 10)  # Delay dài
)
# Ước tính: ~250 batch × 7.5s = ~31 phút
```

### Best practices:
1. Test với số lượng nhỏ trước (10-20 codes)
2. Monitor xem có bị captcha không
3. Điều chỉnh tham số phù hợp
4. Nếu vẫn bị chặn, cân nhắc dùng proxy

## Dấu hiệu bị chặn:
- Error message chứa "captcha"
- Response HTML chứa "verify you are human"
- Request bị timeout liên tục
- HTTP status 403 (Forbidden) hoặc 429 (Too Many Requests)

## Giải pháp nâng cao (nếu vẫn bị chặn):

### 1. Thêm Proxy Rotation
```python
# Cần implement thêm
proxies = [
    "http://proxy1:port",
    "http://proxy2:port",
    # ...
]
# Rotate proxy cho mỗi request
```

### 2. Session Management
```python
# Dùng cookies/session như browser thật
# Giữ session giữa các request
```

### 3. Residential Proxies
- Dùng service như: Bright Data, Oxylabs, SmartProxy
- Tốn phí nhưng hiệu quả cao

### 4. CAPTCHA Solving Service
- 2captcha.com, anti-captcha.com
- Tự động giải captcha nếu gặp

