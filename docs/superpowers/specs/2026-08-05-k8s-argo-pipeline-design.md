# RecipeAI — Kubernetes Argo Pipeline Design

## Background

RecipeAI is a CLI app that generates recipes with nutrition analysis using a multi-agent LLM pipeline. It has two operating modes (cuisine-based, ingredient-based) that both follow a 3-stage flow: Plan → Cook → Nutrition. The app currently runs locally as a single process with an MCP nutrition server spawned as a subprocess over stdio.

This design deploys RecipeAI as a 3-stage Argo Workflow pipeline on Kubernetes, with each stage running in its own container and the MCP nutrition server as a standalone K8s Service.

## Current State

- **Entry point:** `main.py` — CLI with `--mode cuisine|ingredient` and mode-specific args
- **Stage 1 (Plan):** `src/planner.py` (cuisine) or `src/ingredient_planner.py` (ingredient) — produces a `Plan` Pydantic model
- **Stage 2 (Chef):** `src/chef.py` — `generate_recipe()` (cuisine) or `generate_nutrition_aware_recipe()` (ingredient) — produces a `Recipe` Pydantic model
- **Stage 3 (Nutrition):** `src/nutrition.py` — calls MCP server to compute `NutritionProfile`
- **MCP Server:** `nutrition_mcp/mcp_server.py` — stdio transport, backed by TinyDB (`data/nutrition.json`)
- **MCP Client:** `nutrition_mcp/mcp_client.py` — async subprocess-based, JSON-RPC over stdin/stdout
- **Data models:** `src/models.py` — `UserNeeds`, `Plan`, `Recipe`, `NutritionProfile` (Pydantic v2)
- **No container/K8s configs exist**

## Proposal

Containerize each pipeline stage separately, add stage CLI wrappers for file-based I/O, convert the MCP server to Streamable HTTP transport for cross-pod communication, refactor LangChain tools to native async, and orchestrate with Argo Workflows using artifact passing between stages.

## Design

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Argo Workflow                          │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌───────────────┐     │
│  │ Planner  │───▶│   Chef   │───▶│   Nutrition   │     │
│  │  Stage   │    │  Stage   │    │    Stage      │     │
│  └──────────┘    └──────────┘    └───────┬───────┘     │
│   plan.json       recipe.json       ▲    │              │
│   (artifact)      (artifact)        │    │              │
│                                     │    ▼              │
│                              ┌──────┴──────────┐       │
│                              │  MCP Nutrition   │       │
│                              │    Service       │       │
│                              │  (Deployment +   │       │
│                              │   ClusterIP)     │       │
│                              └─────────────────┘       │
└─────────────────────────────────────────────────────────┘
         ▲
         │ OPENAI_API_KEY
    ┌────┴─────┐
    │ K8s      │
    │ Secret   │
    └──────────┘
