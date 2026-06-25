#!/usr/bin/env bash
# Stop Robotaxi Sim local backend (:8001) and frontend (:5174).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/.local/robotaxi.pids"
BACKEND_PORT="${ROBOTAXI_BACKEND_PORT:-8001}"
FRONTEND_PORT="${ROBOTAXI_FRONTEND_PORT:-5174}"

log() { printf '[robotaxi] %s\n' "$*"; }

if [[ -f "$PID_FILE" ]]; then
  while read -r pid; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      log "Stopping pid $pid"
      kill "$pid" 2>/dev/null || true
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  for pid in $pids; do
    log "Stopping listener on port $port (pid $pid)"
    kill "$pid" 2>/dev/null || true
  done
done

log "Stopped."
