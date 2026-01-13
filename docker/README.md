# Docker 使用
```bash
docker build -t augment-lite-mcp:1.1.0 .
docker run --rm -it \
  -e AUGMENT_DB_DIR=/app/data \
  -e GLM_API_KEY=your-key \
  -e MINIMAX_API_KEY=your-key \
  -e REQUESTY_API_KEY=sk-... \
  augment-lite-mcp:1.1.0
```
> 伺服器是 stdio 服務，通常由 Claude Code CLI fork 啟動；容器模式請用 `docker exec -it` 方式與之互動或改為 TCP/Unix socket（需要你自行擴充）。
