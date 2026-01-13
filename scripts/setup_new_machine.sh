#!/bin/bash
# 在新電腦上設置 augment-lite-mcp
# 用途：自動安裝依賴、配置環境、遷移專案

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 取得腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ============================================================
# 工具函數
# ============================================================

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================
# 檢查系統需求
# ============================================================

check_requirements() {
    print_header "檢查系統需求"
    echo ""
    
    local all_ok=true
    
    # 檢查 Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python: $python_version"
    else
        print_error "Python 3 未安裝"
        all_ok=false
    fi
    
    # 檢查 pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3: 已安裝"
    else
        print_error "pip3 未安裝"
        all_ok=false
    fi
    
    # 檢查 git
    if command -v git &> /dev/null; then
        print_success "git: 已安裝"
    else
        print_warning "git: 未安裝（可選）"
    fi
    
    # 檢查 nc (netcat)
    if command -v nc &> /dev/null; then
        print_success "nc (netcat): 已安裝"
    else
        print_warning "nc (netcat): 未安裝（用於檢查 proxy 狀態）"
    fi
    
    echo ""
    
    if [ "$all_ok" = false ]; then
        print_error "缺少必要的系統需求，請先安裝"
        exit 1
    fi
    
    print_success "系統需求檢查通過"
    echo ""
}

# ============================================================
# 安裝依賴
# ============================================================

install_dependencies() {
    print_header "安裝依賴"
    echo ""
    
    # 創建虛擬環境
    if [ ! -d ".venv" ]; then
        print_info "創建 Python 虛擬環境..."
        python3 -m venv .venv
        print_success "虛擬環境已創建"
    else
        print_info "虛擬環境已存在"
    fi
    
    # 啟動虛擬環境
    source .venv/bin/activate
    
    # 升級 pip
    print_info "升級 pip..."
    uv pip install --upgrade pip > /dev/null 2>&1

    # 安裝依賴
    if [ -f "requirements.txt" ]; then
        print_info "安裝依賴套件..."
        uv pip install -r requirements.txt
        print_success "依賴套件已安裝"
    else
        print_warning "requirements.txt 不存在，跳過安裝"
    fi
    
    echo ""
}

# ============================================================
# 配置環境變數
# ============================================================

configure_env() {
    print_header "配置環境變數"
    echo ""
    
    if [ -f ".env" ]; then
        print_info ".env 檔案已存在"
        read -p "是否要重新配置？[y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    # 複製範例檔案
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "已複製 .env.example 到 .env"
    else
        touch .env
        print_info "已創建空的 .env 檔案"
    fi
    
    echo ""
    print_info "請編輯 .env 檔案設置以下環境變數："
    echo "  - AUGMENT_DB_DIR (資料目錄路徑)"
    echo "  - GLM_BASE_URL / GLM_API_KEY (GLM endpoint 和 key)"
    echo "  - MINIMAX_BASE_URL / MINIMAX_API_KEY (MiniMax endpoint 和 key)"
    echo "  - REQUESTY_API_KEY (Requesty API Key)"
    echo ""
    
    read -p "是否現在編輯 .env？[y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
    
    echo ""
}

# ============================================================
# 遷移資料
# ============================================================

migrate_data() {
    print_header "遷移資料"
    echo ""
    
    print_info "如果你有舊電腦的資料備份，可以在這裡恢復"
    echo ""
    
    read -p "是否有資料備份需要恢復？[y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "跳過資料遷移"
        echo ""
        return
    fi
    
    read -p "請輸入備份目錄路徑: " backup_path
    
    if [ ! -d "$backup_path" ]; then
        print_error "備份目錄不存在: $backup_path"
        return
    fi
    
    # 恢復 data 目錄
    if [ -d "$backup_path/data" ]; then
        print_info "恢復 data/ 目錄..."
        mkdir -p data

        # 恢復專案配置和記憶
        [ -f "$backup_path/data/projects.json" ] && cp "$backup_path/data/projects.json" data/
        [ -f "$backup_path/data/memory.sqlite" ] && cp "$backup_path/data/memory.sqlite" data/
        [ -f "$backup_path/data/response_cache.sqlite" ] && cp "$backup_path/data/response_cache.sqlite" data/

        # 恢復向量索引（如果有）
        if ls "$backup_path/data/vector_index"*.faiss 1> /dev/null 2>&1; then
            print_info "恢復向量索引..."
            cp "$backup_path/data/vector_index"*.faiss data/ 2>/dev/null || true
            cp "$backup_path/data/vector_chunks"*.pkl data/ 2>/dev/null || true
            print_success "向量索引已恢復"
        fi

        # 恢復語義快取（如果有）
        if ls "$backup_path/data/semantic_cache"*.faiss 1> /dev/null 2>&1; then
            print_info "恢復語義快取..."
            cp "$backup_path/data/semantic_cache"*.faiss data/ 2>/dev/null || true
            cp "$backup_path/data/semantic_cache_entries"*.pkl data/ 2>/dev/null || true
            print_success "語義快取已恢復"
        fi

        print_success "data/ 目錄已恢復"
    fi

    # 恢復配置
    if [ -f "$backup_path/config/models.yaml" ]; then
        print_info "恢復 config/models.yaml..."
        mkdir -p config
        cp "$backup_path/config/models.yaml" config/
        print_success "config/models.yaml 已恢復"
    fi

    echo ""
    print_success "資料遷移完成"

    # 提示是否需要重建索引
    if [ ! -f "data/vector_index_"*.faiss ]; then
        echo ""
        print_warning "沒有檢測到向量索引，建議重建"
        echo "執行: python retrieval/build_vector_index.py"
    fi

    echo ""
}

