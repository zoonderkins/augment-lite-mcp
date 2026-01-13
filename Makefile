# ============================================================
# augment-lite-mcp Makefile
# Version: 1.1.0
# ============================================================

VERSION := 1.1.0

.PHONY: help venv install install-lock install-vector index add-project list-projects \
        activate-project rebuild-project build-vector-index rebuild-vector-index \
        clean-semantic-cache run-mcp test test-unit test-api test-integration \
        test-quick test-all lint format clean clean-all backup \
        check-proxy manage docker-build docker-run version status

# ============================================================
# 幫助
# ============================================================

help:
	@echo "augment-lite-mcp v$(VERSION) Makefile 命令："
	@echo ""
	@echo "版本資訊："
	@echo "  make version                              - 顯示版本號"
	@echo "  make status                               - 顯示系統狀態"
	@echo ""
	@echo "環境設置："
	@echo "  make venv                                 - 創建虛擬環境"
	@echo "  make install                              - 安裝基礎依賴（requirements.txt）"
	@echo "  make install-lock                         - 安裝依賴（requirements-lock.txt）"
	@echo "  make install-vector                       - 安裝向量檢索依賴（v0.4.0 新增）"
	@echo ""
	@echo "專案管理："
	@echo "  make add-project NAME=<name> PATH=<path>  - 新增專案"
	@echo "  make list-projects                        - 列出所有專案"
	@echo "  make activate-project NAME=<name>         - 啟用專案"
	@echo "  make rebuild-project NAME=<name>          - 重建專案索引"
	@echo ""
	@echo "向量檢索（v0.4.0 新增）："
	@echo "  make build-vector-index NAME=<name>       - 為專案建立向量索引"
	@echo "  make rebuild-vector-index NAME=<name>     - 重建專案向量索引"
	@echo "  make clean-semantic-cache                 - 清理語義快取"
	@echo ""
	@echo "運行："
	@echo "  make run-mcp                              - 運行 MCP stdio server"
	@echo "  make manage                               - 運行互動式管理工具"
	@echo ""
	@echo "測試："
	@echo "  make test                                 - 運行所有測試（完整測試）"
	@echo "  make test-quick                           - 快速測試（僅單元測試，約1分鐘）"
	@echo "  make test-unit                            - 單元測試（無需 API key）"
	@echo "  make test-api                             - API 測試（需要索引）"
	@echo "  make test-integration                     - 整合測試（需要 Proxy）"
	@echo ""
	@echo "開發："
	@echo "  make lint                                 - 代碼檢查"
	@echo "  make format                               - 代碼格式化"
	@echo ""
	@echo "清理："
	@echo "  make clean                                - 清理快取和臨時檔案"
	@echo "  make clean-all                            - 清理所有資料（危險）"
	@echo ""
	@echo "工具："
	@echo "  make backup                               - 備份資料"
	@echo "  make check-proxy                          - 檢查本地 Proxy 狀態"
	@echo ""
	@echo "Docker："
	@echo "  make docker-build                         - 建立 Docker 映像"
	@echo "  make docker-run                           - 運行 Docker 容器"

# ============================================================
# 環境設置
# ============================================================

venv:
	python3 -m venv .venv
	@echo "✅ 虛擬環境已創建"
	@echo "請執行: source .venv/bin/activate"

install:
	uv pip install --upgrade pip
	uv pip install -r requirements.txt
	@echo "✅ 基礎依賴已安裝（requirements.txt）"
	@echo ""
	@echo "💡 提示：如需啟用向量檢索功能，請執行："
	@echo "   make install-vector"

install-lock:
	uv pip install --upgrade pip
	uv pip install -r requirements-lock.txt
	@echo "✅ 依賴已安裝（requirements-lock.txt）"

install-vector:
	@echo "安裝向量檢索依賴..."
	@if [ ! -f ".venv/bin/activate" ]; then \
		echo "❌ 錯誤: 虛擬環境不存在，請先執行: make venv"; \
		exit 1; \
	fi
	@bash scripts/install_vector_deps.sh
	@echo "✅ 向量檢索依賴已安裝"

# ============================================================
# 專案管理
# ============================================================

add-project:
	@if [ -z "$(NAME)" ] || [ -z "$(PATH)" ]; then \
		echo "❌ 錯誤: 請提供 NAME 和 PATH"; \
		echo "用法: make add-project NAME=miceai PATH=/path/to/project"; \
		exit 1; \
	fi
	.venv/bin/python retrieval/multi_project.py add $(NAME) $(PATH)

list-projects:
	.venv/bin/python retrieval/multi_project.py list

activate-project:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ 錯誤: 請提供 NAME"; \
		echo "用法: make activate-project NAME=miceai"; \
		exit 1; \
	fi
	.venv/bin/python retrieval/multi_project.py activate $(NAME)

rebuild-project:
	@if [ -z "$(NAME)" ]; then \
		echo "重建所有專案..."; \
		.venv/bin/python retrieval/multi_project.py rebuild; \
	else \
		echo "重建專案: $(NAME)"; \
		.venv/bin/python retrieval/multi_project.py rebuild $(NAME); \
	fi

# ============================================================
# 向量檢索（v0.4.0 新增）
# ============================================================

build-vector-index:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ 錯誤: 請提供專案名稱"; \
		echo "用法: make build-vector-index NAME=myproject"; \
		exit 1; \
	fi
	@echo "為專案 $(NAME) 建立向量索引..."
	.venv/bin/python retrieval/build_vector_index.py $(NAME)

