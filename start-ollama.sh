#!/bin/sh

set -e

echo "Starting Ollama server..."
ollama serve &

echo "Waiting for Ollama to be ready..."
sleep 5

echo "Pulling model..."
OLLAMA_NO_TUI=1 ollama pull tinyllama || true

echo "Ollama ready"
wait
