#!/usr/bin/env bash
# Run from the project root: bash src/utils/scripts/loading_agents.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Find project root by searching upward for pyproject.toml — works whether the
# script is run from src/utils/scripts/ or directly from the project root.
PROJECT_ROOT="$SCRIPT_DIR"
while [[ "$PROJECT_ROOT" != "/" && ! -f "$PROJECT_ROOT/pyproject.toml" ]]; do
  PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
  echo "ERROR: could not locate project root (no pyproject.toml found)" >&2
  exit 1
fi
PID_FILE="$SCRIPT_DIR/agents.pids"
LOG_FILE="$SCRIPT_DIR/agents.log"       # shared startup/shutdown summary
LOG_DIR="$SCRIPT_DIR/logs"              # per-agent log files
mkdir -p "$LOG_DIR"
cd "$PROJECT_ROOT"

# Auto-shutdown any previously running agents before starting fresh
if [[ -f "$SCRIPT_DIR/shutdown_agents.sh" ]]; then
  bash "$SCRIPT_DIR/shutdown_agents.sh"
fi

> "$PID_FILE"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

create_db_tables() {
  log "[CREATE] Creating database tables..."
bash "$SCRIPT_DIR/create_tables.sh" >> "$LOG_FILE" 2>&1 \
    && log "[CREATE] Database tables created successfully." \
    || log "[CREATE] WARNING: failed to create database tables — check $LOG_FILE for details."
}

register() {
  local name="$1"
  local port="$2"
  shift 2
  # Derive a safe filename from the agent name: lowercase + underscores
  local slug
  slug="$(echo "$name" | tr '[:upper:] ' '[:lower:]_')"
  local agent_log="$LOG_DIR/${slug}.log"
  log "[STARTUP] Starting $name on port $port  →  log: logs/${slug}.log"
  "$@" >> "$agent_log" 2>&1 &
  local pid=$!
  echo "$pid:$name:$port" >> "$PID_FILE"
  log "[STARTUP] $name started  |  PID=$pid  PORT=$port"
}

# MCP server must be up before agents start receiving requests that need it
register "MCP Server"              8000  python -m uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
# agent card embedding generation needs ~2s per card (API + cooldown) × ~9 cards
sleep 20  # give the MCP server time to build embeddings before agents come online

register "Aspectuator Agent"       10101 python -m agents --agent-card agent_cards/aspectuator_agent.json        --port 10101 --host localhost
register "Content Strategist"      10103 python -m agents --agent-card agent_cards/content_strategist_agent.json --port 10103 --host localhost
register "Deep Research Agent"     10105 python -m agents --agent-card agent_cards/deep_research_agent.json      --port 10105 --host localhost
register "Image Generation Agent"  10107 python -m agents --agent-card agent_cards/image_generation_agent.json   --port 10107 --host localhost
register "LinkedIn Post Generator" 10109 python -m agents --agent-card agent_cards/linkedin_post_writer_agent.json --port 10109 --host localhost
register "Marketing Assistant"     10111 python -m agents --agent-card agent_cards/marketing_assistant_agent.json --port 10111 --host localhost
register "Orchestrator Agent"      10113 python -m agents --agent-card agent_cards/orchestrator_agent.json       --port 10113 --host localhost
register "Planner Agent"           10115 python -m agents --agent-card agent_cards/planner_agent.json            --port 10115 --host localhost
register "SEO Blog Writer"         10117 python -m agents --agent-card agent_cards/seo_blog_writer_agent.json    --port 10117 --host localhost
register "Whitepaper Writer"       10119 python -m agents --agent-card agent_cards/whitepaper_writer_agent.json --port 10119 --host localhost

log "[STARTUP] All $(wc -l < "$PID_FILE") agents launched. PIDs written to $PID_FILE"
# python -m create_tables >> "$LOG_FILE" 2>&1 \
#   && log "[STARTUP] Database tables created successfully." \
#   || log "[STARTUP] WARNING: failed to create database tables — check $LOG_FILE for details."
bash "$SCRIPT_DIR/create_tables.sh" >> "$LOG_FILE" 2>&1 \
    && log "[STARTUP] Database tables created successfully." \
    || log "[STARTUP] WARNING: failed to create database tables — check $LOG_FILE for details."