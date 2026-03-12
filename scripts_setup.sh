#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate

echo "[INFO] virtualenv ready: .venv"
echo "[INFO] This project can run news collection + article generation with stdlib only."
echo "[INFO] For note auto-post, install playwright manually when your network allows:"
echo "       pip install playwright && python -m playwright install chromium"
