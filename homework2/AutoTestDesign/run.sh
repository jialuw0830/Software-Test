#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

PORT="${PORT:-8501}"
streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port "$PORT" \
  --browser.gatherUsageStats false
