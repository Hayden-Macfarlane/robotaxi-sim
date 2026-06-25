#!/usr/bin/env bash
# Restart backend/frontend without killing the Start Robotaxi Sim.command terminal.
# The foreground launcher supervises child processes and will restart them automatically.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/scripts/stop-local.sh"
