# 測試文件說明

## 目錄結構

```
augment-lite-mcp/
├── test_gemini_mcp.py          # 根目錄：早期測試文件
├── test_mcp_server.sh          # 根目錄：快速整合測試
└── tests/                      # 測試目錄：完整測試套件
    ├── run_all_tests.py        # 測試執行器
    ├── run_new_tests.sh        # 批量測試腳本
    ├── test_*.py               # 各功能模組測試
    └── ...
```

---

## 根目錄 vs tests/ 目錄

### 根目錄測試文件（臨時/快速測試）

#### `test_gemini_mcp.py`
**用途**: 早期 Gemini local proxy 整合測試

**特點**:
- 單一功能測試（Gemini MCP 調用）
- 快速驗證 Gemini port 8084 proxy 是否正常
- 開發階段的臨時測試文件

**何時使用**:
```bash
# 快速測試 Gemini proxy 是否正常
python test_gemini_mcp.py
```

**狀態**: ⚠️ 歷史文件，可考慮移至 `tests/` 或刪除

---

#### `test_mcp_server.sh`
**用途**: MCP 服務器快速整合測試

**特點**:
- Shell 腳本，快速檢查環境配置
- 驗證虛擬環境、數據目錄、索引是否存在
- 測試 MCP 服務器是否可啟動

**何時使用**:
```bash
# 快速檢查 MCP 服務器環境是否正確
./test_mcp_server.sh
```

**狀態**: ✅ 可保留作為快速健康檢查工具

---

### tests/ 目錄（正式測試套件）

#### `tests/run_all_tests.py`
**用途**: 測試執行器，運行所有測試

**特點**:
- Python 測試框架
- 可選擇運行特定測試
- 統一的測試報告

**何時使用**:
```bash
python tests/run_all_tests.py
```

---

#### `tests/test_high_priority_apis.py`
**用途**: 高優先級 MCP API 測試

**測試內容**:
- `answer.generate` - 核心 RAG 功能
- `index.rebuild` - 索引重建
- 完整的功能流程測試

**特點**:
- 單元測試 + 整合測試
- 模擬實際使用場景
- 詳細的測試輸出

---

#### `tests/test_medium_priority_apis.py`
**用途**: 中優先級 MCP API 測試

**測試內容**:
- Memory API (memory.get, memory.set)
- Cache API (cache.clear, cache.status)
- Task API (task.add, task.list)

---

#### `tests/test_auto_mode.py`
**用途**: Auto 模式專項測試

**測試內容**:
- 專案自動偵測
- "auto" 參數解析
- 當前目錄專案識別

---

#### `tests/test_ace_enhancements.py`
**用途**: ACE 增強功能測試

**測試內容**:
- 自動增量索引
- 雙層檢索架構
- 性能測試

---

## 測試文件對比表

| 維度 | 根目錄測試 | tests/ 目錄測試 |
|------|-----------|----------------|
| **目的** | 快速驗證/臨時測試 | 正式測試套件 |
| **範圍** | 單一功能 | 完整功能覆蓋 |
| **結構** | 簡單腳本 | 結構化測試框架 |
| **維護** | 低（可能過時） | 高（持續更新） |
| **執行** | 獨立運行 | 統一執行器 |
| **報告** | 簡單輸出 | 詳細測試報告 |

---

## 建議的清理方案

### 選項 A: 移動到 tests/（推薦）

```bash
# 移動根目錄測試到 tests/
mv test_gemini_mcp.py tests/manual/
mv test_mcp_server.sh tests/integration/

# 創建子目錄
mkdir -p tests/manual tests/integration
```

### 選項 B: 刪除過時測試

```bash
# 如果功能已被 tests/ 覆蓋，可刪除
rm test_gemini_mcp.py  # 已被 tests/test_rag_generate_proxies.py 覆蓋
```

### 選項 C: 保留快速測試

```bash
# 保留 test_mcp_server.sh 作為快速健康檢查
# 刪除或移動其他
mv test_gemini_mcp.py tests/manual/
```

