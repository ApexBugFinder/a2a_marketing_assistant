# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python / Poetry)

```bash
# Install dependencies
poetry install

# Run the combined MCP + Tools FastAPI server (port 8000)
poetry run python -m uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000

# Run any agent server (each agent runs independently on its own port)
poetry run python -m agents --host localhost --port 10113 --agent-card agent_cards/orchestrator_agent.json
poetry run python -m agents --host localhost --port 10115 --agent-card agent_cards/planner_agent.json
poetry run python -m agents --host localhost --port 10101 --agent-card agent_cards/aspectuator_agent.json
# ...repeat pattern for each agent card

# Lint / sort imports
poetry run isort src/

# Run tests
poetry run pytest
# Single test file
poetry run pytest path/to/test_file.py
```

### Frontend (Angular)

```bash
cd front_end/marketing-assistant
npm install
ng serve          # dev server at http://localhost:4200
ng build          # production build
```

The Angular dev environment points to `http://localhost:10113` (Orchestrator Agent) and `http://localhost:8000` (Tools API). These are set in `front_end/marketing-assistant/src/environments/environment.ts`.

## Architecture

This is an **Agent-to-Agent (A2A)** marketing assistant where every agent is an independent HTTP service communicating via the `a2a-sdk` protocol.

### Runtime topology

```
Angular Frontend (port 4200)
    └── SSE stream → Orchestrator Agent (port 10113)
                         ├── [MCP] → agents/mcp  ─────→ FastMCP "Agents" server  (port 8000 /agents/mcp)
                         │               find_agent (semantic search over agent cards)
                         │
                         └── [A2A] → Planner Agent (port 10115)
                                      Deep Research Agent  (port 10105)
                                      Aspectuator Agent    (port 10101)
                                      Content Strategist   (port 10103)
                                      SEO Blog Writer      (port 10117)
                                      LinkedIn Post Gen    (port 10109)
                                      Image Generation     (port 10107)
                                      Marketing Assistant  (port 10111)
                                          └── [MCP] → tools/mcp ──→ FastMCP "Tools" server (port 8000 /tools/mcp)
```

### Key source locations

| Path | Purpose |
|---|---|
| `src/agents/__main__.py` | CLI entry point; maps agent card names → agent classes |
| `src/agents/orchestrator_agent.py` | Workflow DAG executor; drives the multi-agent pipeline |
| `src/agents/planner_agent.py` | LangGraph ReAct agent; decomposes user queries into task lists |
| `src/agents/marketing_assistant_agent.py` | Google ADK agent; base for all specialised agents |
| `src/common/agent_executor.py` | `GenericAgentExecutor` — A2A request handler for all agents |
| `src/common/workflow.py` | `WorkflowGraph` / `WorkflowNode` — directed-graph executor over A2A calls |
| `src/common/base_agent.py` | Pydantic base class all agents inherit from |
| `src/common/types.py` | Shared Pydantic models (`PlannerResponseFormat`, `TaskList`, etc.) |
| `src/common/instructions/` | Per-agent system prompt / CoT instructions |
| `src/mcp_server/app.py` | Combined FastAPI app mounting both FastMCP sub-apps |
| `src/mcp_server/server_agents.py` | Builds Gemini embeddings of agent cards for semantic `find_agent` |
| `src/mcp_server/server_api.py` | Implements all FastMCP tool handlers |
| `src/mcp_server/client_agents.py` | MCP client helpers used by `WorkflowNode` |
| `agent_cards/*.json` | A2A agent cards (name, URL, skills); read at startup |

### Request flow (happy path)

1. Angular sends a message via SSE to `POST /message:stream` on the **Orchestrator Agent**.
2. `GenericAgentExecutor.execute()` calls `OrchestratorAgent.stream()`.
3. Orchestrator creates a `WorkflowGraph`, adds a **Planner** node, and calls the **Planner Agent** via A2A.
4. Planner returns a `PlannerResponseFormat` — a structured `TaskList` of sequential tasks.
5. Orchestrator adds one `WorkflowNode` per task, then iterates `WorkflowGraph.run_workflow()`.
6. Each node calls `find_agent` on the **Agents MCP server** (cosine similarity over embedded agent cards) to locate the right agent URL, then sends the task via A2A.
7. Specialised agents (ADK-based) call tools on the **Tools MCP server** (`/tools/mcp`) — SerpAPI, Pinecone, PostgreSQL, LinkedIn, image gen, blog writer.
8. Once all nodes complete, Orchestrator generates a Gemini summary and yields it as the final artifact.

### Agent model selection (`marketing_assistant_agent.py`)

- `MarketingAssistantAgent` (name `MarketingAssistantAgent`) → `LITE_LLM_REVIEWER` env var (default `gemini-2.5-pro`)
- `DeepResearchAgent` → `LITE_LLM_RESEARCHER` (default `gemini-2.5-pro-preview`)
- All others → `LITE_LLM_AGENT` (default `gemini-2.0-flash-lite`)

### PlannerAgent checkpointing

`PlannerAgent` uses `langgraph-checkpoint-postgres` for session persistence, automatically falling back to `MemorySaver` if PostgreSQL is unavailable (`src/common/checkpointer.py`).

### MCP server (port 8000)

Two FastMCP sub-apps are mounted on one FastAPI instance:
- `/tools/mcp` — all callable tools (Pinecone, Postgres, SerpAPI, LinkedIn, Blog, Image)
- `/agents/mcp` — `find_agent` tool + `resource://agent_cards/{card_name}` resources

On startup, `build_agent_card_embeddings()` embeds every JSON file in `AGENT_CARDS_DIR` using `GEMINI_EMBEDDING_MODEL` and stores results in an in-memory DataFrame used by `find_agent`.

### Blog publishing

Blog posts are written as HTML to `BLOG_POST_OUTPUT_DIR` and served via Docker+Nginx containers. `src/mcp_server/server_api.py` contains `publish_blog_post_tool` which spins up a container per post.

## Environment variables

Required variables (see `.env` for the full list):

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` | Google Gemini / GenAI key (used by all agents) |
| `DB_URI` | PostgreSQL connection string (Neon or local) |
| `PINECONE_API_KEY` / `PINECONE_INDEX_NAME` | Vector store |
| `SERP_API_KEY` | SerpAPI web search |
| `AGENT_CARDS_DIR` | Path to `agent_cards/` directory (default `agent_cards`) |
| `MCP_SERVER_PORT` | Port for agents MCP (default `8000`) |
| `MCP_SERVER_PORT_2` | Port for tools MCP (default `8000`) |
| `MCP_SERVER_AGENTS_PATH` | Mount path for agents MCP (default `/agents/mcp`) |
| `MCP_SERVER_TOOLS_PATH` | Mount path for tools MCP (default `/tools/mcp`) |
| `LITE_LLM_AGENT` / `LITE_LLM_RESEARCHER` / `LITE_LLM_REVIEWER` | Model names |
| `GEMINI_EMBEDDING_MODEL` | Model for agent card embeddings |
| `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` | LangSmith observability |
| `BLOG_POST_OUTPUT_DIR` | Directory for published blog HTML |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 for image storage |
