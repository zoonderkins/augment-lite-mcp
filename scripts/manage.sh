#!/bin/bash
# augment-lite-mcp 管理腳本
# 用途：管理專案、快取、資料庫，檢查本地 proxy 狀態

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
# 檢查並初始化虛擬環境
# ============================================================

check_and_init_venv() {
    # 檢查虛擬環境是否存在
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}⚠️  虛擬環境不存在，正在創建...${NC}"
        python3 -m venv .venv
        echo -e "${GREEN}✅ 虛擬環境已創建${NC}"
        echo ""

        # 安裝基礎依賴
        echo -e "${BLUE}ℹ️  正在安裝基礎依賴...${NC}"
        .venv/bin/pip install --upgrade pip > /dev/null 2>&1

        # 安裝核心依賴（不含向量檢索）
        if [ -f "requirements-lock.txt" ]; then
            .venv/bin/pip install -r requirements-lock.txt > /dev/null 2>&1
        fi

        echo -e "${GREEN}✅ 基礎依賴已安裝${NC}"
        echo ""

        # 詢問是否安裝向量檢索依賴
        read -p "是否安裝向量檢索依賴？（啟用語義搜尋）[y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            bash scripts/install_vector_deps.sh
        else
            echo -e "${YELLOW}⚠️  跳過向量檢索依賴安裝${NC}"
            echo -e "${BLUE}ℹ️  稍後可執行: bash scripts/install_vector_deps.sh${NC}"
        fi
        echo ""
    fi

    # 啟動虛擬環境
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
}

# 初始化虛擬環境
check_and_init_venv

# Python 執行檔
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

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
# 檢查本地 Proxy 狀態
# ============================================================

check_proxy_status() {
    print_header "檢查本地 Proxy 狀態"
    echo ""
    
    local ports=(8081 8082 8083)
    local names=("Kimi K2-0905" "GLM-4.6" "Minimaxi M2")
    local all_ok=true
    
    for i in "${!ports[@]}"; do
        local port="${ports[$i]}"
        local name="${names[$i]}"
        
        if nc -z 127.0.0.1 "$port" 2>/dev/null; then
            print_success "Port $port ($name) - 運行中"
        else
            print_error "Port $port ($name) - 未運行"
            all_ok=false
        fi
    done
    
    echo ""
    
    if [ "$all_ok" = true ]; then
        print_success "所有本地 Proxy 都在運行中"
    else
        print_warning "部分本地 Proxy 未運行"
        echo ""
        print_info "如需啟動本地 Proxy，請參考文檔或使用以下命令："
        echo "  # 啟動 Kimi Proxy (port 8081)"
        echo "  # 啟動 GLM Proxy (port 8082)"
        echo "  # 啟動 Minimaxi Proxy (port 8083)"
    fi
    
    echo ""
}

# ============================================================
# 專案管理
# ============================================================

list_projects() {
    print_header "專案列表"
    echo ""
    $PYTHON retrieval/multi_project.py list
    echo ""
}

add_project() {
    local name="$1"
    local path="$2"

    if [ -z "$name" ]; then
        print_error "用法: $0 add <project_name|auto> <project_path>"
        echo ""
        echo "範例："
        echo "  $0 add myproject /path/to/project"
        echo "  $0 add auto .  # 自動偵測當前目錄"
        exit 1
    fi

    # Default to current directory if path not specified
    if [ -z "$path" ]; then
        if [ "$name" = "auto" ]; then
            path="."
        else
            print_error "請指定專案路徑"
            exit 1
        fi
    fi

    if [ "$name" = "auto" ]; then
        print_header "新增專案: [自動偵測]"
    else
        print_header "新增專案: $name"
    fi
    echo ""
    $PYTHON retrieval/multi_project.py add "$name" "$path"
    echo ""

    # 檢查是否已安裝向量檢索依賴
    if $PYTHON -c "import faiss; import sentence_transformers" 2>/dev/null; then
        # 詢問是否也建立向量索引
        read -p "是否也建立向量索引？（建議建立以啟用語義搜尋）[Y/n] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "正在建立向量索引..."
            # Resolve the actual project name (handles 'auto')
            local actual_name=$($PYTHON -c "import sys; sys.path.insert(0, 'retrieval'); from multi_project import resolve_project_name; print(resolve_project_name('$name'))")
            $PYTHON retrieval/build_vector_index.py "$actual_name"
            print_success "向量索引已建立"
        else
            print_warning "跳過向量索引建立（稍後可執行: python retrieval/build_vector_index.py $name）"
        fi
    else
        print_warning "向量檢索依賴未安裝，跳過向量索引建立"
        echo ""
        print_info "如需啟用向量檢索，請執行："
        echo "  pip install -r requirements.txt"
        echo "  python retrieval/build_vector_index.py $name"
    fi
    echo ""
}

