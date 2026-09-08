#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-qwen3:30b-instruct}"

if ! command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "Ollama is not installed."
  echo "Install Ollama first from: https://ollama.com/download"
  echo "Then run this file again."
  echo ""
  exit 1
fi

echo ""
echo "Starting Ollama (if needed)..."
(ollama serve >/tmp/laptop-sales-copilot-ollama.log 2>&1 &) || true
sleep 2

echo ""
echo "Downloading the recommended FREE local model:"
echo "  $MODEL"
echo ""
ollama pull "$MODEL"

echo ""
echo "Done. Local AI is ready."
echo "You can now run ./setup_and_run.command"
