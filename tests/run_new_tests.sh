#!/bin/bash
# Run new tests created for Memory API and Auto Mode

set -e  # Exit on error

echo "========================================"
echo "Running New Test Suite"
echo "========================================"

# Change to project root
cd "$(dirname "$0")/.."

# Run Memory API tests
echo ""
echo "========================================" 
echo "1. Memory API Tests"
echo "========================================"
python tests/test_memory_api.py

# Run Auto Mode tests
echo ""
echo "========================================"
echo "2. Auto Mode Tests"
echo "========================================"
python tests/test_auto_mode.py

echo ""
echo "========================================"
echo "✅ All new tests completed!"
echo "========================================"
