# augment-lite-mcp

> **Zero-Maintenance AI Code Assistant** - Local-first, cost-effective, privacy-safe

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/yourusername/augment-lite-mcp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.1+-green.svg)](https://github.com/anthropics/mcp)

---

## 🎯 What is augment-lite-mcp?

augment-lite-mcp 是一個**零維護、本地優先**的 AI 代碼助手引擎，透過 MCP (Model Context Protocol) 整合到 Claude Code 等 AI 編程工具。

### 💡 核心價值

```
零維護搜索 + 本地隱私 + 低成本 AI = 理想的編程助手
```

- **🔥 Zero Maintenance**: 自動增量索引，無需手動重建
- **🔒 Privacy First**: 代碼完全本地存儲（DuckDB + SQLite）
- **💰 Cost Effective**: 每次查詢 ~$0.00005（比純 LLM 便宜 1000 倍）
- **🎯 High Accuracy**: 85% 準確度（混合本地向量 + 遠端 LLM 過濾）

---

## ✨ 核心特性

### 1. 🚀 Auto-Incremental Indexing
**acemcp-inspired 零維護體驗**

```bash
# 不需要手動 rebuild，一切自動完成
./scripts/manage.sh add auto .  # 初次添加專案

# 之後無論如何修改代碼
# 搜索時自動檢測變更並更新索引
```

- ✅ 自動檢測文件變更（mtime + MD5）
- ✅ 只更新變更的文件（60x faster）
- ✅ 完全透明，用戶無感知

### 2. 🔍 Dual-Layer Retrieval
**本地向量 + 遠端 LLM 智能過濾**

```
Layer 1: 本地 PyTorch 嵌入 (sentence-transformers)
  → BM25 + Vector 混合搜索
  → 50 個候選結果
  → 模型: all-MiniLM-L6-v2 (384 dims, 90MB)

Layer 2: Gemini LLM 智能過濾
  → 語義理解 + 去重
  → 最終 8 個高質量結果
```

**結果**:
- 成本: ~$0.00005/query（99.9% 本地處理）
- 延遲: ~1.05s
- 準確度: 85%

**模型選擇**: 支持多種嵌入模型，詳見 [Vector Models 比較](docs/core/COMPARISON.md#vector-embedding-models-比較)

### 3. 📁 Multi-Project Management
**彈性專案組織**

```bash
# 三種方式指定專案
./scripts/manage.sh add myproject /path/to/project  # 名稱
./scripts/manage.sh rebuild 45d8fb52                # ID (8 字元)
./scripts/manage.sh add auto .                      # 自動偵測

# Claude Code 自動使用當前工作目錄專案
# 無需手動切換
```

### 4. 💾 Advanced Caching
**三層快取加速**

- **精確快取** (SQLite): 完全匹配的查詢
- **語義快取** (FAISS): 相似查詢（95% 閾值）
- **Provider 快取** (Requesty/Proxy): API 級別

**結果**: 90% 查詢 < 100ms

### 5. 🧠 Memory & Tasks
**長期記憶 + 任務追蹤**

```python
# 長期記憶（跨會話持久化）
memory.set("api_key", "secret_value", project="myproject")
memory.get("api_key")

# 任務管理
task.add("Implement feature X", priority=10)
task.list(status="in_progress")
```

### 6. 🌐 Web UI (v1.0.0)
**專業管理界面**

```bash
cd web_ui && ./start.sh  # http://localhost:8080
```

- ✅ 實時日誌流（WebSocket）
- ✅ 交互式搜索測試
- ✅ 專案儀表板
- ✅ 現代化深色主題

### 7. 🤖 MCP Protocol Compliance
**22 個 MCP Tools**

| 類別 | Tools |
|------|-------|
| **RAG** | `rag.search`, `answer.generate` |
| **Project** | `project.init`, `project.status`, `index.rebuild` |
| **Cache** | `cache.clear`, `cache.status` |
| **Memory** | `memory.get`, `memory.set`, `memory.delete`, `memory.list`, `memory.clear` |
| **Tasks** | `task.add`, `task.list`, `task.update`, `task.get`, `task.delete`, `task.resume`, `task.current`, `task.stats` |

---

## 📦 快速開始

### 安裝

```bash
# 1. Clone repository
git clone https://github.com/yourusername/augment-lite-mcp.git
cd augment-lite-mcp

# 2. 安裝依賴
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt

# 3. (可選) 安裝向量搜索依賴 (~2GB)
bash scripts/install_vector_deps.sh

# 4. 添加專案並建立索引
./scripts/manage.sh add auto .
```

### 配置 MCP

#### 方式 1: Claude MCP CLI（推薦）

```bash
# 使用 Claude MCP CLI 一鍵配置
claude mcp add --scope user --transport stdio augment-lite \
  --env AUGMENT_DB_DIR="$HOME/augment-lite-mcp/data" \
  --env KIMI_LOCAL_KEY="dummy" \
  --env GLM_LOCAL_KEY="dummy" \
  --env MINIMAXI_LOCAL_KEY="dummy" \
  --env GEMINI_LOCAL_KEY="dummy" \
  --env REQUESTY_API_KEY="your-requesty-api-key-here" \
  -- "$HOME/augment-lite-mcp/.venv/bin/python" \
     "-u" "$HOME/augment-lite-mcp/mcp_bridge_lazy.py"
```

#### 方式 2: 手動配置 JSON

編輯 `~/.claude/config.json`:

```json
{
  "mcpServers": {
    "augment-lite": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-u", "/absolute/path/to/mcp_bridge_lazy.py"],
      "env": {
        "AUGMENT_DB_DIR": "/absolute/path/to/data",
        "KIMI_LOCAL_KEY": "dummy",
        "GLM_LOCAL_KEY": "dummy",
        "MINIMAXI_LOCAL_KEY": "dummy",
        "GEMINI_LOCAL_KEY": "dummy",
        "REQUESTY_API_KEY": "your-requesty-api-key-here"
      }
    }
  }
}
```

**環境變量說明**:
- `AUGMENT_DB_DIR`: 數據目錄（索引、快取、記憶）
- `REQUESTY_API_KEY`: Requesty.ai API 密鑰（必須）
- `*_LOCAL_KEY`: 本地 Proxy 認證（可選，設為 "dummy" 如不使用）

### 使用

```python
# 在 Claude Code 中
# AI 會自動使用 augment-lite MCP tools

# 搜索代碼
"幫我找到處理用戶登錄的代碼"

# 生成答案（帶引用）
"如何配置資料庫連接？"

# 管理任務
"添加任務：重構認證模組"
```

---

## 🏗️ 架構概覽

```
┌──────────────────────────────────────────────┐
│            Claude Code (AI Assistant)         │
└─────────────────┬────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼────────────────────────────┐
│         mcp_bridge_lazy.py (22 Tools)        │
└─────────────────┬────────────────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌────▼─────┐  ┌──▼──────┐  ┌─▼────────┐
│ Retrieval│  │  Cache  │  │  Memory  │
│ (BM25+   │  │ (3-Layer│  │ (SQLite) │
│  Vector) │  │  Cache) │  └──────────┘
└────┬─────┘  └─────────┘
     │
┌────▼─────────────────────────────────┐
│  Layer 1: Local Embeddings           │
│  - sentence-transformers (PyTorch)   │
│  - BM25 + FAISS hybrid search        │
│  - 50 candidates                     │
└────┬─────────────────────────────────┘
     │
┌────▼─────────────────────────────────┐
│  Layer 2: Remote LLM Re-ranking      │
│  - Gemini 2.5 Flash (Port 8084)      │
│  - Smart filtering + deduplication   │
│  - Final 8 results                   │
└──────────────────────────────────────┘
```

---

## 🎯 支援的功能

### ✅ 已實現

- [x] Auto-incremental indexing (零維護)
- [x] Dual-layer retrieval (本地+遠端)
- [x] Multi-project management (名稱/ID/auto)
- [x] Three-layer caching (精確+語義+Provider)
- [x] Long-term memory (global/project scope)
- [x] Task management (structured tracking)
- [x] Web UI (FastAPI + WebSocket)
- [x] MCP protocol compliance (22 tools)
- [x] AI auto-discovery (server instructions)
- [x] Gitignore filtering
- [x] Model-specific system prompts
- [x] Dynamic token limits
- [x] Guardrails (evidence citation)

### 🚧 計劃中 (v1.1.0+)

- [ ] Multi-language embeddings (multilingual-e5-large)
- [ ] Code-specific embeddings (CodeBERT, UniXcoder)
- [ ] GraphRAG integration (code dependency graphs)
- [ ] Incremental vector index updates
- [ ] Cloud deployment options (Docker Compose)
- [ ] VSCode extension (alternative to MCP)
- [ ] Monitoring dashboard (metrics, usage stats)
- [ ] Plugin system (custom tools)

---

## 📊 效能指標

| 指標 | 數值 | 說明 |
|------|------|------|
| **Indexing Speed** | 1000+ files/sec | DuckDB BM25 索引 |
| **Incremental Update** | 0.5s (1 file) | 比全量重建快 60x |
| **Search Latency** | ~1.05s | 含 LLM 過濾 |
| **Cost per Query** | ~$0.00005 | 99.9% 本地處理 |
| **Accuracy** | 85% | 混合搜索 + LLM 過濾 |
| **Cache Hit Rate** | +20% | 語義快取提升 |

---

## 📊 競品比較

想了解 augment-lite-mcp 與其他方案的差異？

- **vs Anthropic @modelcontextprotocol/context**: [查看對比](docs/core/COMPARISON.md#augment-lite-mcp-vs-anthropic-官方-context-providers)
- **vs acemcp**: [查看對比](docs/core/COMPARISON.md#1-augment-lite-mcp-vs-acemcp)
- **vs Augment Code**: [查看對比](docs/core/COMPARISON.md#2-augment-lite-mcp-vs-augment-code-proprietary)
- **vs Qdrant/Weaviate**: [查看對比](docs/core/COMPARISON.md#3-augment-lite-mcp-vs-qdrantweaviate-vector-dbs)
- **Vector Models 選擇指南**: [查看詳情](docs/core/COMPARISON.md#vector-embedding-models-比較)

---

## 🙏 致謝與靈感來源

### 主要靈感來源

- **[acemcp](https://github.com/wxxedu/acemcp)** by @wxxedu
  - 💡 Auto-incremental indexing 實現方式
  - 💡 Zero-maintenance 哲學
  - 💡 Web UI 設計靈感

- **[Augment Code](https://www.augmentcode.com/)** (Proprietary)
  - 💡 Context Engine 架構洞察
  - 💡 Two-stage retrieval (local + remote) 概念

- **[@modelcontextprotocol/context](https://github.com/modelcontextprotocol/servers)** by Anthropic
  - 💡 MCP 協議標準參考
  - 💡 簡潔高效的文件訪問設計

### 技術棧感謝

- **[sentence-transformers](https://www.sbert.net/)** by Hugging Face
  - all-MiniLM-L6-v2 嵌入模型
  - 本地、免費、高質量

- **[Requesty.ai](https://requesty.ai/)**
  - 多模型聚合平台
  - 300+ 模型統一 API

- **[DuckDB](https://duckdb.org/)** - 嵌入式 SQL 資料庫
- **[FAISS](https://github.com/facebookresearch/faiss)** (Meta) - 向量相似度搜索
- **[FastAPI](https://fastapi.tiangolo.com/)** - 現代 Web 框架
- **[Claude Code](https://www.anthropic.com/)** - MCP 協議與開發工具

---

## 📝 文檔

### 用戶文檔 (可選安裝)

```bash
# docs/ 目錄包含完整文檔（已加入 .gitignore）
# 如需閱讀，可在本地查看或在線生成
```

- `docs/guides/` - 使用指南
  - MCP Setup, Multi-Project, Vector Search, Cache, Memory, Tasks
- `docs/features/` - 功能說明
- `docs/core/` - 架構與技術概覽
- `docs/bugfixes/` - Bug 修復記錄

### 開發者文檔 (內部參考)

- `init/specs/` - 技術規格
- `init/guidelines/` - 編碼標準、命名規範、文檔指引
- `init/workflows/` - 發布、修復、功能開發流程

### 測試

```bash
# 快速環境檢查
./health_check.sh

# 完整測試套件
python tests/run_all_tests.py

# 單獨測試
python tests/test_high_priority_apis.py
```

詳見 [TESTING.md](TESTING.md)

---

## 🤝 貢獻

歡迎貢獻！請遵循以下流程：

1. Fork 本倉庫
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

詳見 `init/workflows/RELEASE_WORKFLOW.md` 和 `init/guidelines/CODING_STANDARDS.md`

---

## 📄 授權

本專案採用 MIT License - 詳見 [LICENSE](LICENSE) 文件

---

## 🔗 相關連結

- **Repository**: https://github.com/yourusername/augment-lite-mcp
- **Issues**: https://github.com/yourusername/augment-lite-mcp/issues
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **MCP Protocol**: https://github.com/anthropics/mcp

---

## 💬 社群與支援

- GitHub Issues: 報告 bug 或功能請求
- Discussions: 提問或分享使用經驗

---

**Made with ❤️ by the community**

*Inspired by acemcp, Augment Code, and the open-source AI community*
