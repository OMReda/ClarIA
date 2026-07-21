#!/bin/sh
# ollama-entrypoint.sh
# Starts Ollama server in the background, pulls the model, then keeps the
# server in the foreground. This ensures the model is ready before the
# worker starts sending requests.

set -e

MODEL="${OLLAMA_MODEL:-llama3}"

echo "[ollama-entrypoint] Starting Ollama server..."
ollama serve &
SERVER_PID=$!

# Wait for server to be responsive
echo "[ollama-entrypoint] Waiting for Ollama to be ready..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 1
done

echo "[ollama-entrypoint] Pulling model: ${MODEL}"
ollama pull "${MODEL}"
echo "[ollama-entrypoint] Model ready: ${MODEL}"

# Keep the server in the foreground
wait $SERVER_PID
