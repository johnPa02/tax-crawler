"""
Tax information crawler module
"""
import re
import random
import asyncio
from typing import Dict, List
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from bs4 import BeautifulSoup


async def crawl_tax_code(tax_code: str) -> Dict:
    """
    Crawl tax information for a given tax code
    
    Args:
        tax_code: The tax code to search for
        
    Returns:
        Dictionary containing tax information
    """
    # Use crawl_multiple_tax_codes for single tax code
    results = await crawl_multiple_tax_codes([tax_code])
    return results[0] if results else {"MST": tax_code}


async def crawl_multiple_tax_codes_with_progress(
    tax_codes: List[str],
    batch_size: int = 3,
    delay_range: tuple = (2, 5),
    progress_callback = None
) -> List[Dict]:
    """
    Crawl tax information with progress tracking

    Args:
        tax_codes: List of tax codes to search for
        batch_size: Number of URLs to crawl in parallel
        delay_range: Random delay range between batches
        progress_callback: Callback function(current, total, code, status)

    Returns:
        List of dictionaries containing tax information
    """
    # Browser configuration with anti-detection
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-web-security",
        ]
    )

    # Crawler configuration
    config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        wait_for="css:body",
        # delay_before_return_html should be set per request, not here
        stream=False,
        verbose=False,
        page_timeout=60000
    )

    # Build URLs for all tax codes
    urls = [f"https://masothue.com/Search/?type=auto&q={tax_code.strip()}" for tax_code in tax_codes]

    results = []
    completed = 0
    total = len(tax_codes)

    # Notify initialization start
    if progress_callback:
        progress_callback(0, total, '', 'Initializing browser...')

    # Process in batches
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Browser is now ready
        if progress_callback:
            progress_callback(0, total, '', 'Browser ready! Starting crawl...')

        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_tax_codes = tax_codes[i:i + batch_size]

            batch_num = i//batch_size + 1
            total_batches = (len(urls) + batch_size - 1)//batch_size

            if progress_callback:
                progress_callback(completed, total, batch_tax_codes[0], f"Processing batch {batch_num}/{total_batches}...")

            # Crawl batch (parallel)
            if progress_callback:
                progress_callback(completed, total, batch_tax_codes[0], f"Crawling batch {batch_num}/{total_batches} ({len(batch_urls)} codes)...")

            crawl_results = await crawler.arun_many(
                urls=batch_urls,
                config=config
            )

            # Process each result
            for idx, r in enumerate(crawl_results):
                tax_code = batch_tax_codes[idx].strip()
                completed += 1


                if not r.success:
                    print(f"✗ Error crawling {tax_code}: {r.error_message}")
                    results.append({"MST": tax_code, "Error": r.error_message})
                    continue

                try:
                    # Split HTML by "Ngành nghề kinh doanh" to separate two tables
                    html_parts = r.html.rsplit('Ngành nghề kinh doanh', 1)

                    if len(html_parts) < 2:
                        print(f"✗ Cannot split HTML for {tax_code}")
                        results.append({"MST": tax_code})
                        continue

                    html, html2 = html_parts

                    # Find both tables
                    match = re.search(r"<table.*?>.*?</table>", html, re.DOTALL | re.IGNORECASE)
                    match2 = re.search(r"<table.*?>.*?</table>", html2, re.DOTALL | re.IGNORECASE)

                    if not match:
                        print(f"✗ No company info table found for {tax_code}")
                        results.append({"MST": tax_code})
                        continue

                    table_html = match.group(0)

                    # ==== TABLE 1: Company Information ====
                    soup = BeautifulSoup(table_html, "html5lib")

                    # Remove ads
                    for tag in soup(["script", "style", "ins", "iframe", "div"]):
                        tag.decompose()

                    info = {"MST": tax_code}

                    # Get company name
                    name_tag = soup.select_one("th[colspan='2'] span.copy")
                    if name_tag:
                        info["Tên"] = name_tag.get_text(strip=True)

                    # Parse table rows
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

                            # Check if main industry (has <strong> tag)
                            is_main = bool(tr.find("strong"))
                            code = tds[0].get_text(strip=True)
                            raw_text = tds[1].get_text(" ", strip=True)

                            # Split by "Chi tiết:"
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

                    results.append(info)
                    print(f"✓ Crawled: {tax_code}")

                except Exception as e:
                    print(f"✗ Error processing {tax_code}: {e}")
                    results.append({"MST": tax_code, "Error": str(e)})

            # Update progress after batch completion
            if progress_callback:
                progress_callback(completed, total, '', f"Completed batch {batch_num}/{total_batches} - {completed}/{total} codes done")

            # Delay between batches
            if i + batch_size < len(urls):
                delay = random.uniform(*delay_range)
                if progress_callback:
                    progress_callback(completed, total, '', f"Waiting {delay:.1f}s before next batch...")
                print(f"Waiting {delay:.1f}s before next batch...")
                await asyncio.sleep(delay)

    return results


