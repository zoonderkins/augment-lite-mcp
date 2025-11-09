# scripts/manage.sh 更新說明 (v0.7.0)

**日期**: 2024-11-09
**版本**: v0.7.0

---

## 🎯 更新內容

### 1. 新增增量索引狀態管理

**新功能**:
- 清理資料時包含 `data/index_state*.json` 檔案
- 系統狀態檢查顯示增量索引狀態

**程式碼變更**:

```bash
# clean_data() 函數
echo "  - data/index_state*.json (增量索引狀態) [v0.7.0 新增]"

# 刪除時
rm -f data/index_state*.json
print_success "已刪除增量索引狀態"

# show_status() 函數
local index_state_count=$(ls -1 data/index_state*.json 2>/dev/null | wc -l)
if [ "$index_state_count" -gt 0 ]; then
    print_info "增量索引狀態: $index_state_count 個專案"
else
    print_info "增量索引狀態: 未初始化"
fi
```

---

### 2. 新增 Web UI 管理功能

**新增命令**:
- `start-web-ui` - 啟動 Web UI 服務器
- `install-web-ui` - 安裝 Web UI 依賴

**互動模式新增選項**:
- `11) 啟動 Web UI`
- `12) 安裝 Web UI 依賴`

**程式碼變更**:

```bash
# 新增 start_web_ui() 函數
start_web_ui() {
    print_header "啟動 Web UI"

    # 檢查 web_ui 目錄
    if [ ! -d "web_ui" ]; then
        print_error "Web UI 目錄不存在"
        return 1
    fi

    cd web_ui

    # 檢查依賴
    if ! $PYTHON -c "import fastapi; import uvicorn" 2>/dev/null; then
        # 詢問是否安裝
        read -p "是否現在安裝？[Y/n] " -n 1 -r
        # ...安裝邏輯
    fi

    # 詢問端口
    read -p "請輸入端口號 [默認 8080]: " port
    port=${port:-8080}

    # 啟動服務器
    $PYTHON -m uvicorn main:app --host 0.0.0.0 --port "$port" --reload
}

# 新增 install_web_ui_deps() 函數
install_web_ui_deps() {
    print_header "安裝 Web UI 依賴"
    cd web_ui

    if command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
    else
        $PYTHON -m pip install -r requirements.txt
    fi
}
```

---

### 3. Web UI 狀態檢查

**show_status() 新增**:

```bash
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
```

---

### 4. 主選單更新

**標題更新**:
```bash
print_header "augment-lite-mcp 管理工具 v0.7.0"
```

**新增選項區塊**:
```bash
echo "Web UI (v0.7.0 新增)："
echo "  11) 啟動 Web UI"
echo "  12) 安裝 Web UI 依賴"
```

**互動範圍更新**:
```bash
read -p "請選擇操作 [0-12]: " choice  # 原本 [0-10]
```

---

## 📊 使用範例

### 命令行模式

```bash
# 啟動 Web UI
./scripts/manage.sh start-web-ui

# 安裝 Web UI 依賴
./scripts/manage.sh install-web-ui

# 檢查系統狀態（包含 Web UI 和增量索引狀態）
./scripts/manage.sh status
```

### 互動模式

```bash
# 啟動互動模式
./scripts/manage.sh

# 選擇選項
請選擇操作 [0-12]: 11  # 啟動 Web UI

# 或
請選擇操作 [0-12]: 12  # 安裝 Web UI 依賴

# 或
請選擇操作 [0-12]: 9   # 檢查系統狀態
```

---

## 🎯 完整功能對照表

| 選項 | 功能 | 版本 |
|------|------|------|
| 1 | 列出所有專案 | v0.x |
| 2 | 新增專案 | v0.x |
| 3 | 啟用專案 | v0.x |
| 4 | 刪除專案 | v0.x |
| 5 | 重建專案索引 | v0.x |
| 6 | 清理快取 | v0.x |
| 7 | 清理所有資料 | v0.x (更新: 包含 index_state) |
| 8 | 備份資料 | v0.x |
| 9 | 檢查系統狀態 | v0.x (更新: 包含 Web UI 和增量索引) |
| 10 | 檢查本地 Proxy 狀態 | v0.x |
| **11** | **啟動 Web UI** | **v0.7.0 新增** |
| **12** | **安裝 Web UI 依賴** | **v0.7.0 新增** |
| 0 | 退出 | v0.x |

