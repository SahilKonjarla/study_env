#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${POMODORO_BACKEND_URL:-}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

FRONTEND_PID=""
CLEANED_UP=0

cleanup() {
  if [[ "$CLEANED_UP" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  echo
  echo "Resetting Pi backend and cleaning up Pomodoro controls..."
  if [[ -n "$API_URL" ]]; then
    curl -fsS "$API_URL/reset" >/dev/null 2>&1 || true
  fi

  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi

  wait >/dev/null 2>&1 || true
}

trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

if [[ -z "$API_URL" ]]; then
  echo "Set the Pi backend URL first:"
  echo "  POMODORO_BACKEND_URL=http://PI_IP_ADDRESS:8000 scripts/run_mac_for_pi.sh"
  exit 1
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies. Run:"
  echo "  cd frontend && npm install"
  exit 1
fi

echo "Starting frontend at http://localhost:5173"
VITE_API_BASE_URL="$API_URL" npm --prefix "$ROOT/frontend" run dev &
FRONTEND_PID="$!"

sleep 2

echo "Starting macOS agent against $API_URL. Press Ctrl+C here to reset and stop."
sudo POMODORO_BACKEND_URL="$API_URL" "$PYTHON_BIN" "$ROOT/agent.py"
