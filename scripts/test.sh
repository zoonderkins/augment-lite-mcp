#!/bin/bash
# 快速測試腳本
# 用法: ./scripts/test.sh [quick|unit|api|integration|all]

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 確保虛擬環境存在
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 虛擬環境不存在！${NC}"
    echo "請先運行: make venv && make install"
    exit 1
fi

# 激活虛擬環境
source .venv/bin/activate

# 預設測試類型
TEST_TYPE="${1:-quick}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    augment-lite-mcp 測試運行器                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

case "$TEST_TYPE" in
    quick)
        echo -e "${GREEN}🚀 快速測試模式（僅單元測試，約1分鐘）${NC}"
        echo ""
        python tests/run_all_tests.py --quick
        ;;

    unit)
        echo -e "${GREEN}🧪 運行單元測試${NC}"
        echo ""
        python tests/run_all_tests.py --suite unit
        ;;

    api)
        echo -e "${GREEN}🧪 運行 API 測試${NC}"
        echo ""
        python tests/run_all_tests.py --suite api
        ;;

    integration)
        echo -e "${GREEN}🧪 運行整合測試${NC}"
        echo ""
        python tests/run_all_tests.py --suite integration
        ;;

    all)
        echo -e "${GREEN}🧪 運行所有測試（約5-10分鐘）${NC}"
        echo ""
        python tests/run_all_tests.py --suite all
        ;;

    *)
        echo -e "${RED}❌ 未知的測試類型: $TEST_TYPE${NC}"
        echo ""
        echo "用法: $0 [quick|unit|api|integration|all]"
        echo ""
        echo "測試類型："
        echo "  quick        - 快速測試（僅單元測試，約1分鐘）"
        echo "  unit         - 單元測試（無需 API key）"
        echo "  api          - API 測試（需要數據庫和索引）"
        echo "  integration  - 整合測試（需要 Proxy 和索引）"
        echo "  all          - 運行所有測試（約5-10分鐘）"
        echo ""
        echo "範例："
        echo "  ./scripts/test.sh quick        # 快速測試"
        echo "  ./scripts/test.sh all          # 完整測試"
        echo "  make test-quick                # 使用 Makefile"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 測試通過！${NC}"
else
    echo -e "${RED}❌ 測試失敗！${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"

exit $EXIT_CODE
