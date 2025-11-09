#!/bin/bash
# Start augment-lite Web UI
# Usage: ./start.sh [port]

PORT=${1:-8080}

echo "🚀 Starting augment-lite Web UI on port $PORT"
echo "📊 Dashboard: http://localhost:$PORT"
echo "🔍 API Docs: http://localhost:$PORT/docs"
echo ""

cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
