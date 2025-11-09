#!/bin/bash
# 導出/導入 augment-lite-mcp 資料
# 用途：在不同電腦之間遷移資料

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
# 導出資料
# ============================================================

export_data() {
    print_header "導出資料"
    echo ""
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local export_name="${1:-augment-lite-export-${timestamp}}"
    local export_dir="exports/${export_name}"
    
    print_info "導出目錄: $export_dir"
    echo ""
    
    # 創建導出目錄
    mkdir -p "$export_dir"
    
    # 1. 導出專案配置（不含索引檔案）
    if [ -f "data/projects.json" ]; then
        print_info "導出專案配置..."
        mkdir -p "$export_dir/data"
        cp data/projects.json "$export_dir/data/"
        print_success "專案配置已導出"
    fi
    
    # 2. 導出記憶資料庫
    if [ -f "data/memory.sqlite" ]; then
        print_info "導出記憶資料庫..."
        cp data/memory.sqlite "$export_dir/data/"
        print_success "記憶資料庫已導出"
    fi
    
    # 3. 導出快取資料庫（可選）
    echo ""
    read -p "是否導出快取資料庫？（通常不需要）[y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "data/response_cache.sqlite" ]; then
            cp data/response_cache.sqlite "$export_dir/data/"
            print_success "快取資料庫已導出"
        fi

        # 導出語義快取
        local semantic_cache_count=$(ls -1 data/semantic_cache*.faiss 2>/dev/null | wc -l)
        if [ $semantic_cache_count -gt 0 ]; then
            cp data/semantic_cache*.faiss "$export_dir/data/" 2>/dev/null || true
            cp data/semantic_cache_entries*.pkl "$export_dir/data/" 2>/dev/null || true
            print_success "語義快取已導出 ($semantic_cache_count 個)"
        fi
    fi

    # 4. 導出向量索引（可選）
    echo ""
    read -p "是否導出向量索引？（建議導出，避免重建）[Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        local vector_count=$(ls -1 data/vector_index*.faiss 2>/dev/null | wc -l)
        if [ $vector_count -gt 0 ]; then
            print_info "導出向量索引..."
            cp data/vector_index*.faiss "$export_dir/data/" 2>/dev/null || true
            cp data/vector_chunks*.pkl "$export_dir/data/" 2>/dev/null || true
            print_success "向量索引已導出 ($vector_count 個)"
        else
            print_warning "沒有向量索引可導出"
        fi
    fi
    
    # 5. 導出配置檔案
    if [ -f "config/models.yaml" ]; then
        print_info "導出配置檔案..."
        mkdir -p "$export_dir/config"
        cp config/models.yaml "$export_dir/config/"
        print_success "配置檔案已導出"
    fi
    
    # 6. 導出環境變數範本（不含敏感資訊）
    if [ -f ".env.example" ]; then
        cp .env.example "$export_dir/"
    fi

    # 7. 創建 README
    cat > "$export_dir/README.md" << EOF
# augment-lite-mcp 資料導出

**導出時間：** $(date)
**導出自：** $(hostname)
**版本：** $(cat VERSION 2>/dev/null || echo "unknown")

## 包含的檔案

### 必需檔案
- \`data/projects.json\`: 專案配置（不含索引檔案）
- \`data/memory.sqlite\`: 長期記憶資料庫
- \`config/models.yaml\`: 模型配置
- \`.env.example\`: 環境變數範本

### 可選檔案（根據導出選項）
- \`data/response_cache.sqlite\`: 回應快取
- \`data/semantic_cache*.faiss\`: 語義快取索引
- \`data/semantic_cache_entries*.pkl\`: 語義快取項目
- \`data/vector_index*.faiss\`: 向量索引
- \`data/vector_chunks*.pkl\`: 向量 chunks

## 導入步驟

1. 複製此目錄到新電腦
2. 執行導入腳本：
   \`\`\`bash
   bash scripts/export_import.sh import $export_name
   \`\`\`
3. 更新專案路徑（因為新電腦路徑不同）
4. 如果沒有導出向量索引，需要重建：
   \`\`\`bash
   python retrieval/build_vector_index.py
   \`\`\`

## 注意事項

- ⚠️ 索引檔案（corpus*.duckdb, chunks*.jsonl）未包含在導出中
- ⚠️ 需要在新電腦上重建索引
- ⚠️ 需要更新專案路徑配置
EOF
    
    # 7. 創建壓縮檔
    echo ""
    read -p "是否創建壓縮檔？[Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_info "創建壓縮檔..."
        cd exports
        tar -czf "${export_name}.tar.gz" "$export_name"
        cd ..
        print_success "壓縮檔已創建: exports/${export_name}.tar.gz"
    fi
    
    echo ""
    print_success "導出完成！"
    echo ""
    print_info "導出位置："
    echo "  目錄: $export_dir"
    if [ -f "exports/${export_name}.tar.gz" ]; then
        echo "  壓縮檔: exports/${export_name}.tar.gz"
    fi
    echo ""
    print_info "下一步："
    echo "  1. 將導出檔案複製到新電腦"
    echo "  2. 在新電腦上執行: bash scripts/export_import.sh import $export_name"
    echo ""
}

# ============================================================
# 導入資料
# ============================================================

import_data() {
    print_header "導入資料"
    echo ""
    
    local import_name="$1"
    
    if [ -z "$import_name" ]; then
        print_error "用法: $0 import <export_name>"
        echo ""
        print_info "可用的導出："
        if [ -d "exports" ]; then
            ls -1 exports/
        else
            echo "  (無)"
        fi
        exit 1
    fi
    
    # 檢查導入來源
    local import_source=""
    
    if [ -d "exports/$import_name" ]; then
        import_source="exports/$import_name"
    elif [ -f "exports/${import_name}.tar.gz" ]; then
        print_info "解壓縮 ${import_name}.tar.gz..."
        cd exports
        tar -xzf "${import_name}.tar.gz"
        cd ..
        import_source="exports/$import_name"
        print_success "解壓縮完成"
    elif [ -d "$import_name" ]; then
        import_source="$import_name"
    else
        print_error "找不到導入來源: $import_name"
        exit 1
    fi
    
    echo ""
    print_info "導入來源: $import_source"
    echo ""
    
    # 顯示導入內容
    if [ -f "$import_source/README.md" ]; then
        print_info "導出資訊："
        cat "$import_source/README.md" | head -10
        echo ""
    fi
    
    # 確認導入
    print_warning "這將覆蓋現有的配置和資料！"
    echo ""
    read -p "確定要繼續嗎？[y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消導入"
        exit 0
    fi
    
    # 備份現有資料
    if [ -d "data" ] || [ -d "config" ]; then
        print_info "備份現有資料..."
        local backup_dir="backups/pre-import-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        [ -d "data" ] && cp -r data "$backup_dir/"
        [ -d "config" ] && cp -r config "$backup_dir/"
        print_success "備份完成: $backup_dir"
    fi
    
    echo ""
    
    # 導入資料
    if [ -d "$import_source/data" ]; then
        print_info "導入資料..."
        mkdir -p data
        cp -r "$import_source/data/"* data/
        print_success "資料已導入"
    fi
    
    # 導入配置
    if [ -d "$import_source/config" ]; then
        print_info "導入配置..."
        mkdir -p config
        cp -r "$import_source/config/"* config/
        print_success "配置已導入"
    fi
    
    # 導入環境變數範本
    if [ -f "$import_source/.env.example" ]; then
        if [ ! -f ".env" ]; then
            cp "$import_source/.env.example" .env
            print_success "環境變數範本已導入"
        fi
    fi
    
    echo ""
    print_success "導入完成！"
    echo ""
    
    # 顯示下一步
    print_info "下一步："
    echo ""
    echo "1. 更新專案路徑（因為新電腦路徑不同）："
    echo "   bash scripts/manage.sh"
    echo "   選擇 '2) 新增專案' 或直接編輯 data/projects.json"
    echo ""
    echo "2. 重建索引（如果沒有導入向量索引）："
    echo "   # 重建 BM25 索引"
    echo "   python retrieval/multi_project.py rebuild <project_name>"
    echo "   # 重建向量索引"
    echo "   python retrieval/build_vector_index.py <project_name>"
    echo ""
    echo "3. 檢查配置："
    echo "   編輯 .env 設置 API keys"
    echo "   編輯 config/models.yaml 設置模型配置"
    echo ""
    echo "4. 執行資料庫遷移（如果需要）："
    echo "   python scripts/migrate_all.py"
    echo ""
}

# ============================================================
# 列出導出
# ============================================================

list_exports() {
    print_header "可用的導出"
    echo ""
    
    if [ ! -d "exports" ]; then
        print_info "沒有導出"
        return
    fi
    
    local count=0
    
    # 列出目錄
    for dir in exports/*/; do
        if [ -d "$dir" ]; then
            local name=$(basename "$dir")
            local size=$(du -sh "$dir" | cut -f1)
            echo "📁 $name ($size)"
            
            if [ -f "$dir/README.md" ]; then
                local export_time=$(grep "導出時間" "$dir/README.md" | cut -d: -f2- | xargs)
                echo "   時間: $export_time"
            fi
            
            count=$((count + 1))
        fi
    done
    
    # 列出壓縮檔
    for file in exports/*.tar.gz; do
        if [ -f "$file" ]; then
            local name=$(basename "$file" .tar.gz)
            local size=$(du -sh "$file" | cut -f1)
            echo "📦 $name.tar.gz ($size)"
            count=$((count + 1))
        fi
    done
    
    echo ""
    
    if [ $count -eq 0 ]; then
        print_info "沒有導出"
    else
        print_info "共 $count 個導出"
    fi
    
    echo ""
}

# ============================================================
# 主程式
# ============================================================

main() {
    case "${1:-}" in
        export)
            export_data "$2"
            ;;
        import)
            import_data "$2"
            ;;
        list)
            list_exports
            ;;
        *)
            echo "用法: $0 <command> [args]"
            echo ""
            echo "命令："
            echo "  export [name]    導出資料（可選指定名稱）"
            echo "  import <name>    導入資料"
            echo "  list             列出可用的導出"
            echo ""
            echo "範例："
            echo "  # 導出資料"
            echo "  $0 export"
            echo "  $0 export my-backup"
            echo ""
            echo "  # 列出導出"
            echo "  $0 list"
            echo ""
            echo "  # 導入資料"
            echo "  $0 import augment-lite-export-20251102_143000"
            echo ""
            exit 1
            ;;
    esac
}

main "$@"

