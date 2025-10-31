"""
Tax information crawler module
"""
import re
import time
import requests
from typing import Dict, List
from bs4 import BeautifulSoup


def crawl_tax_code(tax_code: str) -> Dict:
    """
    Crawl tax information for a given tax code
    
    Args:
        tax_code: The tax code to search for
        
    Returns:
        Dictionary containing tax information
    """
    # Use crawl_multiple_tax_codes for single tax code
    results = crawl_multiple_tax_codes([tax_code])
    return results[0] if results else {"MST": tax_code}


def fetch_tax_info(tax_code: str) -> Dict:
    """
    Fetch tax information for a single tax code using requests

    Args:
        tax_code: The tax code to search for

    Returns:
        Dictionary containing tax information
    """
    url = f"https://masothue.com/Search/?type=auto&q={tax_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Referer": "https://masothue.com/",
        "Accept-Language": "vi,en;q=0.9"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = "utf-8"
        html = r.text

        # Split HTML by "Ngành nghề kinh doanh" to separate two tables
        html_parts = html.rsplit('Ngành nghề kinh doanh', 1)

        if len(html_parts) < 2:
            print(f"✗ Cannot split HTML for {tax_code}")
            return {"MST": tax_code}

        html, html2 = html_parts
        match = re.search(r"<table.*?>.*?</table>", html, re.DOTALL | re.IGNORECASE)
        match2 = re.search(r"<table.*?>.*?</table>", html2, re.DOTALL | re.IGNORECASE)

        if not match:
            print(f"✗ No company info table found for {tax_code}")
            return {"MST": tax_code}

        table_html = match.group(0)

        # ==== TABLE 1: Company Information ====
        soup = BeautifulSoup(table_html, "html5lib")

        # Remove junk tags
        for tag in soup(["script", "style", "ins", "iframe", "div"]):
            tag.decompose()

        info = {}

        # Get company name
        name_tag = soup.select_one("th[colspan='2'] span.copy")
        if name_tag:
            info["Tên"] = name_tag.get_text(strip=True)

        # Parse all table rows
        for tr in soup.select("table.table-taxinfo tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            key = tds[0].get_text(strip=True)
            val = tds[1].get_text(" ", strip=True)

            if "Mã số thuế" in key:
                info["MST"] = val
            elif "Địa chỉ Thuế" in key:
                info["Địa chỉ thuế"] = val
            elif re.fullmatch(r"Địa chỉ", key):
                info["Địa chỉ"] = val
            elif "Tình trạng" in key:
                info["Tình trạng"] = val
            elif "Người đại diện" in key:
                rep = tds[1].find("span", {"itemprop": "name"})
                info["Người đại diện"] = rep.get_text(strip=True) if rep else val
            elif "Điện thoại" in key:
                info["Điện thoại"] = val.split("Ẩn")[0].strip()
            elif "Ngày hoạt động" in key:
                info["Ngày hoạt động"] = val
            elif "Quản lý bởi" in key:
                info["Quản lý bởi"] = val
            elif "Loại hình DN" in key:
                info["Loại hình DN"] = val

        # ==== TABLE 2: Industries (Ngành nghề kinh doanh) ====
        if match2:
            table_html2 = match2.group(0)
            soup2 = BeautifulSoup(table_html2, "html5lib")
            industries = []

            for tr in soup2.select("tbody tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                is_main = bool(tr.find("strong"))
                code = tds[0].get_text(strip=True)
                raw_text = tds[1].get_text(" ", strip=True)
                parts = raw_text.split("Chi tiết:", 1)
                name = parts[0].strip()
                detail = parts[1].strip() if len(parts) > 1 else ""
                industries.append({
                    "Mã ngành": code,
                    "Ngành": name,
                    "Chi tiết": detail,
                    "Đậm": is_main
                })

            # Format industries as multi-line string with bold markers
            formatted_industries = []
            for ind in industries:
                prefix = "**" if ind["Đậm"] else ""
                suffix = "**" if ind["Đậm"] else ""
                line = f"{prefix}{ind['Mã ngành']} - {ind['Ngành']}{suffix}"
                if ind["Chi tiết"]:
                    line += f" | Chi tiết: {ind['Chi tiết']}"
                formatted_industries.append(line)

            # Join with newlines
            info["Ngành nghề kinh doanh"] = "\n".join(formatted_industries)

        print(f"✓ Crawled: {tax_code}")
        return info

    except Exception as e:
        print(f"✗ Error crawling {tax_code}: {e}")
        return {"MST": tax_code, "Error": str(e)}


def crawl_multiple_tax_codes_with_progress(
    tax_codes: List[str],
    batch_size: int = 3,
    delay_range: tuple = (2, 5),
    progress_callback = None
) -> List[Dict]:
    """
    Crawl tax information with progress tracking

    Args:
        tax_codes: List of tax codes to search for
        batch_size: Not used in synchronous version (kept for compatibility)
        delay_range: Delay range between requests in seconds
        progress_callback: Callback function(current, total, code, status)

    Returns:
        List of dictionaries containing tax information
    """
    results = []
    total = len(tax_codes)

    # Notify initialization start
    if progress_callback:
        progress_callback(0, total, '', 'Starting crawl...')

    for idx, tax_code in enumerate(tax_codes):
        tax_code = tax_code.strip()

        if progress_callback:
            progress_callback(idx, total, tax_code, f"Crawling {tax_code}...")

        info = fetch_tax_info(tax_code)
        results.append(info)

        if progress_callback:
            progress_callback(idx + 1, total, tax_code, f"Completed {idx + 1}/{total}")

        # Delay between requests (except last one)
        if idx < total - 1:
            import random
            delay = random.uniform(*delay_range)
            if progress_callback:
                progress_callback(idx + 1, total, '', f"Waiting {delay:.1f}s before next request...")
            print(f"Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

    return results


def crawl_multiple_tax_codes(tax_codes: List[str], batch_size: int = 3, delay_range: tuple = (2, 5)) -> List[Dict]:
    """
    Crawl tax information for multiple tax codes sequentially

    Args:
        tax_codes: List of tax codes to search for
        batch_size: Not used in synchronous version (kept for compatibility)
        delay_range: Delay range between requests in seconds (min, max)

    Returns:
        List of dictionaries containing tax information
    """
    import random
    results = []

    for idx, code in enumerate(tax_codes):
        info = fetch_tax_info(code.strip())
        if info:
            results.append(info)

        # Delay between requests (except last one)
        if idx < len(tax_codes) - 1:
            delay = random.uniform(*delay_range)
            print(f"Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

    return results