---

## 🔧 技術細節

### 依賴檢查邏輯

```bash
# 檢查 FastAPI 和 Uvicorn 是否已安裝
if ! $PYTHON -c "import fastapi; import uvicorn" 2>/dev/null; then
    # 未安裝 - 詢問是否安裝
else
    # 已安裝 - 直接啟動
fi
```

### 端口號處理

```bash
# 詢問用戶端口號，默認 8080
read -p "請輸入端口號 [默認 8080]: " port
port=${port:-8080}  # Bash 參數擴展，如果為空則使用 8080
```

### uv vs pip 自動選擇

```bash
if command -v uv &> /dev/null; then
    # 優先使用 uv（更快）
    uv pip install -r requirements.txt
else
    # 回退到 pip
    $PYTHON -m pip install -r requirements.txt
fi
```

---

## 🚀 啟動流程

### 方式 1: 使用 manage.sh (推薦)

```bash
# 互動模式
./scripts/manage.sh
# 選擇 11 → 輸入端口 → 自動啟動

# 命令行模式
./scripts/manage.sh start-web-ui
```

### 方式 2: 直接使用 start.sh

```bash
cd web_ui
./start.sh [port]
```

### 方式 3: 手動啟動

```bash
cd web_ui
uv pip install -r requirements.txt  # 或 pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 📝 狀態輸出範例

### 系統狀態檢查輸出

```
============================================================
系統狀態
============================================================

✅ Python 虛擬環境: 已安裝
ℹ️  索引資料庫: 2 個
ℹ️  分塊資料: 2 個
ℹ️  向量索引: 2 個 (總大小: 150M)
ℹ️  語義快取: 2 個 (總大小: 50M)
ℹ️  回應快取: 2.5M
ℹ️  長期記憶: 128K
ℹ️  增量索引狀態: 2 個專案 [v0.7.0 新增]
✅ Web UI: 已安裝 (啟動: cd web_ui && ./start.sh) [v0.7.0 新增]

============================================================
檢查本地 Proxy 狀態
============================================================

✅ Port 8081 (Kimi K2-0905) - 運行中
❌ Port 8082 (GLM-4.6) - 未運行
❌ Port 8083 (Minimaxi M2) - 未運行

⚠️  部分本地 Proxy 未運行
```

---

## 🎓 最佳實踐

### 開發工作流

```bash
# 1. 啟動 Web UI（互動式管理）
./scripts/manage.sh start-web-ui

# 2. 在瀏覽器打開
# → http://localhost:8080

# 3. 使用 Web UI 測試搜索、查看日誌

# 4. 如需重建索引（已自動化，通常不需要）
# → 在 Web UI 中執行搜索，自動增量索引
```

### 生產環境部署

```bash
# 1. 安裝依賴
./scripts/manage.sh install-web-ui

# 2. 啟動（使用 systemd 或 supervisor）
cd web_ui
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

---

## 🔄 遷移指南

### 從 v0.6.0 遷移到 v0.7.0

**無需手動操作**，但建議：

1. **檢查系統狀態**：
```bash
./scripts/manage.sh status
```

2. **安裝 Web UI 依賴**：
```bash
./scripts/manage.sh install-web-ui
```

3. **測試 Web UI**：
```bash
./scripts/manage.sh start-web-ui
# 訪問 http://localhost:8080
```

4. **享受零維護索引**：
- 不需要手動 `rebuild`
- 搜索時自動檢測文件變更
- 只索引變更的文件（快 10-100 倍）

---

## 📚 相關文件

- **Web UI 文檔**: `web_ui/README.md`
- **增量索引實現**: `retrieval/incremental_indexer.py`
- **v0.7.0 Release Notes**: `V0.7.0_RELEASE_NOTES.md`
- **快速開始**: `QUICK_START_v0.7.0.md`
- **完整 Changelog**: `CHANGELOG.md`

---

**版本**: v0.7.0
**更新日期**: 2024-11-09
**維護者**: augment-lite-mcp team
