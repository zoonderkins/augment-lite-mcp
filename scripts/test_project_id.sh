#!/bin/bash
# 測試專案 ID 和 auto 模式功能

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}測試專案 ID 和 Auto 模式功能${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 取得腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo -e "${YELLOW}1. 測試列出專案（應顯示 ID 和當前專案標記）${NC}"
$PYTHON retrieval/multi_project.py list
echo ""

echo -e "${YELLOW}2. 測試 Python API - find_project_by_id_or_name${NC}"
$PYTHON -c "
from retrieval.multi_project import find_project_by_id_or_name, load_projects

projects = load_projects()
if projects:
    # Get first project
    first_name, first_config = list(projects.items())[0]
    project_id = first_config.get('id', 'N/A')

    print(f'測試查找專案名稱: {first_name}')
    result = find_project_by_id_or_name(first_name)
    if result:
        print(f'  ✅ 找到: {result[0]}')
    else:
        print(f'  ❌ 未找到')

    if project_id != 'N/A':
        print(f'測試查找專案 ID: {project_id}')
        result = find_project_by_id_or_name(project_id)
        if result:
            print(f'  ✅ 找到: {result[0]}')
        else:
            print(f'  ❌ 未找到')
else:
    print('⚠️  沒有專案可測試')
"
echo ""

echo -e "${YELLOW}3. 測試 Python API - resolve_project_name${NC}"
$PYTHON -c "
from retrieval.multi_project import resolve_project_name
import os
from pathlib import Path

# Test auto mode
cwd_name = Path(os.getcwd()).name
print(f'當前目錄: {cwd_name}')
result = resolve_project_name('auto')
print(f'resolve_project_name(\"auto\"): {result}')

# Test with project name
result = resolve_project_name('$PROJECT_ROOT')
print(f'resolve_project_name(專案路徑): {result}')
"
echo ""

echo -e "${YELLOW}4. 測試 utils/project_utils.py - is_project_registered${NC}"
$PYTHON -c "
from utils.project_utils import is_project_registered, load_projects

projects = load_projects()
if projects:
    first_name, first_config = list(projects.items())[0]
    project_id = first_config.get('id', 'N/A')

    # Test by name
    result = is_project_registered(first_name)
    print(f'is_project_registered(\"{first_name}\"): {result}')

    # Test by ID
    if project_id != 'N/A':
        result = is_project_registered(project_id)
        print(f'is_project_registered(\"{project_id}\"): {result}')

    # Test non-existent
    result = is_project_registered('non-existent-project-xyz')
    print(f'is_project_registered(\"non-existent\"): {result}')
else:
    print('⚠️  沒有專案可測試')
"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}測試完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "使用範例："
echo "  bash scripts/manage.sh list               # 列出所有專案（顯示 ID）"
echo "  bash scripts/manage.sh add auto .         # 新增當前目錄專案"
echo "  bash scripts/manage.sh activate auto      # 啟用當前目錄專案"
echo "  bash scripts/manage.sh activate <ID>      # 使用 ID 啟用專案"
echo "  bash scripts/manage.sh rebuild auto       # 重建當前目錄專案"
echo ""
