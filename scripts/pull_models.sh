#!/bin/sh
# Pull required Ollama models on first run.
# This script runs once in the ollama_init container.
set -e

OLLAMA_HOST="${OLLAMA_HOST:-ollama:11434}"
LLM_MODEL="${OLLAMA_LLM_MODEL:-qwen2.5:7b}"
EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"

echo "==> Waiting for Ollama to be ready at $OLLAMA_HOST..."
until curl -sf "http://$OLLAMA_HOST/api/tags" > /dev/null 2>&1; do
  sleep 3
done
echo "==> Ollama is ready."

echo "==> Pulling LLM model: $LLM_MODEL"
curl -X POST "http://$OLLAMA_HOST/api/pull" \
     -H "Content-Type: application/json" \
     -d "{\"name\": \"$LLM_MODEL\"}" \
     --no-progress-meter \
     | while IFS= read -r line; do echo "$line"; done

echo "==> Pulling embedding model: $EMBED_MODEL"
curl -X POST "http://$OLLAMA_HOST/api/pull" \
     -H "Content-Type: application/json" \
     -d "{\"name\": \"$EMBED_MODEL\"}" \
     --no-progress-meter \
     | while IFS= read -r line; do echo "$line"; done

echo "==> All models pulled successfully."
