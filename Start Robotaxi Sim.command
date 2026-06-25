#!/bin/bash
# Double-click to start Robotaxi Sim in Terminal (macOS).
# Binds 127.0.0.1:8001 and 127.0.0.1:5174 only — does not touch logistics-sim (8000/5173).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export ROBOTAXI_BACKEND_PORT="${ROBOTAXI_BACKEND_PORT:-8001}"
export ROBOTAXI_FRONTEND_PORT="${ROBOTAXI_FRONTEND_PORT:-5174}"
export ROBOTAXI_CITY=austin

clear
echo "Robotaxi Sim — local launcher"
echo "  UI:      http://127.0.0.1:${ROBOTAXI_FRONTEND_PORT}"
echo "  Backend: http://127.0.0.1:${ROBOTAXI_BACKEND_PORT}"
echo ""
echo "Only prior Robotaxi processes are stopped; other apps on different ports are left alone."
echo ""

if ! ./scripts/start-local.sh --foreground; then
  echo ""
  echo "Robotaxi Sim exited with an error. See messages above or .local/logs/."
  read -r -p "Press Enter to close this window…"
  exit 1
fi
