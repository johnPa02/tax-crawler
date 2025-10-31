#!/bin/bash
# Build and start the Tax Crawler application using Docker Compose

set -e

echo "🐳 Building Tax Crawler Docker image..."
docker-compose build

echo ""
echo "🚀 Starting Tax Crawler service..."
docker-compose up -d

echo ""
echo "⏳ Waiting for service to be ready..."
sleep 10

echo ""
echo "📊 Container status:"
docker-compose ps

echo ""
echo "✅ Tax Crawler is running!"
echo "🌐 Access the web interface at: http://localhost:8102"
echo ""
echo "📝 Useful commands:"
echo "  - View logs:     docker-compose logs -f"
echo "  - Stop service:  docker-compose stop"
echo "  - Restart:       docker-compose restart"
echo "  - Remove all:    docker-compose down"

