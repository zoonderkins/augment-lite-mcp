#!/bin/bash
# Demo script for multi-project index management (v0.4.0)
# Includes BM25 + Vector index building

set -e

cd "$(dirname "$0")/.."

echo "========================================="
echo "Multi-Project Index Management Demo"
echo "v0.4.0 - BM25 + Vector Retrieval"
echo "========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}Step 1: Add MICE AI project${NC}"
echo "Command: python retrieval/multi_project.py add miceai /Users/lol/temp/rd00010-miceai"
echo ""
read -p "Press Enter to continue..."

python retrieval/multi_project.py add miceai /Users/lol/temp/rd00010-miceai

echo -e "\n${BLUE}Step 2: List all projects${NC}"
echo "Command: python retrieval/multi_project.py list"
echo ""
read -p "Press Enter to continue..."

python retrieval/multi_project.py list

echo -e "\n${BLUE}Step 3: Add another project (optional)${NC}"
echo "You can add more projects like:"
echo "  python retrieval/multi_project.py add myapp /path/to/myapp"
echo ""
echo "Skip this step for now."

echo -e "\n${BLUE}Step 4: Build vector index for the project${NC}"
echo "Command: python retrieval/build_vector_index.py miceai"
echo ""
echo "This will create FAISS vector index for semantic search."
echo ""
read -p "Press Enter to continue..."

python retrieval/build_vector_index.py miceai

echo -e "\n${BLUE}Step 5: Verify active project${NC}"
echo "The active project is marked with 🟢 ACTIVE"
echo ""
read -p "Press Enter to continue..."

python retrieval/multi_project.py list

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}Demo completed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start MCP server: python mcp_bridge_lazy.py"
echo "2. Use Claude Code CLI to search the indexed project"
echo "3. Switch projects with: python retrieval/multi_project.py activate <name>"
echo "4. Rebuild vector index: python retrieval/build_vector_index.py <name>"
echo ""
echo "For more information, see:"
echo "  - docs/MULTI_PROJECT.md"
echo "  - docs/guides/VECTOR_SEARCH.md"
echo "  - docs/v0.4.0_FEATURES.md"

