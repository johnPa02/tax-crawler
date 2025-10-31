"""
Debug script to test crawler on AWS server
Run this on the AWS server to diagnose issues
"""
import asyncio
import sys
from crawler import crawl_tax_code

async def test_crawl():
    print("="*60)
    print("Testing crawler on AWS server")
    print("="*60)
    
    test_code = "0318735609"
    
    try:
        print(f"\nTesting with tax code: {test_code}")
        print("Starting crawl...")
        
        result = await crawl_tax_code(test_code)
        
        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        
        if "Error" in result:
            print(f"❌ ERROR: {result.get('Error')}")
            return False
        elif "Tên" in result:
            print(f"✓ SUCCESS!")
            print(f"  MST: {result.get('MST')}")
            print(f"  Tên: {result.get('Tên')}")
            print(f"  Địa chỉ: {result.get('Địa chỉ', 'N/A')}")
            return True
        else:
            print(f"⚠ PARTIAL: Got data but no company name")
            print(f"  Data: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_crawl())
    sys.exit(0 if success else 1)

