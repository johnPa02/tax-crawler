#!/bin/bash
# Start the web server

echo "🚀 Starting Tax Information Crawler..."
echo ""

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Using uv to run the application..."
    uv run python main.py web
else
    echo "Using python to run the application..."
    python main.py web
fi

