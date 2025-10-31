# 🛡️ Giải pháp chống bị chặn khi crawl - Tổng kết

## ✅ Đã implement thành công

### 1. **Batch Processing** ⚡
- Chia nhỏ requests thành các batch
- Mặc định: 3 codes/batch
- Tự động điều chỉnh: 2 codes/batch nếu >20 codes
- **Lợi ích**: Tránh overload server, giống người dùng thật hơn

### 2. **Random Delays** 🎲
- Delay ngẫu nhiên giữa các batch: 2-5 giây
- Delay trước khi lấy HTML: 1.5-3 giây
- **Lợi ích**: Tránh pattern đều đặn bị phát hiện

### 3. **Browser Fingerprint Masking** 🎭
```python
BrowserConfig(
    headless=True,
    extra_args=[
        "--disable-blink-features=AutomationControlled",  # Ẩn automation
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-web-security",
    ]
)
```
- **Lợi ích**: Ẩn dấu hiệu đây là bot/automation

### 4. **Intelligent Batching** 🧠
- Tự động giảm batch size nếu số lượng lớn
- Code trong `app.py`:
  ```python
  batch_size = 2 if len(tax_codes) > 20 else 3
  ```

## 📊 Performance

### Tốc độ crawl (ước tính):
- **10 codes**: ~15-20 giây
- **50 codes**: ~2-3 phút
- **100 codes**: ~5-7 phút
- **500 codes**: ~25-35 phút

### Trade-off:
| Batch Size | Speed | Safety | Use Case |
|------------|-------|--------|----------|
| 1 | 🐌 Slow | 🛡️ Very Safe | Bị chặn nhiều |
| 2 | 🚶 Medium | 🛡️ Safe | >20 codes |
| 3 | 🏃 Fast | ✅ Balanced | Default |
| 5+ | 🚀 Very Fast | ⚠️ Risky | Testing only |

## 🎯 Cách sử dụng

### Trong code Python:
```python
from crawler import crawl_multiple_tax_codes

# Mặc định (balanced)
results = await crawl_multiple_tax_codes(tax_codes)

# An toàn hơn (cho danh sách lớn)
results = await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=2,
    delay_range=(3, 7)
)

# Nhanh hơn (cho testing)
results = await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=5,
    delay_range=(1, 2)
)
```

### Qua Web Interface:
1. Upload CSV file
2. Hệ thống tự động:
   - Dùng batch_size=2 nếu >20 codes
   - Dùng batch_size=3 nếu ≤20 codes
3. Chờ kết quả và download CSV

## 🚨 Xử lý khi bị chặn

### Dấu hiệu bị chặn:
- ❌ Nhận captcha challenge
- ❌ HTTP 403/429 errors
- ❌ Timeout liên tục
- ❌ Response chứa "verify you are human"

### Giải pháp:
1. **Giảm batch_size xuống 1**
   ```python
   results = await crawl_multiple_tax_codes(tax_codes, batch_size=1)
   ```

2. **Tăng delay lên 5-10 giây**
   ```python
   results = await crawl_multiple_tax_codes(
       tax_codes, 
       batch_size=1, 
       delay_range=(5, 10)
   )
   ```

3. **Chờ một thời gian rồi thử lại** (15-30 phút)

4. **Sử dụng proxy** (nâng cao - cần implement thêm)

## 📈 Kết quả Test

### Test với 6 codes:
```
✓ Batch 1/2 (3 codes) → 3.7s delay
✓ Batch 2/2 (3 codes) → no delay
Total: ~8 seconds
Success rate: 66% (4/6 valid codes)
```

### Observation:
- ✅ Không bị captcha
- ✅ Tất cả valid codes đều crawl được
- ✅ Delay working correctly
- ✅ Batch processing stable

## 🔮 Tương lai / Nâng cao

Nếu vẫn bị chặn nhiều, có thể implement thêm:

1. **Proxy Rotation** 🔄
   - Dùng nhiều IP address
   - Rotate mỗi request hoặc mỗi batch

2. **Session Management** 🍪
   - Giữ cookies/session giữa requests
   - Simulate user session

3. **CAPTCHA Solver** 🤖
   - Tích hợp 2captcha, anti-captcha
   - Tự động solve captcha nếu gặp

4. **Distributed Crawling** 🌐
   - Crawl từ nhiều máy/server
   - Load balancing

## 📚 Tài liệu tham khảo

- [ANTI_DETECTION.md](ANTI_DETECTION.md) - Chi tiết kỹ thuật
- [README.md](README.md) - Hướng dẫn sử dụng
- [crawler.py](crawler.py) - Source code

## 💡 Tips

1. **Test nhỏ trước**: Luôn test với 5-10 codes trước khi chạy hàng trăm
2. **Monitor logs**: Xem console để biết progress và phát hiện vấn đề sớm
3. **Backup data**: Save kết quả thường xuyên (sau mỗi batch)
4. **Off-peak hours**: Crawl vào giờ thấp điểm (đêm khuya) sẽ ít bị chặn hơn
5. **Respect robots.txt**: Nếu có thể, check và respect rate limits

---
**Cập nhật**: 31/10/2025
**Status**: ✅ Hoạt động tốt, chưa gặp vấn đề captcha với default settings