```

### Container Images (4 total)

| Image | Entrypoint | Purpose |
|-------|-----------|---------|
| `recipeai-planner` | `.venv/bin/python -m stages.plan_stage` | Runs cuisine or ingredient planner based on `mode` param |
| `recipeai-chef` | `.venv/bin/python -m stages.chef_stage` | Runs standard or nutrition-aware chef based on `mode` param |
| `recipeai-nutrition` | `.venv/bin/python -m stages.nutrition_stage` | Computes nutrition via HTTP call to MCP service |
| `recipeai-mcp-server` | `.venv/bin/python -m nutrition_mcp.mcp_http_server` | Standalone nutrition DB service over Streamable HTTP |

Images are built with podman and loaded into the local cluster (minikube/kind). Manifests use `imagePullPolicy: Never`.

### Stage CLI Wrappers

New `stages/` package with thin CLI wrappers. Each reads input from a file, calls existing business logic, writes output to a file.

#### `stages/plan_stage.py`

```
Input:  CLI args (--mode, --cuisine, --max-prep-time, --dietary-needs, --request, --nutrition-goals)
Output: /output/plan.json (serialized Plan model)
Also outputs: /output/plan_metadata.json (mode, nutrition_goals for downstream stages)
```

- Cuisine mode: calls `generate_plan(UserNeeds(...))` from `src/planner.py`
- Ingredient mode: calls `generate_ingredient_plan(request)` from `src/ingredient_planner.py`
  - Requires MCP client connection for tool-calling ReAct agent
  - Connects to MCP service via `MCP_SERVER_URL` env var

#### `stages/chef_stage.py`

```
Input:  /input/plan.json, /input/plan_metadata.json
Output: /output/recipe.json (serialized Recipe model)
```

- Reads `mode` from metadata to pick chef variant
- Cuisine mode: calls `generate_recipe(plan)` from `src/chef.py`
- Ingredient mode: calls `generate_nutrition_aware_recipe(plan, nutrition_goals)` from `src/chef.py`

#### `stages/nutrition_stage.py`

```
Input:  /input/recipe.json
Output: /output/nutrition.json (serialized NutritionProfile with formatting)
```

- Calls `compute_nutrition(recipe)` from `src/nutrition.py`
- Uses HTTP MCP client via `MCP_SERVER_URL` env var

### MCP Server — Streamable HTTP Transport

#### New file: `nutrition_mcp/mcp_http_server.py`

Wraps the existing `NutritionMCPServer` class but serves over Streamable HTTP using `mcp.server.streamable_http` instead of `mcp.server.stdio`. Listens on port 8080.

Exposes two health endpoints:
- `/healthz` — liveness probe, returns 200 if the server process is alive
- `/readyz` — readiness probe, returns 200 only when TinyDB is loaded and ready to serve

The existing `nutrition_mcp/mcp_server.py` (stdio) remains unchanged for local development.

#### New file: `nutrition_mcp/mcp_http_client.py`

Streamable HTTP-based MCP client that connects to the MCP service at `MCP_SERVER_URL`. Implements the same interface as `AsyncNutritionMCPClient` (same `call_tool()` and `calculate_recipe_nutrition()` methods).

#### Updated: `src/mcp_tools.py` — `MCPClientManager`

Updated to support both transports:
- If `MCP_SERVER_URL` env var is set → use HTTP client (K8s mode)
- Otherwise → use stdio client (local mode, existing behavior)

### LangChain Tools — Native Async Refactor

Refactor the 4 LangChain tools in `src/mcp_tools.py` (`FindIngredientTool`, `CalculateRecipeNutritionTool`, `GetHighProteinFoodsTool`, `SearchIngredientsTool`) from sync `_run()` + `asyncio.run()` + `nest_asyncio` to native async `_arun()` methods.

- Remove `nest_asyncio` dependency and its `nest_asyncio.apply()` call
- Remove `asyncio.run()` wrappers from each tool
- Implement `_arun()` on each tool, calling the MCP client directly
- Update `src/agent_utils.py` to use `await agent_executor.ainvoke()` instead of `agent_executor.invoke()`
- Update `src/ingredient_planner.py` to be async (`async def generate_ingredient_plan`)

### Containerfiles

Located in `images/` directory. Built with podman. All share a common pattern:

```dockerfile
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ src/
COPY stages/ stages/
COPY nutrition_mcp/ nutrition_mcp/
COPY database/ database/
COPY utils/ utils/
COPY data/ data/
```

Per-image Containerfiles:
- `images/Containerfile.planner` — `ENTRYPOINT [".venv/bin/python", "-m", "stages.plan_stage"]`
- `images/Containerfile.chef` — `ENTRYPOINT [".venv/bin/python", "-m", "stages.chef_stage"]`
- `images/Containerfile.nutrition` — `ENTRYPOINT [".venv/bin/python", "-m", "stages.nutrition_stage"]`
- `images/Containerfile.mcp-server` — `ENTRYPOINT [".venv/bin/python", "-m", "nutrition_mcp.mcp_http_server"]`, exposes port 8080

A comprehensive `.containerignore` excludes `.venv/`, `tests/`, `.git/`, `.vscode/`, `docs/`, `.env`, and raw USDA source data (`data/complete_nutrition_database.json`).

### K8s Manifests

```
k8s/
├── namespace.yaml
├── secret.yaml                 # Template with placeholder for OPENAI_API_KEY
├── mcp-server/
│   ├── deployment.yaml         # 1 replica, port 8080, liveness + readiness probes
│   └── service.yaml            # ClusterIP on port 8080
└── argo/
    ├── artifact-repo-configmap.yaml
    └── workflow.yaml
