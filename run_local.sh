#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/tharun/resume-tool"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing Python virtual environment at .venv."
  echo "Run ./setup.sh first."
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Building frontend assets..."
npm run build

export FLASK_PORT="${FLASK_PORT:-5001}"

echo "Starting app at http://127.0.0.1:${FLASK_PORT}"
exec .venv/bin/python app.py