activate_project() {
    local name="$1"

    if [ -z "$name" ]; then
        # 列出可用專案
        print_header "可用專案列表"
        echo ""
        $PYTHON retrieval/multi_project.py list
        echo ""
        echo "請輸入專案名稱、ID 或 'auto' (當前目錄):"
        read -p "> " name
    fi

    if [ -z "$name" ]; then
        print_error "專案名稱不能為空"
        return 1
    fi

    if [ "$name" = "auto" ]; then
        print_header "啟用專案: [當前目錄]"
    else
        print_header "啟用專案: $name"
    fi
    echo ""
    $PYTHON retrieval/multi_project.py activate "$name"
    echo ""
}

remove_project() {
    local name="$1"

    if [ -z "$name" ]; then
        # 列出可用專案
        print_header "可用專案列表"
        echo ""
        $PYTHON retrieval/multi_project.py list
        echo ""
        echo "請輸入要刪除的專案名稱、ID 或 'auto' (當前目錄):"
        read -p "> " name
    fi

    if [ -z "$name" ]; then
        print_error "專案名稱不能為空"
        return 1
    fi

    if [ "$name" = "auto" ]; then
        print_header "刪除專案: [當前目錄]"
    else
        print_header "刪除專案: $name"
    fi
    echo ""

    # 確認刪除
    read -p "確定要刪除專案 '$name' 嗎？這將刪除索引檔案。[y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PYTHON retrieval/multi_project.py remove "$name"
        print_success "專案已刪除"
    else
        print_info "取消刪除"
    fi

    echo ""
}

rebuild_project() {
    local name="$1"

    if [ -z "$name" ]; then
        # 列出可用專案
        print_header "可用專案列表"
        echo ""
        $PYTHON retrieval/multi_project.py list
        echo ""
        echo "請輸入要重建的專案名稱、ID 或 'auto' (當前目錄):"
        read -p "> " name
    fi

    if [ -z "$name" ]; then
        print_error "專案名稱不能為空"
        return 1
    fi

    if [ "$name" = "auto" ]; then
        print_header "重建專案索引: [當前目錄]"
    else
        print_header "重建專案索引: $name"
    fi
    echo ""
    $PYTHON retrieval/multi_project.py rebuild "$name"
    echo ""

    # 檢查是否已安裝向量檢索依賴
    if $PYTHON -c "import faiss; import sentence_transformers" 2>/dev/null; then
        # 詢問是否也重建向量索引
        read -p "是否也重建向量索引？[y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "正在重建向量索引..."
            # Resolve the actual project name (handles 'auto')
            local actual_name=$($PYTHON -c "import sys; sys.path.insert(0, 'retrieval'); from multi_project import resolve_project_name; print(resolve_project_name('$name'))")
            $PYTHON retrieval/build_vector_index.py "$actual_name"
            print_success "向量索引已重建"
        fi
    else
        print_warning "向量檢索依賴未安裝，跳過向量索引重建"
        echo ""
        print_info "如需啟用向量檢索，請執行："
        echo "  pip install -r requirements.txt"
    fi
    echo ""
}

# ============================================================
# 快取管理
# ============================================================

clear_cache() {
    local scope="$1"
    
    print_header "清理快取"
    echo ""
    
    if [ -z "$scope" ]; then
        echo "請選擇清理範圍："
        echo "  1) 全域快取 (global)"
        echo "  2) 活動專案快取 (active)"
        echo "  3) 所有快取 (all)"
        echo "  4) 取消"
        echo ""
        read -p "請選擇 [1-4]: " choice
        
        case $choice in
            1) scope="global" ;;
            2) scope="active" ;;
            3) scope="all" ;;
            4) print_info "取消清理"; return ;;
            *) print_error "無效選擇"; return ;;
        esac
    fi
    
    # 確認清理
    read -p "確定要清理 '$scope' 快取嗎？[y/N] " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PYTHON -c "