```

#### MCP Server Deployment

- Image: `recipeai-mcp-server:latest`
- `imagePullPolicy: Never` (local images)
- Replicas: 1
- Port: 8080
- Liveness probe: HTTP GET `/healthz`
- Readiness probe: HTTP GET `/readyz`
- Nutrition DB baked into image (read-only reference data)

#### MCP Server Service

- Type: ClusterIP
- Port: 8080
- Selector matches MCP server Deployment pods

#### K8s Secret

Template file with placeholder:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: recipeai-secrets
  namespace: recipeai
type: Opaque
stringData:
  openai-api-key: "REPLACE_WITH_YOUR_KEY"
```

### Argo Workflow

Parameters:
- `mode` (required): `cuisine` or `ingredient`
- `cuisine` (cuisine mode): cuisine type
- `max-prep-time` (cuisine mode): minutes
- `dietary-needs` (optional): dietary restrictions
- `request` (ingredient mode): natural language request
- `nutrition-goals` (optional): e.g., "high protein", "low carb"

Steps:
1. **plan** — runs `recipeai-planner` with CLI args from workflow parameters. Outputs `plan.json` and `plan_metadata.json` as Argo artifacts.
2. **cook** — receives plan artifacts as inputs. Outputs `recipe.json` as Argo artifact.
3. **nutrition** — receives recipe artifact as input. Outputs `nutrition.json` as Argo artifact.

Env vars per step:
- **plan**: `OPENAI_API_KEY` (LLM calls), `MCP_SERVER_URL` (needed in ingredient mode — ReAct agent makes tool calls to MCP service during planning)
- **cook**: `OPENAI_API_KEY` (LLM calls only)
- **nutrition**: `MCP_SERVER_URL` only — no LLM calls, no API key

Error handling: fail fast. If a stage crashes, Argo marks it as failed. No automatic retries.

### Artifact Repository

Configurable via Argo's artifact repository ConfigMap. Works with:
- **MinIO** for local/dev clusters
- **S3/GCS/Azure Blob** for cloud clusters

The workflow references artifacts generically — the backend is configured at the Argo controller level, not in the workflow itself.

## Files Changed

### New files
- `stages/__init__.py`
- `stages/plan_stage.py`
- `stages/chef_stage.py`
- `stages/nutrition_stage.py`
- `nutrition_mcp/mcp_http_server.py`
- `nutrition_mcp/mcp_http_client.py`
- `images/Containerfile.planner`
- `images/Containerfile.chef`
- `images/Containerfile.nutrition`
- `images/Containerfile.mcp-server`
- `.containerignore`
- `k8s/namespace.yaml`
- `k8s/secret.yaml`
- `k8s/mcp-server/deployment.yaml`
- `k8s/mcp-server/service.yaml`
- `k8s/argo/artifact-repo-configmap.yaml`
- `k8s/argo/workflow.yaml`
- `k8s/kustomization.yaml`

### Modified files
- `src/mcp_tools.py` — `MCPClientManager` updated to support HTTP transport; LangChain tools refactored to native async (`_arun()`)
- `src/agent_utils.py` — updated to use `ainvoke()` for async agent execution
- `src/ingredient_planner.py` — `generate_ingredient_plan` made async

### Unchanged files
- `main.py` — local CLI usage preserved
- `src/planner.py`, `src/chef.py`, `src/nutrition.py` — business logic untouched
- `src/models.py` — Pydantic models are the inter-stage contract
- `src/llm_config.py` — unchanged
- `nutrition_mcp/mcp_server.py` — stdio version preserved for local dev
- `nutrition_mcp/mcp_client.py` — stdio client preserved for local dev
- `database/`, `utils/`, `data/` — unchanged

## Testing

- **Local:** `main.py` continues to work unchanged (stdio MCP path)
- **Stage wrappers:** Each stage can be tested locally by running it with file I/O: `.venv/bin/python -m stages.plan_stage --mode cuisine --cuisine italian --max-prep-time 30`
- **Containers:** Build and run each image locally with `podman run`
- **MCP HTTP server:** Test with curl against `/healthz`, `/readyz`, and a sample tool call
- **Argo:** Submit workflow to a local cluster (kind/minikube) with Argo installed

## Security

- `OPENAI_API_KEY` stored as a K8s Secret, never baked into images or committed
- `OPENAI_API_KEY` only injected into steps that make LLM calls (plan, cook) — not into the nutrition step
- Secret template in `k8s/secret.yaml` uses placeholder values
- `.env` file excluded from container images via `.containerignore`
- MCP service is ClusterIP only — not exposed outside the cluster
- No other credentials or sensitive data in the pipeline