---

## 推薦做法（v1.0.0+）

### 1. 保留快速健康檢查
```
根目錄:
  test_mcp_server.sh  ✅ 保留（重命名為 health_check.sh）
```

### 2. 移動開發測試到 tests/
```
tests/
  ├── manual/
  │   └── test_gemini_mcp.py  # 手動測試
  └── integration/
      └── test_mcp_integration.sh  # 整合測試
```

### 3. 統一測試入口
```bash
# 快速檢查
./health_check.sh

# 完整測試
python tests/run_all_tests.py

# 手動測試
python tests/manual/test_gemini_mcp.py
```

---

## 執行所有測試

```bash
# 方式 1: 使用測試執行器
python tests/run_all_tests.py

# 方式 2: 使用 shell 腳本
bash tests/run_new_tests.sh

# 方式 3: 單獨運行
python tests/test_high_priority_apis.py
python tests/test_medium_priority_apis.py
python tests/test_auto_mode.py

# 方式 4: 快速健康檢查
./test_mcp_server.sh
```

---

## 測試覆蓋範圍

### tests/ 目錄（正式測試）

#### ✅ 已測試功能
- ✅ RAG search and answer generation
- ✅ Project management (init, rebuild, status)
- ✅ Memory API (get, set, delete, list, clear)
- ✅ Cache API (clear, status)
- ✅ Task management (add, list, update, get, delete)
- ✅ Auto mode detection and resolution
- ✅ ACE enhancements (incremental indexing)
- ✅ Deduplication, ranking, filtering
- ✅ Index rebuild logic
- ✅ Proxy routing (Gemini, Kimi, GLM, MiniMax)

#### ❌ v1.3.x 新功能（缺少測試）
> **注意**: 以下功能在 v1.3.x 新增，但測試腳本尚未覆蓋

| 工具 | 描述 | 測試文件 |
|------|------|----------|
| `dual.search` | 雙引擎搜索 (auggie + augment-lite) | ❌ 需要 `test_v1.3_new_features.py` |
| `answer.accumulated` | 多輪累積問答 | ❌ 需要 `test_v1.3_new_features.py` |
| `answer.unified` | 統一編排 (返回執行計劃) | ❌ 需要 `test_v1.3_new_features.py` |
| `code.symbols` | Tree-sitter 符號提取 (12 種語言) | ❌ 需要 `test_v1.3_new_features.py` |
| `code.find_symbol` | 按名稱查找符號定義 | ❌ 需要 `test_v1.3_new_features.py` |
| `code.references` | AST-based 引用查找 | ❌ 需要 `test_v1.3_new_features.py` |
| `search.pattern` | Regex 精確搜索 | ❌ 需要 `test_v1.3_new_features.py` |
| `file.read` | 文件讀取（支持行範圍） | ❌ 需要 `test_v1.3_new_features.py` |
| `file.list` | 目錄列表 | ❌ 需要 `test_v1.3_new_features.py` |
| `file.find` | Glob 模式查找 | ❌ 需要 `test_v1.3_new_features.py` |

**整體覆蓋率**: 21/31 工具 (68%)

### 根目錄（快速測試）
- ⚠️ Gemini MCP basic call (已被 tests/ 覆蓋)
- ✅ MCP server health check (環境驗證)

---

## 結論

**根目錄測試文件**:
- `test_gemini_mcp.py`: 早期開發測試，功能已被 `tests/` 覆蓋，建議移除或歸檔
- `test_mcp_server.sh`: 快速健康檢查工具，建議保留並重命名為 `health_check.sh`

**tests/ 目錄**:
- 完整的測試套件，覆蓋所有核心功能
- 結構化、可維護、持續更新
- 應作為主要測試入口

**建議行動**:
1. 移除 `test_gemini_mcp.py`（或移至 `tests/manual/`）
2. 重命名 `test_mcp_server.sh` 為 `health_check.sh`
3. 更新 README.md 說明測試執行方式
