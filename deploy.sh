#!/bin/bash

# Production deployment script for Tax Crawler

set -e  # Exit on error

echo "================================================"
echo "Tax Crawler - Production Deployment"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and docker-compose are installed${NC}"

# Stop existing containers
echo ""
echo "Stopping existing containers..."
docker-compose down

# Build images
echo ""
echo "Building Docker images..."
docker-compose build

# Start services
echo ""
echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

# Check Redis
if docker-compose ps redis | grep -q "Up"; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running${NC}"
fi

# Check App
if docker-compose ps app | grep -q "Up"; then
    echo -e "${GREEN}✓ App is running${NC}"
else
    echo -e "${RED}✗ App is not running${NC}"
    docker-compose logs app
    exit 1
fi

# Check Nginx (if enabled)
if docker-compose ps nginx | grep -q "Up" 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
fi

# Test endpoints
echo ""
echo "Testing endpoints..."

# Test main page
if curl -f -s http://localhost:8102/ > /dev/null; then
    echo -e "${GREEN}✓ Main page is accessible (http://localhost:8102/)${NC}"
else
    echo -e "${RED}✗ Main page is not accessible${NC}"
fi

# Test with nginx (if enabled)
if curl -f -s http://localhost/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx proxy is working (http://localhost/)${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo "================================================"
echo ""
echo "Services:"
echo "  - App: http://localhost:8102"
echo "  - Nginx: http://localhost (if enabled)"
echo ""
echo "Commands:"
echo "  - View logs: docker-compose logs -f app"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart"
echo "  - Status: docker-compose ps"
echo ""
echo "⚠️  IMPORTANT: Configure your reverse proxy (Nginx/Apache)"
echo "   to disable buffering for /progress/ endpoint!"
echo "   See nginx.conf for example configuration."
echo ""