rebuild-vector-index:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ 錯誤: 請提供專案名稱"; \
		echo "用法: make rebuild-vector-index NAME=myproject"; \
		exit 1; \
	fi
	@echo "重建專案 $(NAME) 的向量索引..."
	@rm -f data/vector_index_$(NAME).faiss data/vector_metadata_$(NAME).json
	.venv/bin/python retrieval/build_vector_index.py $(NAME)

clean-semantic-cache:
	@echo "清理語義快取..."
	@rm -f data/semantic_cache.sqlite
	@echo "✅ 語義快取已清理"

# ============================================================
# 運行
# ============================================================

run-mcp:
	@echo "運行 MCP stdio server..."
	@echo "按 Ctrl+C 停止"
	.venv/bin/python mcp_bridge_lazy.py

manage:
	./scripts/manage.sh

# ============================================================
# 開發
# ============================================================

# ============================================================
# 測試
# ============================================================

test: test-all

test-quick:
	@echo "🚀 快速測試模式（僅單元測試）"
	.venv/bin/python tests/run_all_tests.py --quick

test-unit:
	@echo "🧪 運行單元測試"
	.venv/bin/python tests/run_all_tests.py --suite unit

test-api:
	@echo "🧪 運行 API 測試"
	.venv/bin/python tests/run_all_tests.py --suite api

test-integration:
	@echo "🧪 運行整合測試"
	.venv/bin/python tests/run_all_tests.py --suite integration

test-all:
	@echo "🧪 運行所有測試"
	.venv/bin/python tests/run_all_tests.py --suite all

# ============================================================
# 代碼質量
# ============================================================

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .

# ============================================================
# 清理
# ============================================================

clean:
	@echo "清理快取和臨時檔案..."
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -f data/response_cache.sqlite data/semantic_cache.sqlite
	@echo "✅ 清理完成"

clean-all:
	@echo "⚠️  這將刪除所有資料！"
	@read -p "確定要繼續嗎？請輸入 'DELETE' 確認: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		rm -rf .venv data/*.sqlite data/*.duckdb data/*.jsonl data/*.faiss data/*.json; \
		echo "✅ 所有資料已刪除"; \
	else \
		echo "❌ 取消清理"; \
	fi

# ============================================================
# 工具
# ============================================================

backup:
	./scripts/manage.sh backup

check-proxy:
	./scripts/manage.sh check-proxy

# ============================================================
# Docker
# ============================================================

docker-build:
	docker build -t augment-lite-mcp:$(VERSION) -t augment-lite-mcp:latest .

docker-run:
	docker run -i --rm \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/config:/app/config \
		-e AUGMENT_DB_DIR=/app/data \
		-e GLM_API_KEY=$(GLM_API_KEY) \
		-e MINIMAX_API_KEY=$(MINIMAX_API_KEY) \
		-e REQUESTY_API_KEY=$(REQUESTY_API_KEY) \
		augment-lite-mcp:$(VERSION)

# ============================================================
# 版本資訊
# ============================================================

version:
	@echo "augment-lite-mcp version: $(VERSION)"
	@cat VERSION

status:
	@echo "========================================="
	@echo "augment-lite-mcp v$(VERSION) 系統狀態"
	@echo "========================================="
	@echo ""
	@echo "📦 虛擬環境："
	@if [ -d ".venv" ]; then \
		echo "  ✅ 已創建 (.venv)"; \
	else \
		echo "  ❌ 未創建 - 請執行: make venv"; \
	fi
	@echo ""
	@echo "📚 依賴套件："
	@if [ -f ".venv/bin/python" ]; then \
		if .venv/bin/python -c "import torch" 2>/dev/null; then \
			echo "  ✅ PyTorch: $$(.venv/bin/python -c 'import torch; print(torch.__version__)')"; \
		else \
			echo "  ❌ PyTorch 未安裝"; \
		fi; \
		if .venv/bin/python -c "import faiss" 2>/dev/null; then \
			echo "  ✅ FAISS 已安裝"; \
		else \
			echo "  ❌ FAISS 未安裝"; \
		fi; \
		if .venv/bin/python -c "import sentence_transformers" 2>/dev/null; then \
			echo "  ✅ sentence-transformers 已安裝"; \
		else \
			echo "  ❌ sentence-transformers 未安裝"; \
		fi; \
		if .venv/bin/python -c "import numpy; print('  ✅ NumPy:', numpy.__version__)" 2>/dev/null; then \
			:; \
		else \
			echo "  ❌ NumPy 未安裝"; \
		fi; \
	else \
		echo "  ❌ 虛擬環境未創建"; \
	fi
	@echo ""
	@echo "📁 專案資料："
	@if [ -f "data/projects.json" ]; then \
		echo "  專案數量: $$(cat data/projects.json | grep -o '"name"' | wc -l | tr -d ' ')"; \
	else \
		echo "  ❌ 無專案資料"; \
	fi
	@echo ""
	@echo "🗄️  資料檔案："
	@echo "  BM25 索引: $$(ls -1 data/*.duckdb 2>/dev/null | wc -l | tr -d ' ') 個"
	@echo "  向量索引: $$(ls -1 data/vector_index_*.faiss 2>/dev/null | wc -l | tr -d ' ') 個"
	@echo "  語義快取: $$(if [ -f 'data/semantic_cache.sqlite' ]; then echo '已啟用'; else echo '未啟用'; fi)"
	@echo "  回應快取: $$(if [ -f 'data/response_cache.sqlite' ]; then echo '已啟用'; else echo '未啟用'; fi)"
	@echo ""
	@echo "========================================="