from cache import clear
project = None if '$scope' == 'global' else ('auto' if '$scope' == 'active' else 'all')
clear(project=project)
"
        print_success "快取已清理"
    else
        print_info "取消清理"
    fi
    
    echo ""
}

# ============================================================
# 資料管理
# ============================================================

clean_data() {
    print_header "清理資料"
    echo ""

    echo "這將刪除以下資料："
    echo "  - data/corpus*.duckdb (所有索引資料庫)"
    echo "  - data/chunks*.jsonl (所有分塊資料)"
    echo "  - data/index_state*.json (增量索引狀態) [v0.7.0 新增]"
    echo "  - data/vector_index*.faiss (所有向量索引)"
    echo "  - data/vector_chunks*.pkl (所有向量 chunks)"
    echo "  - data/semantic_cache*.faiss (所有語義快取索引)"
    echo "  - data/semantic_cache_entries*.pkl (所有語義快取項目)"
    echo "  - data/response_cache.sqlite (回應快取)"
    echo "  - data/memory.sqlite (長期記憶)"
    echo "  - data/projects.json (專案配置)"
    echo ""

    print_warning "這是危險操作！所有資料將被刪除！"
    echo ""
    
    read -p "確定要繼續嗎？請輸入 'DELETE' 確認: " confirm
    
    if [ "$confirm" = "DELETE" ]; then
        echo ""
        print_info "開始清理..."
        
        # 刪除符號連結（如果存在）
        if [ -L "data/corpus.duckdb" ]; then
            rm -f data/corpus.duckdb
            print_success "已刪除 corpus.duckdb 符號連結"
        fi
        if [ -L "data/chunks.jsonl" ]; then
            rm -f data/chunks.jsonl
            print_success "已刪除 chunks.jsonl 符號連結"
        fi

        # 刪除索引檔案
        rm -f data/corpus*.duckdb
        rm -f data/chunks*.jsonl
        print_success "已刪除索引檔案"

        # 刪除增量索引狀態 (v0.7.0)
        rm -f data/index_state*.json
        print_success "已刪除增量索引狀態"

        # 刪除向量索引
        rm -f data/vector_index*.faiss
        rm -f data/vector_chunks*.pkl
        print_success "已刪除向量索引"

        # 刪除語義快取
        rm -f data/semantic_cache*.faiss
        rm -f data/semantic_cache_entries*.pkl
        print_success "已刪除語義快取"

        # 刪除快取
        rm -f data/response_cache.sqlite
        print_success "已刪除回應快取"

        # 刪除記憶
        rm -f data/memory.sqlite
        print_success "已刪除長期記憶"

        # 刪除專案配置
        rm -f data/projects.json
        print_success "已刪除專案配置"
        
        echo ""
        print_success "資料清理完成"
    else
        print_info "取消清理"
    fi
    
    echo ""
}

backup_data() {
    print_header "備份資料"
    echo ""
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="backups/backup_${timestamp}"
    
    mkdir -p "$backup_dir"
    
    # 備份所有資料
    if [ -d "data" ]; then
        cp -r data "$backup_dir/"
        print_success "已備份 data/ 到 $backup_dir/"
    fi
    
    # 備份配置
    if [ -f "config/models.yaml" ]; then
        mkdir -p "$backup_dir/config"
        cp config/models.yaml "$backup_dir/config/"
        print_success "已備份 config/models.yaml"
    fi
    
    echo ""
    print_success "備份完成: $backup_dir"
    echo ""
}

# ============================================================
# 系統狀態
# ============================================================