# ============================================================
# 更新專案路徑
# ============================================================

update_project_paths() {
    print_header "更新專案路徑"
    echo ""
    
    if [ ! -f "data/projects.json" ]; then
        print_info "沒有專案配置，跳過"
        echo ""
        return
    fi
    
    print_info "檢測到專案配置檔案"
    echo ""
    
    # 顯示現有專案
    .venv/bin/python retrieval/multi_project.py list
    
    echo ""
    print_warning "專案路徑可能需要更新（因為在新電腦上路徑不同）"
    echo ""
    
    read -p "是否要更新專案路徑？[y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "跳過路徑更新"
        echo ""
        return
    fi
    
    # 讀取專案列表
    local projects=$(.venv/bin/python -c "
import json
from pathlib import Path
config_path = Path('data/projects.json')
if config_path.exists():
    projects = json.load(open(config_path))
    for name in projects.keys():
        print(name)
")
    
    # 逐個更新專案路徑
    for project in $projects; do
        echo ""
        print_info "專案: $project"
        read -p "請輸入新的專案路徑（留空跳過）: " new_path
        
        if [ -n "$new_path" ]; then
            .venv/bin/python retrieval/multi_project.py add "$project" "$new_path"
        fi
    done
    
    echo ""
    print_success "專案路徑更新完成"
    echo ""
}

# ============================================================
# 執行資料庫遷移
# ============================================================

run_migrations() {
    print_header "執行資料庫遷移"
    echo ""
    
    if [ ! -f "data/memory.sqlite" ] && [ ! -f "data/response_cache.sqlite" ]; then
        print_info "沒有需要遷移的資料庫"
        echo ""
        return
    fi
    
    print_info "檢測到舊版資料庫，需要執行遷移"
    echo ""
    
    read -p "是否執行資料庫遷移？[y/N] " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        .venv/bin/python scripts/migrate_all.py
    else
        print_info "跳過資料庫遷移"
    fi
    
    echo ""
}

# ============================================================
# 檢查本地 Proxy
# ============================================================

check_local_proxy() {
    print_header "檢查本地 Proxy"
    echo ""
    
    print_info "檢查本地 Proxy 服務狀態..."
    echo ""
    
    bash scripts/manage.sh check-proxy
    
    echo ""
    print_info "如果本地 Proxy 未運行，請先啟動它們"
    echo "或修改 config/models.yaml 使用 Requesty 服務"
    echo ""
}

# ============================================================
# 測試配置
# ============================================================

test_configuration() {
    print_header "測試配置"
    echo ""
    
    print_info "測試動態 max_output_tokens 配置..."
    .venv/bin/python scripts/test_dynamic_max_tokens.py
    
    echo ""
}

# ============================================================
# 顯示下一步
# ============================================================

show_next_steps() {
    print_header "設置完成！"
    echo ""
    
    print_success "augment-lite-mcp 已在新電腦上設置完成"
    echo ""
    
    print_info "下一步："
    echo ""
    echo "1. 配置 Claude Code CLI："
    echo "   claude mcp add --scope user --transport stdio augment-lite \\"
    echo "     --env AUGMENT_DB_DIR=\"$PROJECT_ROOT/data\" \\"
    echo "     --env GLM_API_KEY=\"your-glm-key\" \\"
    echo "     --env MINIMAX_API_KEY=\"your-minimax-key\" \\"
    echo "     --env REQUESTY_API_KEY=\"your-api-key\" \\"
    echo "     -- \"$PROJECT_ROOT/.venv/bin/python\" \\"
    echo "        \"-u\" \"$PROJECT_ROOT/mcp_bridge_lazy.py\""
    echo ""
    echo "2. 管理專案："
    echo "   bash scripts/manage.sh"
    echo ""
    echo "3. 新增專案："
    echo "   bash scripts/manage.sh add myproject /path/to/project"
    echo ""
    echo "4. 啟用專案："
    echo "   bash scripts/manage.sh activate myproject"
    echo ""
    echo "5. 建立向量索引（如果沒有恢復）："
    echo "   python retrieval/build_vector_index.py"
    echo ""
    echo "6. 檢查狀態："
    echo "   bash scripts/manage.sh status"
    echo ""
    
    print_info "完整文檔請參考："
    echo "  - README.md"
    echo "  - docs/ARCHITECTURE.md"
    echo "  - docs/MULTI_PROJECT.md"
    echo ""
}

# ============================================================
# 主程式
# ============================================================

main() {
    clear
    print_header "augment-lite-mcp 新電腦設置嚮導"
    echo ""
    
    # 1. 檢查系統需求
    check_requirements
    
    # 2. 安裝依賴
    install_dependencies
    
    # 3. 配置環境變數
    configure_env
    
    # 4. 遷移資料（可選）
    migrate_data
    
    # 5. 更新專案路徑（如果有）
    update_project_paths
    
    # 6. 執行資料庫遷移（如果需要）
    run_migrations
    
    # 7. 檢查本地 Proxy
    check_local_proxy
    
    # 8. 測試配置
    read -p "是否執行配置測試？[y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_configuration
    fi
    
    # 9. 顯示下一步
    show_next_steps
}

main "$@"

