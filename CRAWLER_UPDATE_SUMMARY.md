# Crawler Update Summary

## Changes Made

The crawler has been updated to properly parse and format the "Ngành nghề kinh doanh" (Industries) section based on the provided logic.

### Key Improvements

1. **HTML Splitting**: The HTML is now split by "Ngành nghề kinh doanh" text to separate the two tables:
   - Table 1: Company information (Thông tin doanh nghiệp)
   - Table 2: Industries (Ngành nghề kinh doanh)

2. **Industry Parsing**: The industries table is now parsed with the following structure:
   - `Mã ngành`: Industry code
   - `Ngành`: Industry name
   - `Chi tiết`: Details (if available)
   - `Đậm`: Boolean indicating if this is a main industry (marked with `<strong>` tag)

3. **Formatting**: Industries are formatted as a multi-line string with:
   - Main industries wrapped with `**` markers (markdown bold)
   - Format: `**Code - Name**` for main industries
   - Format: `Code - Name` for secondary industries
   - Optional details appended as: `| Chi tiết: {detail}`
   - Each industry on a new line

### Example Output

```
**4663 - Bán buôn máy móc, thiết bị và phụ tùng máy khác**
4669 - Bán buôn máy móc, thiết bị và phụ tùng máy khác | Chi tiết: Thương mại điện tử
7490 - Hoạt động chuyên môn, khoa học và công nghệ khác
```

### Functions Updated

Both crawler functions have been updated with the same logic:

1. `crawl_multiple_tax_codes_with_progress()` - Lines 95-220
2. `crawl_multiple_tax_codes()` - Lines 295-420

### Technical Details

- Uses `BeautifulSoup` with `html5lib` parser for robust HTML parsing
- Detects main industries by checking for `<strong>` tags in table rows
- Splits industry text by "Chi tiết:" to separate name from details
- Joins all industries with newline separator (`\n`)
- Preserves existing company information parsing

### Testing

A test script has been created at `test_crawler.py` to verify the changes work correctly with tax code `0318735609`.

## Usage

The crawler functions now return data with properly formatted industries:

```python
result = {
    "MST": "0318735609",
    "Tên": "Company Name",
    "Địa chỉ": "Address",
    ...
    "Ngành nghề kinh doanh": "**4663 - Main Industry**\n4669 - Secondary Industry | Chi tiết: Details"
}
```

The multi-line format makes it easy to:
- Display in web interfaces (split by `\n`)
- Export to CSV/Excel
- Parse back into structured data if needed