show_status() {
    print_header "系統狀態"
    echo ""
    
    # 檢查 Python 環境
    if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
        print_success "Python 虛擬環境: 已安裝"
    else
        print_warning "Python 虛擬環境: 未安裝"
    fi
    
    # 檢查資料目錄
    if [ -d "data" ]; then
        local db_count=$(ls -1 data/corpus*.duckdb 2>/dev/null | wc -l)
        local chunks_count=$(ls -1 data/chunks*.jsonl 2>/dev/null | wc -l)
        print_info "索引資料庫: $db_count 個"
        print_info "分塊資料: $chunks_count 個"
    else
        print_warning "資料目錄: 不存在"
    fi
    
    # 檢查向量索引
    local vector_count=$(ls -1 data/vector_index*.faiss 2>/dev/null | wc -l)
    if [ "$vector_count" -gt 0 ]; then
        local vector_total_size=$(du -ch data/vector_index*.faiss data/vector_chunks*.pkl 2>/dev/null | grep total | cut -f1)
        print_info "向量索引: $vector_count 個 (總大小: $vector_total_size)"
    else
        print_info "向量索引: 0 個"
    fi

    # 檢查語義快取
    local semantic_cache_count=$(ls -1 data/semantic_cache*.faiss 2>/dev/null | wc -l)
    if [ "$semantic_cache_count" -gt 0 ]; then
        local semantic_total_size=$(du -ch data/semantic_cache*.faiss data/semantic_cache_entries*.pkl 2>/dev/null | grep total | cut -f1)
        print_info "語義快取: $semantic_cache_count 個 (總大小: $semantic_total_size)"
    else
        print_info "語義快取: 0 個"
    fi

    # 檢查快取
    if [ -f "data/response_cache.sqlite" ]; then
        local cache_size=$(du -h data/response_cache.sqlite | cut -f1)
        print_info "回應快取: $cache_size"
    else
        print_info "回應快取: 不存在"
    fi

    # 檢查記憶
    if [ -f "data/memory.sqlite" ]; then
        local memory_size=$(du -h data/memory.sqlite | cut -f1)
        print_info "長期記憶: $memory_size"
    else
        print_info "長期記憶: 不存在"
    fi

    # 檢查增量索引狀態 (v0.7.0)
    local index_state_count=$(ls -1 data/index_state*.json 2>/dev/null | wc -l)
    if [ "$index_state_count" -gt 0 ]; then
        print_info "增量索引狀態: $index_state_count 個專案"
    else
        print_info "增量索引狀態: 未初始化"
    fi

    # 檢查 Web UI
    if [ -d "web_ui" ]; then
        if [ -f "web_ui/.venv/bin/uvicorn" ] || command -v uvicorn &> /dev/null; then
            print_success "Web UI: 已安裝 (啟動: cd web_ui && ./start.sh)"
        else
            print_warning "Web UI: 未安裝依賴 (安裝: cd web_ui && uv pip install -r requirements.txt)"
        fi
    else
        print_warning "Web UI: 目錄不存在"
    fi

    echo ""

    # 檢查本地 Proxy
    check_proxy_status
}

# ============================================================
# Web UI 管理 (v0.7.0)
# ============================================================

start_web_ui() {
    print_header "啟動 Web UI"
    echo ""

    if [ ! -d "web_ui" ]; then
        print_error "Web UI 目錄不存在"
        return 1
    fi

    cd web_ui

    # 檢查依賴
    if ! $PYTHON -c "import fastapi; import uvicorn" 2>/dev/null; then
        print_warning "Web UI 依賴未安裝"
        echo ""
        read -p "是否現在安裝？[Y/n] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "正在安裝依賴..."
            if command -v uv &> /dev/null; then
                uv pip install -r requirements.txt
            else
                $PYTHON -m pip install -r requirements.txt
            fi
            print_success "依賴安裝完成"
            echo ""
        else
            print_info "取消啟動"
            cd ..
            return 1
        fi
    fi

    # 詢問端口
    read -p "請輸入端口號 [默認 8080]: " port
    port=${port:-8080}

    echo ""
    print_success "正在啟動 Web UI 於端口 $port..."
    print_info "訪問: http://localhost:$port"
    print_info "API 文檔: http://localhost:$port/docs"
    echo ""
    print_warning "按 Ctrl+C 停止服務器"
    echo ""

    # 啟動 Web UI
    $PYTHON -m uvicorn main:app --host 0.0.0.0 --port "$port" --reload
}

install_web_ui_deps() {
    print_header "安裝 Web UI 依賴"
    echo ""

    if [ ! -d "web_ui" ]; then
        print_error "Web UI 目錄不存在"
        return 1
    fi

    cd web_ui

    print_info "正在安裝依賴..."
    if command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
        print_success "使用 uv 安裝完成"
    else
        $PYTHON -m pip install -r requirements.txt
        print_success "使用 pip 安裝完成"
    fi

    cd ..
    echo ""
}

# ============================================================
# 主選單
# ============================================================

