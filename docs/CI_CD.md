# CI/CD Guide — Chatbot A2A Marketing Assistant

## Overview

This project has three GitHub Actions workflows that run automatically or on-demand to validate code quality and system health.

```
                         Push / PR to main
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              │
        ┌──────────────┐ ┌──────────────┐     │
        │ Backend CI   │ │ Frontend CI  │     │
        │ (isort +     │ │ (prettier +  │     │
        │  pytest)     │ │  vitest)     │     │
        └──────────────┘ └──────────────┘     │
                │              │              │
                └──────┬───────┘              │
                       ▼                      │
                 ✅ Status checks             │
                 on PR before merge           │
                                              │
                                              │
              Manual trigger                  │
           (workflow_dispatch)                │
                    │                         │
                    ▼                         │
           ┌──────────────┐                   │
           │  E2E Tests   │ ◄─────────────────┘
           │ (MCP Tools & │
           │  Agents)     │
           └──────────────┘
```

## Workflows

### 1. Backend CI (`backend-ci.yml`)

**Runs on:** Every push to `main` and every PR targeting `main`.

| Job | Tool | What it checks |
|---|---|---|
| `lint` | `isort --check-only` | Import ordering follows project conventions |
| `unit-test` | `pytest` | Pure-Python logic: Pydantic models, type validators, schema registries, utilities |

**What is NOT tested here:** `src/tools/` and `src/mcp_server/` are excluded because they import live cloud SDKs (Pinecone, Google genai, PostgreSQL). Those are covered by the E2E workflow.

**Failure recovery:**
- `lint` fails → run `poetry run isort src/` locally and commit
- `unit-test` fails → read the pytest output for the specific assertion that failed

### 2. Frontend CI (`frontend-ci.yml`)

**Runs on:** Every push to `main` and every PR targeting `main`.

| Job | Tool | What it checks |
|---|---|---|
| `lint` | `prettier --check` | Code formatting across `.ts`, `.html`, `.scss` files |
| `unit-test` | `vitest --run` | Angular component and service unit tests with jsdom |

**Failure recovery:**
- `lint` fails → run `npx prettier --write "src/**/*.{ts,html,scss}"` and commit
- `unit-test` fails → check the Vitest output for the failing test name

### 3. E2E Tests (`e2e-tests.yml`)

**Runs on:** Manual trigger only — developer opts in.

This workflow starts the full backend stack and verifies all MCP tools and agent services are reachable and functional.

**Steps performed:**
1. Checkout code, install Python 3.12 + Poetry deps
2. Write `.env` from GitHub Secrets (real credentials)
3. Start MCP server on port 8000 (`poetry run python -m mcp_server`)
4. Poll health check until the server responds
5. Run **Tools MCP test**: `client_agents --path /tools/mcp --test`
6. Run **Agents MCP test**: `client_agents --path /agents/mcp --test`
7. Stop server and collect logs

**What these tests validate:**
- Tools MCP: Pinecone scraper/pusher/retriever, PostgreSQL tools, SerpAPI search, image generation, LinkedIn posting, blog writer
- Agents MCP: Agent card embedding (Gemini), semantic `find_agent` tool

## How to Run E2E Tests

### From GitHub UI
1. Go to your repo → **Actions** tab
2. Select **"E2E Tests (MCP Tools & Agents)"** from the left sidebar
3. Click **"Run workflow"** → **"Run workflow"**

### From CLI

```bash
gh workflow run e2e-tests.yml

# Watch the run in real time:
gh run watch

# View results:
gh run view --log
```

## Required GitHub Secrets

These must be set in **Repo Settings → Secrets and variables → Actions → Repository secrets**.

| Secret | Used by | Where to get it |
|---|---|---|
| `GOOGLE_API_KEY` | E2E | [Google AI Studio](https://aistudio.google.com/apikey) |
| `DB_URI` | E2E | [Neon Console](https://console.neon.tech) → Connection string |
| `PINECONE_API_KEY` | E2E | [Pinecone Console](https://app.pinecone.io) → API Keys |
| `PINECONE_INDEX_NAME` | E2E | Pinecone Console → Index name (e.g. `deep-research-agent`) |
| `SERP_API_KEY` | E2E | [SerpAPI Dashboard](https://serpapi.com/manage-api-key) |
| `OPENAI_API_KEY` | E2E | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `LANGSMITH_API_KEY` | E2E | [LangSmith Settings](https://smith.langchain.com/settings) |
| `AWS_ACCESS_KEY_ID` | E2E | [AWS IAM](https://console.aws.amazon.com/iam) → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | E2E | AWS IAM (paired with Access Key ID) |
| `GEMINI_EMBEDDING_MODEL` | E2E | Model name string (default: `gemini-embedding-001`) |

## Interpreting Failures

### Backend CI Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `isort` reports misordered imports | Code was pushed without running isort | `poetry run isort src/` and commit |
| `pytest` import error | New file imports a cloud SDK not mocked in CI | Move the test to E2E, or add a mock |
| `pytest` assertion failure | Logic bug in a model or utility | Check the traceback for the specific assertion |

### Frontend CI Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `prettier` reports formatting issues | Code pushed without formatting | `npx prettier --write "src/**/*.{ts,html,scss}"` |
| `vitest` component creation fails | Missing import or provider in `TestBed` | Check the component's dependencies are provided |
| `vitest` timeout | Test is doing real HTTP calls instead of mocking | Use Angular's `HttpClientTestingModule` |

### E2E Test Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| MCP server doesn't start | Port 8000 is already in use in the CI runner | Add `lsof -ti:8000 | xargs kill -9` before starting |
| Tools MCP test fails for one tool | That service's API key is invalid or expired | Rotate the key in GitHub Secrets and re-run |
| Tools MCP test fails for all tools | `.env` was not written correctly | Check the "Verify .env file" step output in the CI log |
| Agents MCP test fails | `GOOGLE_API_KEY` is invalid or `GEMINI_EMBEDDING_MODEL` name is wrong | Verify the key in Google AI Studio and the model name in Secrets |

## Adding New Tests

### Python Unit Tests
- Place in the same directory as the code being tested
- Name: `test_<module>.py` or `test_<feature>.py`
- Only test pure-Python logic — no cloud SDK imports
- Run locally: `poetry run pytest src/path/to/test_file.py -v`

### Python E2E Tests
- Tests that need live services go in the E2E workflow's test runner
- Currently uses `client_agents --test`; future integration tests can be added as separate scripts
- Run locally: start `poetry run python -m mcp_server` first, then run the test

### Frontend Unit Tests
- Place next to the component: `my-component.spec.ts`
- Use Angular `TestBed` for component tests
- Use Vitest mocking (`vi.fn()`) for services
- Run locally: `npx vitest --run`

## Branch Protection (Recommended)

Configure in **Repo Settings → Rules → Rulesets**:

1. Create a ruleset targeting the `main` branch
2. Enable **"Require status checks to pass before merging"**
3. Add these required checks:
   - `Lint (isort)` / `Unit Tests (pytest)` — from Backend CI
   - `Lint (Prettier)` / `Unit Tests (Vitest)` — from Frontend CI
4. Enable **"Require branches to be up to date before merging"**
