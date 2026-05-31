#!/usr/bin/env bash
# Run from anywhere: bash src/utils/scripts/shutdown_agents.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SRC_DIR="$PROJECT_DIR/src"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
PID_FILE="$SCRIPT_DIR/agents.pids"
LOG_FILE="$SCRIPT_DIR/agents.log"
AGENT_PORTS=(8000 10101 10103 10105 10107 10109 10111 10113 10115 10117)

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

stop_pid() {
  local pid="$1" name="$2" port="$3"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    log "[SHUTDOWN] Stopping $name  |  PID=$pid  PORT=$port"
  else
    log "[SHUTDOWN] $name (PID=$pid PORT=$port) was already stopped"
  fi
}

delete_db_tables() {
  log "[SHUTDOWN] Deleting database tables..."
  PYTHONPATH="$SRC_DIR" "$VENV_PYTHON" "$SRC_DIR/tools/postgres_tools.py" >> "$LOG_FILE" 2>&1 \
    && log "[SHUTDOWN] Database tables deleted." \
    || log "[SHUTDOWN] WARNING: failed to delete database tables — check $LOG_FILE for details."
}

force_kill_pid() {
  local pid="$1" name="$2" port="$3"
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null
    log "[SHUTDOWN] Force-killed $name  |  PID=$pid  PORT=$port"
  fi
}

# ── Primary path: PID file exists ────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
  log "[SHUTDOWN] Sending SIGTERM to all registered agents..."
  while IFS=: read -r pid name port; do
    [[ -z "$pid" ]] && continue
    stop_pid "$pid" "$name" "$port"
  done < "$PID_FILE"

  sleep 5

  STRAGGLERS=()
  while IFS=: read -r pid name port; do
    [[ -z "$pid" ]] && continue
    kill -0 "$pid" 2>/dev/null && STRAGGLERS+=("$pid:$name:$port")
  done < "$PID_FILE"

  if [[ ${#STRAGGLERS[@]} -gt 0 ]]; then
    log "[SHUTDOWN] Force-killing ${#STRAGGLERS[@]} straggler(s)..."
    for entry in "${STRAGGLERS[@]}"; do
      IFS=: read -r pid name port <<< "$entry"
      force_kill_pid "$pid" "$name" "$port"
    done
  fi

  FAILED=()
  while IFS=: read -r pid name port; do
    [[ -z "$pid" ]] && continue
    kill -0 "$pid" 2>/dev/null && FAILED+=("$name (PID=$pid)")
  done < "$PID_FILE"

  if [[ ${#FAILED[@]} -gt 0 ]]; then
    log "[SHUTDOWN] ERROR: failed to stop: ${FAILED[*]}"
    exit 1
  fi

  rm -f "$PID_FILE"
  log "[SHUTDOWN] All agents stopped successfully."
  delete_db_tables
  exit 0
fi

# ── Fallback path: no PID file — kill by port ────────────────────────────────
log "[SHUTDOWN] No PID file found — scanning agent ports for orphaned processes..."
found=0
for port in "${AGENT_PORTS[@]}"; do
  pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | sort -u)
  for pid in $pids; do
    name="port-$port process"
    stop_pid "$pid" "$name" "$port"
    found=$((found + 1))
  done
done

if [[ $found -eq 0 ]]; then
  log "[SHUTDOWN] No agent processes found on any port. Nothing to do."
  exit 0
fi

sleep 5

# Force-kill anything still alive on those ports
for port in "${AGENT_PORTS[@]}"; do
  pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | sort -u)
  for pid in $pids; do
    force_kill_pid "$pid" "port-$port process" "$port"
  done
done

# Final check
still_up=()
for port in "${AGENT_PORTS[@]}"; do
  pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | sort -u)
  for pid in $pids; do
    still_up+=("PID=$pid PORT=$port")
  done
done

if [[ ${#still_up[@]} -gt 0 ]]; then
  log "[SHUTDOWN] ERROR: could not stop: ${still_up[*]}"
  exit 1
fi

log "[SHUTDOWN] All agent processes stopped (fallback port-scan mode)."
delete_db_tables
