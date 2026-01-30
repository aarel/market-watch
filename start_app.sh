#!/bin/bash

# Market-Watch Application Startup Script

echo "🚀 Starting Market-Watch Trading Bot..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your Alpaca credentials"
    exit 1
fi

# Check dependencies
if ! pip show fastapi > /dev/null 2>&1; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Display current configuration
echo "📊 Current Configuration:"
echo "  TRADING_MODE: $(grep TRADING_MODE .env | cut -d'=' -f2)"
echo "  AUTO_TRADE: $(grep AUTO_TRADE .env | cut -d'=' -f2)"
echo ""

# Start the application
echo "🎯 Starting FastAPI server..."
echo "   Web UI: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""

uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
