"""
Test script to verify the crawler works with the new industry parsing logic
"""
import asyncio
import json
from crawler import crawl_multiple_tax_codes


async def test_crawler():
    """Test the crawler with a sample tax code"""
    print("Testing crawler with tax code: 0318735609")
    print("=" * 60)
    
    tax_codes = ["0318735609"]
    results = await crawl_multiple_tax_codes(tax_codes, batch_size=1, delay_range=(1, 2))
    
    if results:
        result = results[0]
        print("\n✅ Crawl successful!")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Check if industries are formatted properly
        if "Ngành nghề kinh doanh" in result:
            print("\n" + "=" * 60)
            print("📋 Industries (formatted):")
            print("=" * 60)
            print(result["Ngành nghề kinh doanh"])
        
        # Save to file
        with open("test_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n" + "=" * 60)
        print("✅ Result saved to test_result.json")
    else:
        print("❌ Crawl failed - no results returned")


if __name__ == "__main__":
    asyncio.run(test_crawler())

