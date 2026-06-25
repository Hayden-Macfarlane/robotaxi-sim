#!/usr/bin/env bash
# Start Robotaxi Sim locally: API :8001 + UI :5174 (isolated from logistics-sim 8000/5173).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${ROBOTAXI_BACKEND_PORT:-8001}"
FRONTEND_PORT="${ROBOTAXI_FRONTEND_PORT:-5174}"
LOG_DIR="$ROOT/.local/logs"
PID_FILE="$ROOT/.local/robotaxi.pids"
mkdir -p "$LOG_DIR" "$(dirname "$PID_FILE")"

BACKEND_PID=""
FRONTEND_PID=""

log() { printf '[robotaxi] %s\n' "$*"; }

cleanup() {
  log "Shutting down…"
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
}

trap cleanup EXIT INT TERM

stop_saved_pids() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 0
  fi
  while read -r pid; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      log "Stopping previous Robotaxi process (pid $pid)"
      kill "$pid" 2>/dev/null || true
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  sleep 0.3
}

ensure_port_for_robotaxi() {
  local port="$1"
  local label="$2"
  local pattern="$3"
  local pids
  pids="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  for pid in $pids; do
    local cmd
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if echo "$cmd" | grep -qE "$pattern"; then
      log "Freeing port $port from previous Robotaxi process (pid $pid)"
      kill "$pid" 2>/dev/null || true
    else
      log "ERROR: Port $port ($label) is in use by another program (pid $pid)."
      log "  $cmd"
      log "Robotaxi uses $BACKEND_PORT/$FRONTEND_PORT so logistics-sim (8000/5173) stays separate."
      log "Stop the other program or set ROBOTAXI_BACKEND_PORT / ROBOTAXI_FRONTEND_PORT."
      exit 1
    fi
  done
  sleep 0.3
}

ensure_python_env() {
  if [[ ! -x "$ROOT/venv/bin/python" ]]; then
    log "Creating Python 3.14 venv…"
    python3.14 -m venv "$ROOT/venv"
  fi
  if ! "$ROOT/venv/bin/python" -c "import uvicorn, fastapi" 2>/dev/null; then
    log "Installing Python dependencies…"
    "$ROOT/venv/bin/pip" install -q -e "$ROOT"
  fi
  if [[ ! -f "$ROOT/data/cities/austin/nodes.json" ]]; then
    log "Building Austin city graph…"
    "$ROOT/venv/bin/python" "$ROOT/scripts/build_city_graph.py"
  fi
}

ensure_frontend_deps() {
  if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
    log "Installing frontend dependencies…"
    (cd "$ROOT/frontend" && npm install)
  fi
}

stop_saved_pids
ensure_port_for_robotaxi "$BACKEND_PORT" "backend" "api\.server:app"
ensure_port_for_robotaxi "$FRONTEND_PORT" "frontend" "vite|robotaxi-sim/frontend"
ensure_python_env
ensure_frontend_deps

log "Starting backend on 127.0.0.1:$BACKEND_PORT"
"$ROOT/venv/bin/uvicorn" api.server:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload \
  >"$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

log "Starting frontend on 127.0.0.1:$FRONTEND_PORT"
(cd "$ROOT/frontend" && npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1) \
  >"$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

printf '%s\n' "$BACKEND_PID" "$FRONTEND_PID" >"$PID_FILE"

sleep 2
UI_URL="http://127.0.0.1:$FRONTEND_PORT"
log "Robotaxi Sim → $UI_URL"
log "Backend log: $LOG_DIR/backend.log"
log "Frontend log: $LOG_DIR/frontend.log"
log "Press Ctrl+C in this window to stop."

if command -v open >/dev/null 2>&1; then
  open "$UI_URL"
fi

wait "$BACKEND_PID" "$FRONTEND_PID"
