#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python -m venv .venv
source .venv/bin/activate
uv pip install --upgrade pip
uv pip install -r requirements.txt

# Build a tiny demo index
python retrieval/build_index.py --root "$ROOT/examples/project"

# Env (configure your API keys)
export AUGMENT_DB_DIR="$ROOT/data"
# export GLM_BASE_URL="http://127.0.0.1:8082/v1"
# export GLM_API_KEY="your-key"
# export MINIMAX_BASE_URL="http://127.0.0.1:8083/v1"
# export MINIMAX_API_KEY="your-key"
# export REQUESTY_API_KEY="sk-..."

echo "Starting augment-lite-mcp server (stdio). Press Ctrl+C to stop."
python -u mcp_bridge_lazy.py