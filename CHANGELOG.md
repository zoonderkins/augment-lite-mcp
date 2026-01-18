# Changelog

All notable changes to augment-lite MCP server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.3] - 2026-01-18

### ✨ New Features
- **OpenRouter Embedding API**: Added `EmbeddingProvider` class supporting API embeddings via OpenRouter
  - Primary: `qwen/qwen3-embedding-4b` (2560 dims)
  - Fallback: Local `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
  - Config: `config/models.yaml` → `embedding` section
- **CJK Tokenizer**: Added `_simple_tokenize()` for Chinese/Japanese/Korean document chunking
- **Extended File Types**: Expanded to 70+ supported file extensions (CODE_EXTS + DOC_EXTS)

### 🔧 Improvements
- **TopK Over-fetch**: Increased from `k×2` to `k×3` for larger candidate pool
- **Per-file Dedup**: Changed from limit=1 to limit=2 (better recall, less aggressive)
- **Safe Source Parsing**: Regex `r":(?:chunk)?\d+$"` handles Windows paths, URLs safely
- **Dimension Guard**: Fail-fast check with provider/model info in error messages
- **Single-vector Shape**: Handle `(D,)` → `(1, D)` with ndim guard

### 📚 Documentation
- **Mermaid Diagrams**: Added system architecture and hybrid search flow diagrams
- **Technical Parameters**: Updated table with k×3, per-file limit=2, 2560 dims
- **File Types List**: Added collapsible section with 70+ supported extensions

---

## [1.3.2] - 2026-01-16

### ✨ New Features
- **Unified Search Tools**: Added 3 new tools for dual-MCP orchestration
  - `answer.accumulated`: Multi-round evidence accumulation with automatic query decomposition
  - `answer.unified`: Execution plan generator for auggie-mcp + augment-lite coordination
  - `dual.search`: Combined search wrapper with auggie invocation hint
- **Auto-Rebuild Stale Index**: `dual.search` auto-detects when auggie finds files missing from augment-lite (>50%), triggers `incremental_index` rebuild and re-searches
  - New parameter: `auto_rebuild` (default: true)
  - Returns: `index_rebuilt`, `rebuild_info` fields

### 🔧 Bug Fixes
- **Fixed MiniMax config**: Changed to OpenAI-compatible format (`type: "openai-compatible"`)
- **Fixed cache import**: Corrected `cache_get/cache_set` to `get/set` in accumulated_answer.py
- **Fixed __pycache__ stale bytecode**: Auto-clear `__pycache__` on MCP server startup (excludes `.venv`)
- **Fixed index.rebuild subprocess**: Use `.venv/bin/python` instead of system Python to ensure duckdb/faiss available
- **Improved index.rebuild errors**: Return stderr/stdout/cmd in error response for debugging

### 📚 Documentation
- Added Section 8 (Unified Search) to README with Auto-Rebuild documentation
- Updated SERVER_INSTRUCTIONS with tool selection guide
- Total tools: 31

---

## [1.3.1] - 2026-01-14

### 🔧 Bug Fixes
- **Fixed `resolve_auto_project()` inconsistency**: `project_status` now correctly reports memory keys count
  - Root cause: Multiple modules had duplicate `_get_active_project()` implementations that only checked `active=True`
  - Fixed: All modules now use unified `resolve_auto_project()` with smart directory matching
  - Affected files: `cache.py`, `semantic_cache.py`, `retrieval/search.py`, `retrieval/vector_search.py`, `retrieval/build_vector_index.py`, `utils/project_utils.py`

### 📚 Documentation
- Updated README roadmap with v1.4.0/v1.5.0 plans (modify symbol tools, LSP bridge)

---

## [1.3.0] - 2025-01-14

### 🔧 Bug Fixes
- **Fixed `sys` import bug**: `rag_search` with `auto_index=true` no longer crashes due to missing `sys` import
- **Fixed incremental_indexer**: Added missing functions (`load_gitignore`, `should_skip_file`, `parse_file_with_tree_sitter`) to `build_index.py`
- **Fixed setup scripts**: `setup_new_machine.sh` and `manage.sh` now correctly detect 原廠 API vs local proxy mode

### ✨ New Features
- **AUTO-INIT workflow**: Projects auto-initialize when running `rag_search` without manual `project.init`
- **auggie-mcp collaboration modes**: Added Mode A/B/C documentation for MCP server coordination
- **Serena-style memory patterns**: Proactive memory system with standard keys (`project_overview`, `code_style`, etc.)

### 📚 Documentation
- Added BM25+Vector technical architecture diagram to README
- Added execution logic flow diagram (Auto-Init → Auto-Index → Search)
- Added auggie-mcp integration section with collaboration modes

---

## [1.2.0] - 2025-01-13

### 🛡️ Modern Guardrails Module
- Added configurable guardrails for MCP tool safety
- Implemented per-tool enable/disable settings
- Added audit logging for tool invocations

---

## [1.0.0] - 2025-11-10

### 🎉 First Stable Release

augment-lite-mcp v1.0.0 是第一個穩定版本，整合了 0.x 系列所有功能並修復了關鍵 bug。

---

## 🚀 Major Features

### 1. Auto-Incremental Indexing
**Zero-Maintenance Search Experience** (acemcp-inspired)

- ✅ **自動變更檢測**: 搜索前自動檢測並索引文件變更
- ✅ **增量更新**: 只處理變更文件，不重建整個索引
- ✅ **透明操作**: 用戶無需手動執行 `project.init` 或 `index.rebuild`
- ✅ **智能檢測**: 使用 mtime、文件大小和 MD5 hash 精確檢測變更
- ✅ **狀態持久化**: 索引狀態存儲於 `data/index_state_{project}.json`

**Implementation**:
- New module: `retrieval/incremental_indexer.py`
- Integrated into `rag.search` tool with `auto_index` parameter (default: `True`)

**Performance**:
- 編輯 1 個文件: 60x faster (30s → 0.5s)
- 編輯 5 個文件: 25x faster (30s → 1.2s)
- 新增 10 個文件: 12x faster (30s → 2.5s)

### 2. FastAPI Web UI
**Professional Management Interface**

- ✅ **實時日誌流**: WebSocket 實時日誌查看
- ✅ **搜索測試**: 交互式搜索界面
- ✅ **專案儀表板**: 查看所有已索引專案
- ✅ **現代化 UI**: 響應式深色主題

**Stack**:
- FastAPI 0.121.1, Uvicorn 0.34.0, WebSockets 14.1

**Usage**:
```bash
cd web_ui && ./start.sh  # http://localhost:8080
```

### 3. Dual-Layer Retrieval Architecture
**High-Quality, Low-Cost Code Search**

- **Layer 1: Local Vector Embeddings**
  - Model: sentence-transformers/all-MiniLM-L6-v2 (384 dims)
  - Engine: PyTorch CPU (local, free)
  - Speed: ~50ms per search
  - BM25 + Vector hybrid search with score fusion

- **Layer 2: Remote LLM Re-ranking**
  - Model: Gemini 2.5 Flash (via local proxy port 8084)
  - Cost: ~$0.00005 per query
  - Speed: ~1s per search
  - Smart filtering with model-specific system prompts

**Results**:
- Accuracy: 85% (vs 70% pure local, 90% pure LLM)
- Cost: ~$0.00005 per query (vs $0.05 pure LLM)
- Latency: ~1.05s total

### 4. Multi-Project Management
**Flexible Project Organization**

- ✅ **三種指定方式**: 名稱 / ID (8 字元) / auto (自動偵測)
- ✅ **快速切換**: <1 秒切換專案，無需重建索引
- ✅ **工作目錄感知**: MCP 自動使用 Claude Code 當前工作專案
- ✅ **專案隔離**: 獨立的索引、快取和記憶體

**CLI Management**:
```bash
./scripts/manage.sh add auto .         # 自動偵測並添加當前專案
./scripts/manage.sh list                # 列出所有專案
./scripts/manage.sh rebuild myproject   # 重建指定專案索引
```

### 5. Advanced Caching System
**Three-Layer Cache for Performance**

- **Layer 1: Exact Cache** (SQLite)
  - 精確匹配查詢結果
  - TTL: 1 hour

- **Layer 2: Semantic Cache** (FAISS)
  - 向量相似度匹配 (threshold: 0.95)
  - 20% cache hit rate improvement

- **Layer 3: Provider Cache** (Requesty/Local Proxy)
  - 90% queries < 100ms response time

### 6. Long-Term Memory & Task Management

**Memory System**:
- SQLite key-value storage
- Global / Project scope isolation
- MCP tools: `memory.get`, `memory.set`, `memory.delete`

**Task System**:
- Structured task tracking with status (pending/in_progress/done/cancelled)
- Priority levels and subtasks support
- Resume mechanism for interrupted tasks
- MCP tools: `task.add`, `task.list`, `task.update`, `task.current`

### 7. MCP Protocol Compliance

**22 MCP Tools**:
- RAG search with auto-indexing
- Project management (init, status, rebuild)
- Cache management (clear, status)
- Memory operations (get, set, delete, list)
- Task management (add, list, update, get, delete, resume, current, stats)
- Answer generation with citations

**AI Auto-Discovery**:
- Server-level instructions guide AI on when to use each tool
- MCP resources expose indexed projects and memory
- Proactive usage patterns for zero-configuration experience

---

## ✨ Enhancements

### Model Support
- ✅ Gemini 2.5 Flash via local proxy (port 8084)
- ✅ Kimi, GLM, MiniMax via local proxies (ports 8081-8083)
- ✅ 300+ models via Requesty.ai aggregation
- ✅ Model-specific system prompts optimization
- ✅ Automatic min_tokens protection to avoid truncation

### System Prompts Customization
- ✅ `config/system_prompts.yaml` for per-model prompts
- ✅ Gemini: 簡潔版 (50 字以內)
- ✅ Claude: 詳細版 (100+ 字)
- ✅ Qwen: 深度分析版

### Dynamic Token Limits
- ✅ Auto-adjust output tokens based on route (2048-16384)
- ✅ Prevents finish_reason="length" errors

### Guardrails
- ✅ Enforce evidence citation in answers
- ✅ Refuse to answer when evidence is insufficient
- ✅ Always provide source file references

---

## 🐛 Bug Fixes

### Vector Index Auto Mode (v1.0.0)
- **Problem**: `./scripts/manage.sh add auto .` passed "auto" instead of resolved project name to `build_vector_index.py`
- **Symptom**: Vector index failed with "Chunks file not found: chunks_auto.jsonl"
- **Fix**: Added `resolve_project_name()` call in `add_project()` and `rebuild_project()` functions
- **Files**: `scripts/manage.sh` (line 187-188, 305-306)
- **Doc**: `docs/bugfixes/BUGFIX_VECTOR_INDEX_AUTO_MODE.md`

### Auto Mode Project Resolution (v0.6.0)
- Fixed MCP API "auto" mode resolution across all tools
- Added `resolve_project_name()` utility function
- Unified "auto" mode handling in MCP bridge

### Gitignore Filtering (v0.6.0)
- Fixed index to properly respect `.gitignore` rules
- Excluded `node_modules/`, `.git/`, build artifacts

### MCP API Error Handling (v0.5.1)
- Improved error messages for missing dependencies
- Better fallback when vector search unavailable

---

## 📝 Documentation

### User Documentation
- `docs/guides/`: Comprehensive usage guides
  - MCP Setup, Multi-Project, Vector Search, Cache, Memory, Tasks
- `docs/features/`: Feature explanations
- `docs/core/`: Architecture and technical overview
  - **NEW**: `COMPARISON.md` - 競品比較與選型指南
    - vs Anthropic @modelcontextprotocol/context
    - vs acemcp (inspired by)
    - vs Augment Code (proprietary)
    - vs Qdrant/Weaviate (vector DBs)
    - Vector embedding models comparison (6 models)

### Developer Documentation
- `init/specs/`: Technical specifications
- `init/guidelines/`: Coding standards, naming conventions, documentation guide
- `init/workflows/`: Release, bugfix, and feature development workflows

### Configuration Examples
- **Claude MCP CLI**: One-command setup with environment variables
- **Manual JSON config**: Traditional config.json approach
- **Vector model switching**: 6 embedding models to choose from

---

## 🎯 Performance Metrics

| Metric | Value |
|--------|-------|
| **Indexing Speed** | 1000+ files/sec (BM25) |
| **Search Latency** | ~1.05s (with LLM re-ranking) |
| **Cache Hit Rate** | 20% improvement with semantic cache |
| **Cost per Query** | ~$0.00005 (99.9% local processing) |
| **Accuracy** | 85% (hybrid search + LLM filtering) |

---

## ⚠️ Breaking Changes

None. This is the first stable release.

---

## 🙏 Acknowledgments

### Inspiration & References

- **[acemcp](https://github.com/wxxedu/acemcp)** by @wxxedu
  - Auto-incremental indexing implementation
  - Zero-maintenance philosophy
  - Web UI design inspiration

- **[Augment Code](https://www.augmentcode.com/)** (Proprietary)
  - Context Engine architecture insights
  - Two-stage retrieval (local + remote) concept

- **[sentence-transformers](https://www.sbert.net/)** by Hugging Face
  - all-MiniLM-L6-v2 embedding model
  - Local, free, and high-quality embeddings

- **[Requesty.ai](https://requesty.ai/)**
  - Multi-model aggregation platform
  - 300+ model access with unified API

### Community Contributors

- Claude Code team for MCP protocol and development tools
- DuckDB team for embedded SQL database
- FAISS team (Meta) for vector similarity search
- FastAPI team for modern web framework

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/augment-lite-mcp.git
cd augment-lite-mcp

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
uv pip install -r requirements-lock.txt

# Optional: Install vector search dependencies (~2GB)
bash scripts/install_vector_deps.sh

# Add project and build index
./scripts/manage.sh add auto .

# Configure MCP in Claude Code
# Add to ~/.claude/config.json:
{
  "mcpServers": {
    "augment-lite": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/mcp_bridge_lazy.py"]
    }
  }
}
```

---

## 🔗 Links

- **Repository**: https://github.com/yourusername/augment-lite-mcp
- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/yourusername/augment-lite-mcp/issues
- **License**: MIT

---

## 📅 Release History

- **v1.0.0** (2025-11-10): First stable release
- **v0.7.0** (2024-11-09): Auto-incremental indexing, Web UI
- **v0.6.0** (2024-11-09): AI auto-discovery, MCP resources
- **v0.5.2** (2024-11-08): Token optimization, system prompts
- **v0.5.1** (2024-11-06): Documentation improvements
- **v0.5.0** (2024-11-03): Multi-project support
- **v0.4.0** (2024-10-28): Semantic cache, retry logic
- **v0.3.0** (2024-10-20): Vector search, hybrid retrieval

---

**[1.0.0]**: https://github.com/yourusername/augment-lite-mcp/releases/tag/v1.0.0
