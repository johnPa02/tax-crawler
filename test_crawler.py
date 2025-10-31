"""
Test script for the tax crawler
"""
import json
import time
from crawler import fetch_tax_info, crawl_multiple_tax_codes

def test_single():
    """Test single tax code"""
    print("=== Test Single Tax Code ===")
    tax_code = "0318735609"
    result = fetch_tax_info(tax_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()

def test_multiple():
    """Test multiple tax codes"""
    print("=== Test Multiple Tax Codes ===")
    tax_codes = ["0318735609", "0200837003"]
    results = crawl_multiple_tax_codes(tax_codes, delay_range=(1, 2))
    
    for result in results:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()
    
    # Save to file
    with open("company_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("✅ Results saved to company_data.json")

if __name__ == "__main__":
    test_single()
    print("\n" + "="*60 + "\n")
    test_multiple()

