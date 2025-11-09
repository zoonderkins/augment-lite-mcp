# Docker 使用
```bash
docker build -t augment-lite-mcp:0.2.1 .
docker run --rm -it -e AUGMENT_DB_DIR=/app/data       -e KIMI_LOCAL_KEY=dummy -e GLM_LOCAL_KEY=dummy -e MINIMAXI_LOCAL_KEY=dummy       -e REQUESTY_API_KEY=sk-...       -p 7000:7000 augment-lite-mcp:0.2.1
```
> 伺服器是 stdio 服務，通常由 Claude Code CLI fork 啟動；容器模式請用 `docker exec -it` 方式與之互動或改為 TCP/Unix socket（需要你自行擴充）。