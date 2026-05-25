"""
Tax information crawler module
"""
import re
import time
import random
import requests
from typing import Dict, List
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"
]

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
    Fetch tax information for a single tax code using requests, with enterpriseTax fallback.
    
    Args:
        tax_code: The tax code to search for
        
    Returns:
        Dictionary containing tax information
    """
    def parse_company_html(html_text: str) -> dict:
        table_matches = re.findall(r"<table.*?>.*?</table>", html_text, re.DOTALL | re.IGNORECASE)
        if not table_matches:
            return None

        # First table is company info (required)
        table_html = table_matches[0]
        # Second table is industries (optional)
        table_html2 = table_matches[1] if len(table_matches) > 1 else None

        # ==== TABLE 1: Company Information ====
        soup_table = BeautifulSoup(table_html, "html5lib")

        # Remove junk tags
        for tag in soup_table(["script", "style", "ins", "iframe", "div"]):
            tag.decompose()

        info_dict = {}

        # Get company name
        name_tag = soup_table.select_one("th[colspan='2'] span.copy")
        if name_tag:
            info_dict["Tên"] = name_tag.get_text(strip=True)

        # Parse all table rows
        for tr in soup_table.select("table.table-taxinfo tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            key = tds[0].get_text(strip=True)
            val = tds[1].get_text(" ", strip=True)

            if "Mã số thuế" in key:
                info_dict["MST"] = val
            elif "Địa chỉ Thuế" in key:
                info_dict["Địa chỉ thuế"] = val
            elif re.fullmatch(r"Địa chỉ", key):
                info_dict["Địa chỉ"] = val
            elif "Tình trạng" in key:
                info_dict["Tình trạng"] = val
            elif "Người đại diện" in key:
                rep = tds[1].find("span", {"itemprop": "name"})
                info_dict["Người đại diện"] = rep.get_text(strip=True) if rep else val
            elif "Điện thoại" in key:
                info_dict["Điện thoại"] = val.split("Ẩn")[0].strip()
            elif "Ngày hoạt động" in key:
                info_dict["Ngày hoạt động"] = val
            elif "Quản lý bởi" in key:
                info_dict["Quản lý bởi"] = val
            elif "Loại hình DN" in key:
                info_dict["Loại hình DN"] = val

        # ==== TABLE 2: Industries (Ngành nghề kinh doanh) ====
        if table_html2:
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

            formatted_industries = []
            for ind in industries:
                prefix = "**" if ind["Đậm"] else ""
                suffix = "**" if ind["Đậm"] else ""
                line = f"{prefix}{ind['Mã ngành']} - {ind['Ngành']}{suffix}"
                if ind["Chi tiết"]:
                    line += f" | Chi tiết: {ind['Chi tiết']}"
                formatted_industries.append(line)

            info_dict["Ngành nghề kinh doanh"] = "\n".join(formatted_industries)
            
        return info_dict

    url = f"https://masothue.com/Search/?type=enterprise&q={tax_code}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://masothue.com/",
        "Accept-Language": "vi,en;q=0.9,en-US;q=0.8"
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = "utf-8"
        html = r.text

        # Check for captcha
        if r.status_code == 403 or "Check bot" in html:
            print(f"✗ Captcha blocked for {tax_code}")
            return {"MST": tax_code, "Error": "Bị chặn bởi captcha. Vui lòng giải captcha tại masothue.com rồi thử lại."}

        info = parse_company_html(html)
        returned_mst = info.get("MST", "") if info else ""

        # FALLBACK: If no info found or MST mismatched (due to random bot redirect)
        if not info or (returned_mst and returned_mst != tax_code):
            print(f"⚠ Mismatch or no data for {tax_code} (got '{returned_mst}'). Fallback to enterpriseTax...")
            
            fallback_url = f"https://masothue.com/Search/?type=enterpriseTax&q={tax_code}"
            r_fb = requests.get(fallback_url, headers=headers, timeout=15)
            r_fb.encoding = "utf-8"
            soup_fb = BeautifulSoup(r_fb.text, "html5lib")
            
            target_slug = None
            # Find the exact match
            for a in soup_fb.select(".tax-listing h3 a"):
                slug = a.get("href")
                parent_div = a.find_parent("div")
                if parent_div:
                    hashtag_a = parent_div.find("a", href=slug)
                    if hashtag_a and hashtag_a.text.strip() == tax_code:
                        target_slug = slug
                        break
            
            # If no exact match, take the first link
            if not target_slug:
                first_link = soup_fb.select_one(".tax-listing h3 a")
                if first_link:
                    target_slug = first_link.get("href")
                    
            if target_slug:
                slug_url = f"https://masothue.com{target_slug}"
                r_slug = requests.get(slug_url, headers=headers, timeout=15)
                r_slug.encoding = "utf-8"
                info = parse_company_html(r_slug.text)

        if not info:
            print(f"✗ No tables found for {tax_code} even after fallback")
            return {"MST": tax_code, "Error": "Không tìm thấy dữ liệu công ty."}

        # Final verification
        returned_mst = info.get("MST", "")
        # Allow branch match (e.g., 0100109106-097 when requested 0100109106)
        if returned_mst and returned_mst != tax_code and not returned_mst.startswith(f"{tax_code}-"):
            print(f"⚠ MST mismatch after fallback: requested {tax_code} but got {returned_mst}")
            return {"MST": tax_code, "Error": f"MST không khớp. Yêu cầu {tax_code} nhưng nhận được {returned_mst}."}

        print(f"✓ Crawled: {tax_code} -> {info.get('Tên', 'N/A')}")
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
