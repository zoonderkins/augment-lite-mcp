# ============================================================
# augment-lite-mcp Dockerfile
# Version: 1.3.2
# 支援 MCP stdio 通訊
# ============================================================

FROM python:3.12-slim

LABEL version="1.3.2"
LABEL description="augment-lite-mcp: Local-first AI coding assistant with MCP support"
LABEL maintainer="your-email@example.com"

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴和 uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# 複製依賴檔案
COPY requirements-lock.txt .

# 安裝 Python 依賴
RUN uv pip install --system --no-cache -r requirements-lock.txt

# 複製專案檔案
COPY . .

# 創建資料目錄
RUN mkdir -p /app/data

# 設定環境變數
ENV AUGMENT_DB_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# 暴露 stdio（MCP 使用 stdin/stdout）
# 不需要 EXPOSE，因為使用 stdio 而非網路端口

# 健康檢查（可選，檢查資料目錄）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test -d /app/data || exit 1

# 運行 MCP stdio server
# 使用 -u 確保 stdout 不被緩衝
ENTRYPOINT ["python", "-u", "mcp_bridge_lazy.py"]

