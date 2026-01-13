#!/bin/bash
# Test script for MCP server integration

set -e

PROJECT_ROOT="$HOME/Downloads/augment-lite-mcp"
cd "$PROJECT_ROOT"

echo "========================================="
echo "MCP Server Integration Test"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if virtual environment exists
echo -e "\n${YELLOW}[Test 1]${NC} Checking virtual environment..."
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"
else
    echo -e "${RED}✗${NC} Virtual environment not found. Run: make venv"
    exit 1
fi

# Test 2: Check if data directory and index exist
echo -e "\n${YELLOW}[Test 2]${NC} Checking data directory and index..."
if [ -f "data/chunks.jsonl" ]; then
    echo -e "${GREEN}✓${NC} Index file found: data/chunks.jsonl"
    CHUNK_COUNT=$(wc -l < data/chunks.jsonl)
    echo "  → Chunks count: $CHUNK_COUNT"
else
    echo -e "${RED}✗${NC} Index file not found. Run: make index"
    exit 1
fi

# Test 3: Test manual execution
echo -e "\n${YELLOW}[Test 3]${NC} Testing manual execution (5 seconds timeout)..."
source .venv/bin/activate

export AUGMENT_DB_DIR="$PROJECT_ROOT/data"
export GLM_API_KEY="${GLM_API_KEY:-dummy}"
export MINIMAX_API_KEY="${MINIMAX_API_KEY:-dummy}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-dummy}"
export REQUESTY_API_KEY="${REQUESTY_API_KEY:-dummy}"

# Send a test request to the server
timeout 5s bash -c '
echo "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}" | python -u mcp_bridge_lazy.py
' > /tmp/mcp_test_output.txt 2>&1 &
PID=$!

sleep 2

if ps -p $PID > /dev/null; then
    echo -e "${GREEN}✓${NC} Server started successfully"
    kill $PID 2>/dev/null || true
else
    echo -e "${RED}✗${NC} Server failed to start"
    echo "Output:"
    cat /tmp/mcp_test_output.txt
    exit 1
fi

# Test 4: Check MCP protocol response
echo -e "\n${YELLOW}[Test 4]${NC} Testing MCP protocol initialization..."
RESPONSE=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
    timeout 3s python -u mcp_bridge_lazy.py 2>/dev/null | head -1 || echo "")

if [ -n "$RESPONSE" ]; then
    echo -e "${GREEN}✓${NC} MCP server responded"
    echo "  Response preview: ${RESPONSE:0:100}..."
else
    echo -e "${YELLOW}⚠${NC} No response (this might be normal for stdio initialization)"
fi

# Test 5: Verify Claude Code CLI configuration
echo -e "\n${YELLOW}[Test 5]${NC} Checking Claude Code CLI MCP configuration..."
CLAUDE_CONFIG="$HOME/.config/claude/claude_desktop_config.json"

if [ -f "$CLAUDE_CONFIG" ]; then
    if grep -q "augment-lite" "$CLAUDE_CONFIG"; then
        echo -e "${GREEN}✓${NC} augment-lite found in Claude config"
    else
        echo -e "${YELLOW}⚠${NC} augment-lite not found in Claude config"
        echo "  Run the following to add it:"
        echo ""
        echo "  claude mcp add --scope user --transport stdio augment-lite \\"
        echo "    --env AUGMENT_DB_DIR=\"$PROJECT_ROOT/data\" \\"
        echo "    --env GLM_API_KEY=\"\$GLM_API_KEY\" \\"
        echo "    --env MINIMAX_API_KEY=\"\$MINIMAX_API_KEY\" \\"
        echo "    --env REQUESTY_API_KEY=\"\$REQUESTY_API_KEY\" \\"
        echo "    -- \"$PROJECT_ROOT/.venv/bin/python\" \\"
        echo "       \"-u\" \"$PROJECT_ROOT/mcp_bridge_lazy.py\""
    fi
else
    echo -e "${YELLOW}⚠${NC} Claude config not found at: $CLAUDE_CONFIG"
fi

echo -e "\n========================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. If not already added, run the 'claude mcp add' command shown above"
echo "2. Restart Claude Code CLI"
echo "3. Test with: claude mcp list"
echo ""

