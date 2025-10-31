# 🔍 Tax Information Crawler

Web application để tra cứu thông tin mã số thuế doanh nghiệp từ masothue.com

## ✨ Tính năng

- 🔢 Tra cứu thông tin mã số thuế đơn lẻ
- 📁 Upload file CSV để tra cứu hàng loạt mã số thuế
- 💾 Tải xuống kết quả dưới dạng file CSV
- 🎨 Giao diện web đẹp mắt, dễ sử dụng
- ⚡ Xử lý bất đồng bộ (async) để tối ưu hiệu suất
- 🛡️ **Chống phát hiện anti-bot**: Batch processing, random delays, browser fingerprint masking

## 📋 Thông tin thu thập

- Tên doanh nghiệp
- Mã số thuế
- Địa chỉ
- Tình trạng hoạt động
- Người đại diện pháp luật
- Số điện thoại
- Loại hình doanh nghiệp
- Ngày bắt đầu hoạt động
- Cơ quan quản lý thuế
- Ngành nghề kinh doanh

## 🚀 Cài đặt

### Yêu cầu
- Python 3.11+
- uv (recommended) hoặc pip

### Cài đặt dependencies

Sử dụng uv (khuyến nghị):
```bash
uv sync
```

Hoặc sử dụng pip:
```bash
pip install -e .
```

## 💻 Sử dụng

### 1. Chạy Web Server

```bash
# Cách 1: Sử dụng main.py
python main.py web

# Cách 2: Sử dụng uvicorn trực tiếp
uvicorn app:app --reload

# Cách 3: Sử dụng app.py
python app.py
```

Sau đó mở trình duyệt và truy cập: http://localhost:8000

### 2. Chạy CLI Example

```bash
python main.py
```

### 3. Sử dụng Web Interface

#### Tra cứu đơn lẻ:
1. Nhập mã số thuế vào ô input
2. Click "Tra cứu"
3. Xem kết quả hiển thị

#### Tra cứu hàng loạt từ CSV:
1. Chuẩn bị file CSV với cột đầu tiên chứa mã số thuế (xem `sample_tax_codes.csv`)
2. Click "Chọn file CSV" và chọn file
3. Click "Xử lý file CSV"
4. Đợi xử lý hoàn tất
5. Click "💾 Tải xuống CSV" để tải kết quả

## 📁 Cấu trúc dự án

```
tax-crawler/
├── app.py                      # FastAPI web application
├── crawler.py                  # Core crawler logic
├── main.py                     # Main entry point
├── templates/
│   └── index.html             # Web interface template
├── sample_tax_codes.csv       # Sample CSV file
├── pyproject.toml             # Project dependencies
└── README.md                  # This file
```

## 📝 Format file CSV

File CSV đầu vào cần có định dạng:

```csv
tax_code
0200837003
0100109106
0101326650
```

**⚠️ QUAN TRỌNG: Giữ số 0 ở đầu mã số thuế!**

- Cột đầu tiên chứa mã số thuế
- Header có thể là bất kỳ tên nào (tax_code, mst, etc.)
- **Phải giữ số 0 ở đầu** (ví dụ: `0200837003` không phải `200837003`)
- Khi dùng Excel, phải format cột là **Text** trước khi nhập liệu
- Xem hướng dẫn chi tiết trong file [CSV_GUIDE.md](CSV_GUIDE.md)

## 🔧 Cấu hình

### Tham số chống phát hiện

```python
# Trong crawler.py
await crawl_multiple_tax_codes(
    tax_codes,
    batch_size=3,        # Số lượng mã crawl đồng thời (mặc định: 3)
    delay_range=(2, 5)   # Delay ngẫu nhiên giữa các batch (giây)
)
```

**Tùy chỉnh theo nhu cầu:**
- `batch_size`: Giảm xuống 1-2 nếu bị chặn, tăng lên 5-10 nếu muốn nhanh hơn
- `delay_range`: Tăng lên (5, 10) nếu bị captcha, giảm xuống (1, 3) nếu muốn nhanh

📖 **Chi tiết**: Xem [ANTI_DETECTION.md](ANTI_DETECTION.md) để biết thêm về các kỹ thuật chống phát hiện

## 🛠️ Technology Stack

- **Backend**: FastAPI
- **Crawler**: crawl4ai
- **HTML Parser**: BeautifulSoup4 với html5lib
- **CSV Processing**: pandas
- **Template Engine**: Jinja2
- **ASGI Server**: uvicorn

## ⚠️ Lưu ý

- Crawler sử dụng dữ liệu công khai từ masothue.com
- Tốc độ crawl phụ thuộc vào tốc độ phản hồi của website
- Nên sử dụng với số lượng mã số thuế hợp lý để tránh quá tải
- Delay được đặt giữa các request để tránh bị block

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

