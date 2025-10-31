"""
Example showing the new industry formatting in action
"""

# Before (old format):
old_format = {
    "MST": "0318735609",
    "Tên": "CÔNG TY CỔ PHẦN CÔNG NGHỆ VIỄN THÔNG SAAS",
    "Ngành nghề kinh doanh": "4663 - Bán buôn máy móc, thiết bị và phụ tùng máy khác..."
    # Single line, hard to distinguish main vs secondary industries
}

# After (new format):
new_format = {
    "MST": "0318735609",
    "Tên": "CÔNG TY CỔ PHẦN CÔNG NGHỆ VIỄN THÔNG SAAS",
    "Ngành nghề kinh doanh": """**4663 - Bán buôn máy móc, thiết bị và phụ tùng máy khác**
4669 - Bán buôn máy móc, thiết bị và phụ tùng máy khác | Chi tiết: Thương mại điện tử
7490 - Hoạt động chuyên môn, khoa học và công nghệ khác
**6201 - Lập trình máy tính**
6202 - Tư vấn máy tính và hoạt động quản lý vận hành máy tính"""
}

# How to use in your application:

# 1. Display in console
print("=== Ngành nghề kinh doanh ===")
print(new_format["Ngành nghề kinh doanh"])

# 2. Split into lines for HTML rendering
industries_lines = new_format["Ngành nghề kinh doanh"].split("\n")
for line in industries_lines:
    if line.startswith("**") and line.endswith("**"):
        # This is a main industry - render in bold
        clean_line = line.strip("*")
        print(f"<strong>{clean_line}</strong>")
    else:
        # Secondary industry - render normally
        print(f"<span>{line}</span>")

# 3. Parse back to structured data if needed
def parse_industries(industries_text):
    """Parse the formatted industries text back to structured data"""
    result = []
    for line in industries_text.split("\n"):
        is_main = line.startswith("**") and line.endswith("**")
        clean_line = line.strip("*")
        
        # Split code and name
        parts = clean_line.split(" - ", 1)
        if len(parts) < 2:
            continue
            
        code = parts[0]
        rest = parts[1]
        
        # Check for details
        if " | Chi tiết: " in rest:
            name, detail = rest.split(" | Chi tiết: ", 1)
        else:
            name = rest
            detail = ""
        
        result.append({
            "code": code,
            "name": name,
            "detail": detail,
            "is_main": is_main
        })
    
    return result

# Example usage
structured = parse_industries(new_format["Ngành nghề kinh doanh"])
print("\nStructured industries:")
for ind in structured:
    marker = "⭐" if ind["is_main"] else "  "
    print(f"{marker} [{ind['code']}] {ind['name']}")
    if ind["detail"]:
        print(f"    └─ Chi tiết: {ind['detail']}")

