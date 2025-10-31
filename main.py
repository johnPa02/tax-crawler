"""
Tax Crawler - Main entry point
"""
import sys
from crawler import crawl_tax_code, crawl_multiple_tax_codes


def cli_example():
    """Example CLI usage"""
    print("=== Tax Crawler CLI Example ===\n")

    # Single tax code
    tax_code = '0200837003'
    print(f"Crawling tax code: {tax_code}")
    result = crawl_tax_code(tax_code)

    print("\n📋 Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    print("\n" + "="*50)
    print("To start the web server, run:")
    print("  python app.py")
    print("Or:")
    print("  uvicorn app:app --reload")
    print("="*50)


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # Start web server
        import uvicorn
        from app import app
        print("🚀 Starting web server at http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Run CLI example
        cli_example()


if __name__ == "__main__":
    main()
