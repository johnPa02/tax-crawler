#!/bin/bash

# Quick test script for AWS deployment
# Tests if the crawler is working inside Docker container

echo "================================================"
echo "Testing Tax Crawler on AWS"
echo "================================================"

# Test 1: Check if service is up
echo ""
echo "[1] Checking if service is accessible..."
if curl -f -s http://localhost:8102/ > /dev/null; then
    echo "✓ Service is UP"
else
    echo "✗ Service is DOWN"
    exit 1
fi

# Test 2: Check health endpoint
echo ""
echo "[2] Checking health endpoint..."
curl -s http://localhost:8102/health | python3 -m json.tool

# Test 3: Test actual crawl inside Docker container
echo ""
echo "[3] Testing crawl inside Docker container..."
docker exec tax-crawler-app python3 -c "
import asyncio
from crawler import crawl_tax_code

async def test():
    print('Testing crawl_tax_code...')
    try:
        result = await crawl_tax_code('0318735609')
        if 'Tên' in result:
            print(f'✓ SUCCESS: {result[\"Tên\"]}')
            return True
        elif 'Error' in result:
            print(f'✗ ERROR: {result[\"Error\"]}')
            return False
        else:
            print(f'⚠ PARTIAL: {result}')
            return False
    except Exception as e:
        print(f'✗ EXCEPTION: {e}')
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(test())
exit(0 if success else 1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Crawl test PASSED"
else
    echo ""
    echo "✗ Crawl test FAILED"
    echo ""
    echo "Checking container logs..."
    docker logs tax-crawler-app --tail 50
fi

echo ""
echo "================================================"
echo "Test Complete"
echo "================================================"