show_menu() {
    clear
    print_header "augment-lite-mcp 管理工具 v0.7.0"
    echo ""
    echo "專案管理："
    echo "  1) 列出所有專案"
    echo "  2) 新增專案"
    echo "  3) 啟用專案"
    echo "  4) 刪除專案"
    echo "  5) 重建專案索引"
    echo ""
    echo "快取管理："
    echo "  6) 清理快取"
    echo ""
    echo "資料管理："
    echo "  7) 清理所有資料 (危險)"
    echo "  8) 備份資料"
    echo ""
    echo "Web UI (v0.7.0 新增)："
    echo "  11) 啟動 Web UI"
    echo "  12) 安裝 Web UI 依賴"
    echo ""
    echo "系統："
    echo "  9) 檢查系統狀態"
    echo "  10) 檢查本地 Proxy 狀態"
    echo ""
    echo "  0) 退出"
    echo ""
}

interactive_mode() {
    while true; do
        show_menu
        read -p "請選擇操作 [0-12]: " choice
        echo ""

        case $choice in
            1) list_projects; read -p "按 Enter 繼續..." ;;
            2)
                echo "專案名稱 (輸入 'auto' 自動偵測當前目錄):"
                read -p "> " name
                if [ "$name" = "auto" ]; then
                    path="."
                else
                    read -p "專案路徑: " path
                fi
                add_project "$name" "$path"
                read -p "按 Enter 繼續..."
                ;;
            3)
                activate_project
                read -p "按 Enter 繼續..."
                ;;
            4)
                remove_project
                read -p "按 Enter 繼續..."
                ;;
            5)
                echo "請選擇重建範圍："
                echo "  1) 重建單一專案"
                echo "  2) 重建所有專案"
                echo "  3) 取消"
                echo ""
                read -p "請選擇 [1-3]: " rebuild_choice

                case $rebuild_choice in
                    1)
                        rebuild_project
                        ;;
                    2)
                        print_header "重建所有專案索引"
                        echo ""
                        $PYTHON retrieval/multi_project.py rebuild
                        echo ""
                        ;;
                    3)
                        print_info "取消重建"
                        ;;
                    *)
                        print_error "無效選擇"
                        ;;
                esac
                read -p "按 Enter 繼續..."
                ;;
            6) clear_cache; read -p "按 Enter 繼續..." ;;
            7) clean_data; read -p "按 Enter 繼續..." ;;
            8) backup_data; read -p "按 Enter 繼續..." ;;
            9) show_status; read -p "按 Enter 繼續..." ;;
            10) check_proxy_status; read -p "按 Enter 繼續..." ;;
            11) start_web_ui ;;
            12) install_web_ui_deps; read -p "按 Enter 繼續..." ;;
            0) print_info "再見！"; exit 0 ;;
            *) print_error "無效選擇"; read -p "按 Enter 繼續..." ;;
        esac
    done
}

# ============================================================
# 主程式
# ============================================================

main() {
    if [ $# -eq 0 ]; then
        # 無參數：進入互動模式
        interactive_mode
    else
        # 有參數：執行對應命令
        case "$1" in
            list) list_projects ;;
            add) add_project "$2" "$3" ;;
            activate) activate_project "$2" ;;
            remove) remove_project "$2" ;;
            rebuild) rebuild_project "$2" ;;
            clear-cache) clear_cache "$2" ;;
            clean) clean_data ;;
            backup) backup_data ;;
            status) show_status ;;
            check-proxy) check_proxy_status ;;
            start-web-ui) start_web_ui ;;
            install-web-ui) install_web_ui_deps ;;
            *)
                echo "用法: $0 [command] [args]"
                echo ""
                echo "命令："
                echo "  list                         列出所有專案"
                echo "  add <name|auto> <path>       新增專案 ('auto' 自動偵測)"
                echo "  activate <name|id|auto>      啟用專案"
                echo "  remove <name|id|auto>        刪除專案"
                echo "  rebuild <name|id|auto>       重建專案索引"
                echo "  clear-cache [scope]          清理快取 (global/active/all)"
                echo "  clean                        清理所有資料"
                echo "  backup                       備份資料"
                echo "  status                       顯示系統狀態"
                echo "  check-proxy                  檢查本地 Proxy 狀態"
                echo ""
                echo "Web UI (v0.7.0 新增)："
                echo "  start-web-ui                 啟動 Web UI"
                echo "  install-web-ui               安裝 Web UI 依賴"
                echo ""
                echo "專案可使用名稱、ID 或 'auto' (當前目錄) 指定"
                echo "無參數時進入互動模式"
                exit 1
                ;;
        esac
    fi
}

main "$@"

