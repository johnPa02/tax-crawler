# 🚀 Quick Start - Anti-Detection Crawling

## TL;DR (Too Long, Didn't Read)

### Crawl nhỏ (<20 codes):
```python
results = await crawl_multiple_tax_codes(tax_codes)
```
✅ Nhanh, an toàn, không cần config gì thêm

### Crawl lớn (>100 codes):
```python
results = await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=2,      # Nhỏ hơn = an toàn hơn
    delay_range=(3, 7) # Delay dài hơn = ít bị chặn hơn
)
```
✅ Chậm nhưng an toàn

### Bị chặn rồi?
```python
results = await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=1,       # Từng cái một
    delay_range=(5, 10) # Chờ lâu giữa requests
)
```
✅ Rất chậm nhưng rất an toàn

## Cheat Sheet

| Scenario | batch_size | delay_range | Speed | Safety |
|----------|------------|-------------|-------|--------|
| Test (5-10 codes) | 3 | (1, 2) | ⚡⚡⚡ Fast | ✅ OK |
| Normal (<50 codes) | 3 | (2, 5) | ⚡⚡ Medium | ✅✅ Good |
| Large (100+ codes) | 2 | (3, 7) | ⚡ Slow | ✅✅✅ Safe |
| Very Large (500+) | 1-2 | (5, 10) | 🐌 Very Slow | 🛡️ Very Safe |
| Got Blocked | 1 | (10, 15) | 🐌🐌 Ultra Slow | 🛡️🛡️ Ultra Safe |

## Time Estimation

```
Ước tính thời gian ≈ (số_codes / batch_size) × delay_trung_bình

Ví dụ:
- 100 codes, batch=3, delay=3.5s → (100/3) × 3.5 ≈ 117s ≈ 2 phút
- 500 codes, batch=2, delay=7.5s → (500/2) × 7.5 ≈ 1875s ≈ 31 phút
```

## Code Examples

### Example 1: Quick test
```python
import asyncio
from crawler import crawl_multiple_tax_codes

tax_codes = ["0318735609", "5801554055", "0111265890"]

results = await crawl_multiple_tax_codes(tax_codes)
# → ~10 seconds
```

### Example 2: Production use
```python
# Read from CSV
import pandas as pd
df = pd.read_csv("tax_codes.csv", dtype=str)
tax_codes = df['dinh_danh_doanh_nghiep'].tolist()

# Crawl with safe settings
results = await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=2,
    delay_range=(3, 6)
)

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv("results.csv", index=False, encoding='utf-8-sig')
```

### Example 3: Handle errors
```python
results = await crawl_multiple_tax_codes(tax_codes)

# Check results
success_count = sum(1 for r in results if 'Tên' in r)
error_count = len(results) - success_count

print(f"Success: {success_count}/{len(results)}")
print(f"Errors: {error_count}")

# Get failed codes
failed_codes = [r['MST'] for r in results if 'Tên' not in r]
if failed_codes:
    print(f"Failed codes: {failed_codes}")
    # Retry with safer settings
    retry_results = await crawl_multiple_tax_codes(
        failed_codes,
        batch_size=1,
        delay_range=(5, 10)
    )
```

## Web Interface

1. Go to http://localhost:8000
2. Upload CSV with column `dinh_danh_doanh_nghiep`
3. Click "Xử lý file CSV"
4. Wait (check console for progress)
5. Download results

**Auto settings:**
- ≤20 codes → batch_size=3 (fast)
- >20 codes → batch_size=2 (safer)

## Troubleshooting

### ❌ Getting captcha
→ Giảm batch_size và tăng delay

### ❌ Timeout errors
→ Kiểm tra internet, thử lại sau

### ❌ No data returned
→ Check mã số thuế có đúng không

### ❌ Process too slow
→ Tăng batch_size (nhưng rủi ro cao hơn)

## Best Practices

✅ **DO:**
- Test nhỏ trước (5-10 codes)
- Monitor console logs
- Save results incrementally
- Crawl off-peak hours (night time)
- Use default settings first

❌ **DON'T:**
- Crawl batch_size > 5
- Set delay < 1 second
- Crawl thousands without testing
- Ignore error messages
- Retry immediately after blocking

## Need Help?

1. Check [ANTI_DETECTION.md](ANTI_DETECTION.md) for details
2. Check [ANTI_DETECTION_SUMMARY.md](ANTI_DETECTION_SUMMARY.md) for summary
3. Check console logs for errors
4. Try safer settings (batch_size=1, longer delays)

---
**Last updated**: 31/10/2025

