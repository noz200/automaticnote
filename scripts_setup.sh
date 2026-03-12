#!/usr/bin/env bash
set -euo pipefail

# Windows対応: venv作成とactivate
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  python -m venv .venv
  source .venv/Scripts/activate
else
  python3 -m venv .venv
  source .venv/bin/activate
fi

pip install -r requirements.txt
playwright install chromium

echo "[INFO] virtualenv ready: .venv"
echo "[INFO] This project can run news collection + article generation with stdlib only."
echo "[INFO] For note auto-post, install playwright manually when your network allows:"
echo "       pip install playwright && python -m playwright install chromium"
