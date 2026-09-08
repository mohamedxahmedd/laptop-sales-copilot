#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo ""
echo "Laptop Sales Copilot is starting..."
echo "Primary AI: ITI DeepSeek V3.2. The app is also deployment-ready."
echo ""
if command -v ollama >/dev/null 2>&1; then
  (ollama serve >/tmp/laptop-sales-copilot-ollama.log 2>&1 &) || true
fi
streamlit run app.py
