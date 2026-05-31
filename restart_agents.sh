#!/usr/bin/env bash
# Run from project root: bash restart_agents.sh
#
# Restarts all agents by running shutdown first, then loading.
# The loading script also calls shutdown internally — that second
# call is a harmless no-op since everything is already down.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Locate project root ──────────────────────────────────────────────────────────
PROJECT_ROOT="$SCRIPT_DIR"
while [[ "$PROJECT_ROOT" != "/" && ! -f "$PROJECT_ROOT/pyproject.toml" ]]; do
  PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
  echo "ERROR: could not locate project root (no pyproject.toml found)" >&2
  exit 1
fi

# Path to the scripts directory and the agent-management scripts
SCRIPTS_DIR="$PROJECT_ROOT/src/utils/scripts"
SHUTDOWN_SCRIPT="$SCRIPTS_DIR/shutdown_agents.sh"
LOADING_SCRIPT="$SCRIPTS_DIR/loading_agents.sh"
LOG_FILE="$SCRIPTS_DIR/agents.log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

log "============================================================"
log "[RESTART]  Restarting all agents"
log "============================================================"

# ── Phase 1: Shutdown ───────────────────────────────────────────────────────────
log "[RESTART] Phase 1/2: Stopping all agents..."
if [[ -f "$SHUTDOWN_SCRIPT" ]]; then
  bash "$SHUTDOWN_SCRIPT"
  log "[RESTART] Shutdown complete."
else
  log "[RESTART] ERROR: shutdown_agents.sh not found at $SCRIPTS_DIR"
  exit 1
fi

# ── Phase 2: Startup ────────────────────────────────────────────────────────────
log "[RESTART] Phase 2/2: Starting all agents..."
if [[ -f "$LOADING_SCRIPT" ]]; then
  bash "$LOADING_SCRIPT"
  log "[RESTART] Startup complete."
else
  log "[RESTART] ERROR: loading_agents.sh not found at $SCRIPTS_DIR"
  exit 1
fi

log "============================================================"
log "[RESTART] All agents restarted successfully."
log "============================================================"
