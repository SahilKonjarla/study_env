#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${POMODORO_BACKEND_URL:-http://127.0.0.1:8000}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
UVICORN_BIN="${UVICORN_BIN:-$ROOT/.venv/bin/uvicorn}"

BACKEND_PID=""
FRONTEND_PID=""
CLEANED_UP=0

cleanup() {
  if [[ "$CLEANED_UP" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  echo
  echo "Cleaning up Pomodoro controls..."
  curl -fsS "$API_URL/reset" >/dev/null 2>&1 || true

  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi

  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  wait >/dev/null 2>&1 || true
}

trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

if [[ ! -x "$PYTHON_BIN" || ! -x "$UVICORN_BIN" ]]; then
  echo "Missing backend venv. Run:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies. Run:"
  echo "  cd frontend && npm install"
  exit 1
fi

cd "$ROOT"

echo "Starting backend at $API_URL"
"$UVICORN_BIN" main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID="$!"

sleep 2

echo "Starting frontend at http://localhost:5173"
VITE_API_BASE_URL="$API_URL" npm --prefix "$ROOT/frontend" run dev &
FRONTEND_PID="$!"

sleep 2

echo "Checking macOS Focus Shortcuts..."
if ! "$PYTHON_BIN" "$ROOT/agent.py" --check-shortcuts; then
  echo "Focus Shortcuts are missing or named differently."
  echo "Run scripts/setup_focus_shortcuts.sh to open the setup pages."
  echo "The agent will still run and enforce website blocking."
fi

echo "Starting macOS agent. Press Ctrl+C here to reset and stop everything."
sudo POMODORO_BACKEND_URL="$API_URL" "$PYTHON_BIN" "$ROOT/agent.py"
