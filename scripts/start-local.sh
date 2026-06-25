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
DETACH=false
SHUTDOWN_REQUESTED=false
OPENED_BROWSER=false

if [[ "${1:-}" == "--detach" || "${ROBOTAXI_DETACH:-}" == "1" ]]; then
  DETACH=true
elif [[ "${1:-}" == "--foreground" ]]; then
  DETACH=false
elif [[ ! -t 1 ]]; then
  DETACH=true
fi

log() { printf '[robotaxi] %s\n' "$*"; }

cleanup() {
  SHUTDOWN_REQUESTED=true
  log "Shutting down…"
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
}

trap cleanup INT TERM

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

start_services() {
  BACKEND_PID=""
  FRONTEND_PID=""

  log "Starting backend on 127.0.0.1:$BACKEND_PORT"
  if $DETACH; then
    nohup "$ROOT/venv/bin/uvicorn" api.server:app --host 127.0.0.1 --port "$BACKEND_PORT" \
      >>"$LOG_DIR/backend.log" 2>&1 &
  else
    "$ROOT/venv/bin/uvicorn" api.server:app --host 127.0.0.1 --port "$BACKEND_PORT" \
      >>"$LOG_DIR/backend.log" 2>&1 &
  fi
  BACKEND_PID=$!

  log "Starting frontend on 127.0.0.1:$FRONTEND_PORT"
  if $DETACH; then
    nohup bash -c "cd \"$ROOT/frontend\" && npm run dev -- --port \"$FRONTEND_PORT\" --host 127.0.0.1" \
      >>"$LOG_DIR/frontend.log" 2>&1 &
  else
    bash -c "cd \"$ROOT/frontend\" && npm run dev -- --port \"$FRONTEND_PORT\" --host 127.0.0.1" \
      >>"$LOG_DIR/frontend.log" 2>&1 &
  fi
  FRONTEND_PID=$!

  printf '%s\n' "$BACKEND_PID" "$FRONTEND_PID" >"$PID_FILE"
}

wait_for_ready() {
  local ui_url="http://127.0.0.1:$FRONTEND_PORT"
  local health_url="http://127.0.0.1:$BACKEND_PORT/health"

  sleep 2
  log "Waiting for backend to finish loading the city graph…"
  local waited=0
  for _ in $(seq 1 120); do
    if curl -sf "$health_url" 2>/dev/null | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
      log "Backend ready (${waited}s)"
      break
    fi
    waited=$((waited + 1))
    if (( waited % 5 == 0 )); then
      log "Still loading city graph (${waited}s)…"
    fi
    sleep 1
  done
  if (( waited >= 120 )); then
    log "WARNING: Backend not ready after 120s — check $LOG_DIR/backend.log"
  fi

  log "Waiting for frontend…"
  for _ in $(seq 1 30); do
    if curl -sf "$ui_url" -o /dev/null 2>/dev/null; then
      log "Frontend ready"
      break
    fi
    sleep 1
  done
  log "Robotaxi Sim → $ui_url"
  log "Backend log: $LOG_DIR/backend.log"
  log "Frontend log: $LOG_DIR/frontend.log"
}

# One-time setup before the supervisor loop.
stop_saved_pids
ensure_port_for_robotaxi "$BACKEND_PORT" "backend" "api\.server:app"
ensure_port_for_robotaxi "$FRONTEND_PORT" "frontend" "vite|robotaxi-sim/frontend"
ensure_python_env
ensure_frontend_deps

# Local dashboard always uses full Austin; pytest sets mini_austin in conftest only.
export ROBOTAXI_CITY=austin
log "City graph: $ROBOTAXI_CITY"

while ! $SHUTDOWN_REQUESTED; do
  start_services
  wait_for_ready

  if $DETACH; then
    log "Detached mode — services keep running after this script exits."
    log "Stop with: ./scripts/stop-local.sh"
    exit 0
  fi

  if ! $OPENED_BROWSER && command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:$FRONTEND_PORT"
    OPENED_BROWSER=true
  fi

  log "Running — Ctrl+C in this window to stop."
  log "If backend/frontend are restarted externally, this launcher will bring them back."

  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true

  if $SHUTDOWN_REQUESTED; then
    break
  fi

  log "Services stopped unexpectedly — restarting in 2s…"
  export ROBOTAXI_CITY=austin
  stop_saved_pids
  ensure_port_for_robotaxi "$BACKEND_PORT" "backend" "api\.server:app"
  ensure_port_for_robotaxi "$FRONTEND_PORT" "frontend" "vite|robotaxi-sim/frontend"
  sleep 2
done

cleanup
exit 0