async def crawl_multiple_tax_codes(tax_codes: List[str], batch_size: int = 3, delay_range: tuple = (2, 5)) -> List[Dict]:
    """
    Crawl tax information for multiple tax codes in parallel with anti-detection measures

    Args:
        tax_codes: List of tax codes to search for
        batch_size: Number of URLs to crawl in parallel (smaller = safer, default 3)
        delay_range: Random delay range between batches in seconds (min, max)

    Returns:
        List of dictionaries containing tax information
    """
    # Browser configuration with anti-detection
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-web-security",
        ]
    )

    # Crawler configuration
    config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        wait_for="css:body",
        # delay_before_return_html=random.uniform(1.5, 3),  # Random delay
        stream=False,
        verbose=False,
        page_timeout=60000
    )

    # Build URLs for all tax codes
    urls = [f"https://masothue.com/Search/?type=auto&q={tax_code.strip()}" for tax_code in tax_codes]

    results = []

    # Process in batches to avoid rate limiting
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_tax_codes = tax_codes[i:i + batch_size]

            print(f"Processing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} ({len(batch_urls)} codes)...")

            # Crawl batch
            crawl_results = await crawler.arun_many(
                urls=batch_urls,
                config=config
            )

            # Add delay between batches (except last batch)
            if i + batch_size < len(urls):
                delay = random.uniform(*delay_range)
                print(f"Waiting {delay:.1f}s before next batch...")
                await asyncio.sleep(delay)

            # Process each result in the batch
            for idx, r in enumerate(crawl_results):
                tax_code = batch_tax_codes[idx].strip()

                if not r.success:
                    print(f"✗ Error crawling {tax_code}: {r.error_message}")
                    results.append({"MST": tax_code, "Error": r.error_message})
                    continue

                try:
                    # Split HTML by "Ngành nghề kinh doanh" to separate two tables
                    html_parts = r.html.rsplit('Ngành nghề kinh doanh', 1)

                    if len(html_parts) < 2:
                        print(f"✗ Cannot split HTML for {tax_code}")
                        results.append({"MST": tax_code})
                        continue

                    html, html2 = html_parts

                    # Find both tables
                    match = re.search(r"<table.*?>.*?</table>", html, re.DOTALL | re.IGNORECASE)
                    match2 = re.search(r"<table.*?>.*?</table>", html2, re.DOTALL | re.IGNORECASE)

                    if not match:
                        print(f"✗ No company info table found for {tax_code}")
                        results.append({"MST": tax_code})
                        continue

                    table_html = match.group(0)

                    # ==== TABLE 1: Company Information ====
                    soup = BeautifulSoup(table_html, "html5lib")

                    # Remove ads and junk
                    for tag in soup(["script", "style", "ins", "iframe", "div"]):
                        tag.decompose()

                    info = {"MST": tax_code}

                    # Get company name
                    name_tag = soup.select_one("th[colspan='2'] span.copy")
                    if name_tag:
                        info["Tên"] = name_tag.get_text(strip=True)

                    # Parse all <tr> rows in table
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
                            # Get first representative name only
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

                            # Check if main industry (has <strong> tag)
                            is_main = bool(tr.find("strong"))
                            code = tds[0].get_text(strip=True)
                            raw_text = tds[1].get_text(" ", strip=True)

                            # Split by "Chi tiết:"
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

                    results.append(info)
                    print(f"✓ Crawled: {tax_code}")

                except Exception as e:
                    print(f"✗ Error processing {tax_code}: {e}")
                    results.append({"MST": tax_code, "Error": str(e)})

    return results
