#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Build a tiny demo index
python retrieval/build_index.py --root "$ROOT/examples/project"

# Env (fill Requesty if you plan to use GPT-5/Gemini routes)
export AUGMENT_DB_DIR="$ROOT/data"
export KIMI_LOCAL_KEY="dummy"
export GLM_LOCAL_KEY="dummy"
export MINIMAXI_LOCAL_KEY="dummy"
# export REQUESTY_API_KEY="sk-..."

echo "Starting augment-lite-mcp server (stdio). Press Ctrl+C to stop."
python server.py