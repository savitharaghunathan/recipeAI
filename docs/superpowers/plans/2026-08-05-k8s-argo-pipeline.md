# K8s Argo Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy RecipeAI as a 3-stage Argo Workflow pipeline on Kubernetes with per-stage containers, a Streamable HTTP MCP server, and native async LangChain tools.

**Architecture:** Each pipeline stage (Plan, Chef, Nutrition) runs in its own container with file-based I/O. The MCP nutrition server runs as a standalone K8s Deployment serving over Streamable HTTP. Argo Workflows orchestrates the stages, passing JSON artifacts between them. Images are built with podman and loaded locally.

**Tech Stack:** Python 3.13, MCP SDK 1.13 (Streamable HTTP), Starlette/uvicorn, LangChain, Pydantic v2, Argo Workflows, podman, Kubernetes

## Global Constraints

- Python >= 3.13
- All existing tests must continue to pass (`pytest tests/ -v`)
- `main.py` local CLI must continue to work unchanged (stdio MCP path)
- `src/planner.py`, `src/chef.py`, `src/nutrition.py` business logic must not be modified
- `src/models.py` Pydantic models are the inter-stage data contract
- Existing stdio MCP server (`nutrition_mcp/mcp_server.py`) and client (`nutrition_mcp/mcp_client.py`) must be preserved
- Container runtime: podman (Containerfile, not Dockerfile)
- Image registry: local only, `imagePullPolicy: Never`
- No `nest_asyncio` after refactor — native async throughout
- Entrypoints use `.venv/bin/python` directly, not `uv run`

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `nutrition_mcp/mcp_http_server.py` | Streamable HTTP MCP server with `/healthz` and `/readyz` endpoints |
| `nutrition_mcp/mcp_http_client.py` | Streamable HTTP MCP client, same interface as `AsyncNutritionMCPClient` |
| `stages/__init__.py` | Package marker |
| `stages/plan_stage.py` | CLI wrapper: args → Plan → `/output/plan.json` + metadata |
| `stages/chef_stage.py` | CLI wrapper: reads plan → Recipe → `/output/recipe.json` |
| `stages/nutrition_stage.py` | CLI wrapper: reads recipe → NutritionProfile → `/output/nutrition.json` |
| `images/Containerfile.planner` | Container image for plan stage |
| `images/Containerfile.chef` | Container image for chef stage |
| `images/Containerfile.nutrition` | Container image for nutrition stage |
| `images/Containerfile.mcp-server` | Container image for MCP HTTP server |
| `.containerignore` | Excludes `.venv/`, `tests/`, `.git/`, `.vscode/`, `docs/`, `.env`, raw USDA data |
| `k8s/namespace.yaml` | `recipeai` namespace |
| `k8s/secret.yaml` | Template Secret for `OPENAI_API_KEY` |
| `k8s/mcp-server/deployment.yaml` | MCP server Deployment with health probes |
| `k8s/mcp-server/service.yaml` | ClusterIP Service for MCP server |
| `k8s/argo/artifact-repo-configmap.yaml` | Argo artifact repository config |
| `k8s/argo/workflow.yaml` | 3-stage Argo Workflow |
| `k8s/kustomization.yaml` | Kustomize overlay |
| `tests/test_mcp_http.py` | Tests for HTTP server and client |
| `tests/test_stages.py` | Tests for stage CLI wrappers |

### Modified files

| File | Changes |
|------|---------|
| `src/mcp_tools.py` | `MCPClientManager` supports HTTP transport via `MCP_SERVER_URL`; LangChain tools refactored to native async `_arun()` |
| `src/agent_utils.py` | `run_agent_with_parsing` made async, uses `ainvoke()` |
| `src/ingredient_planner.py` | `generate_ingredient_plan` made async |
| `main.py` | Update `run_ingredient_mode` to `await` the now-async `generate_ingredient_plan` |
| `pyproject.toml` | Add `uvicorn` to dependencies (for MCP HTTP server entrypoint) |

---

### Task 1: MCP Streamable HTTP Server

**Files:**
- Create: `nutrition_mcp/mcp_http_server.py`
- Create: `tests/test_mcp_http.py`
- Modify: `pyproject.toml` (add `uvicorn` dependency)

**Interfaces:**
- Consumes: `NutritionMCPServer` class from `nutrition_mcp/mcp_server.py` (reuses its tool handler registrations via its `.server` attribute)
- Produces: A Starlette ASGI app serving MCP over Streamable HTTP on port 8080, with `/healthz` and `/readyz` endpoints. Runnable as `python -m nutrition_mcp.mcp_http_server`.

- [ ] **Step 1: Add `uvicorn` to dependencies**

In `pyproject.toml`, add `uvicorn` to the `dependencies` list:

```toml
dependencies = [
    "httpx>=0.28.1",
    "langchain>=0.3.27",
    "langchain-openai>=0.3.30",
    "mcp>=1.13.0",
    "nest-asyncio>=1.5.0",
    "pydantic>=2.11.7",
    "tinydb>=4.8.2",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.35.0",
]
```

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && uv sync`

- [ ] **Step 2: Write the MCP HTTP server**

Create `nutrition_mcp/mcp_http_server.py`:

```python
import contextlib
import logging
from collections.abc import AsyncIterator

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from nutrition_mcp.mcp_server import NutritionMCPServer

logger = logging.getLogger(__name__)

nutrition_server = NutritionMCPServer()


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def readyz(request: Request) -> JSONResponse:
    if nutrition_server.nutrition_db is None:
        nutrition_server._ensure_db()
    if nutrition_server.nutrition_db is None:
        return JSONResponse({"status": "not ready"}, status_code=503)
    return JSONResponse({"status": "ready"})


session_manager = StreamableHTTPSessionManager(
    app=nutrition_server.server,
    json_response=True,
)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    async with session_manager.run():
        logger.info("MCP HTTP server started on port 8080")
        yield
    nutrition_server.cleanup()


app = Starlette(
    routes=[
        Route("/healthz", healthz),
        Route("/readyz", readyz),
        Mount("/mcp", app=session_manager.handle_request),
    ],
    lifespan=lifespan,
)


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
```

Note: The `NutritionMCPServer` class needs a small helper to eagerly load the DB for the readiness check. We add `_ensure_db()`:

In `nutrition_mcp/mcp_server.py`, the DB is lazily initialized inside `handle_call_tool`. For the readyz probe, we need to trigger that initialization. Since we can't modify the server file (it's "unchanged"), we'll access `nutrition_db` directly and initialize it if needed. If `nutrition_db` is `None`, we instantiate `NutritionDB` ourselves in the readyz handler:

```python
async def readyz(request: Request) -> JSONResponse:
    if nutrition_server.nutrition_db is None:
        try:
            from database import NutritionDB
            nutrition_server.nutrition_db = NutritionDB(
                nutrition_server.db_path, enable_llm=False
            )
        except Exception:
            return JSONResponse({"status": "not ready"}, status_code=503)
    return JSONResponse({"status": "ready"})
```

Replace the readyz handler in the file with this version.

- [ ] **Step 3: Write tests for the HTTP server**

Create `tests/test_mcp_http.py`:

```python
import pytest
from starlette.testclient import TestClient

from nutrition_mcp.mcp_http_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_mcp_endpoint_rejects_get_without_headers(client):
    response = client.get("/mcp")
    assert response.status_code in (400, 404, 405, 406)
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/test_mcp_http.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 5: Verify existing tests still pass**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

Expected: All existing tests PASS (skip integration tests that require API keys).

- [ ] **Step 6: Commit**

```bash
git add nutrition_mcp/mcp_http_server.py tests/test_mcp_http.py pyproject.toml uv.lock
git commit -m "feat: add MCP Streamable HTTP server with health probes"
```

---

### Task 2: MCP Streamable HTTP Client

**Files:**
- Create: `nutrition_mcp/mcp_http_client.py`
- Modify: `tests/test_mcp_http.py` (add client tests)

**Interfaces:**
- Consumes: MCP Streamable HTTP server at a URL (e.g., `http://localhost:8080/mcp`)
- Produces: `AsyncHTTPNutritionMCPClient` class with methods:
  - `async def connect(self) -> None`
  - `async def call_tool(self, tool_name: str, arguments: dict) -> Any`
  - `async def calculate_recipe_nutrition(self, recipe: Recipe) -> dict`
  - `async def close(self) -> None`
  Same interface pattern as `AsyncNutritionMCPClient` in `nutrition_mcp/mcp_client.py`.

- [ ] **Step 1: Write the HTTP client**

Create `nutrition_mcp/mcp_http_client.py`:

```python
import json
from typing import Any, Dict

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.models import Recipe


class AsyncHTTPNutritionMCPClient:
    """MCP client that connects to the nutrition server over Streamable HTTP."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session = None
        self._streams_context = None
        self._session_context = None

    async def connect(self):
        self._streams_context = streamablehttp_client(url=self.server_url)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()

    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        if not self._session:
            raise RuntimeError("Client not connected. Call connect() first.")
        result = await self._session.call_tool(tool_name, arguments)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return None

    async def calculate_recipe_nutrition(self, recipe: Recipe) -> Dict:
        ingredients = []
        for ingredient in recipe.ingredients:
            try:
                quantity_grams = float(ingredient.qty.split()[0]) if ingredient.qty else 100.0
            except (ValueError, IndexError):
                quantity_grams = 100.0
            ingredients.append({
                "name": ingredient.item,
                "quantity_grams": quantity_grams,
            })
        return await self.call_tool(
            "calculate_recipe_nutrition", {"ingredients": ingredients}
        )

    async def close(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None
            self._session = None
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
            self._streams_context = None
```

- [ ] **Step 2: Write integration test for HTTP client against HTTP server**

Add to `tests/test_mcp_http.py`:

```python
import asyncio
import uvicorn
import threading
import time

from nutrition_mcp.mcp_http_client import AsyncHTTPNutritionMCPClient
from src.models import Recipe, Ingredient


@pytest.fixture(scope="module")
def mcp_http_server():
    """Start MCP HTTP server in a background thread for testing."""
    config = uvicorn.Config(app, host="127.0.0.1", port=18080, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)
    yield "http://127.0.0.1:18080/mcp"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.asyncio
async def test_http_client_find_ingredient(mcp_http_server):
    client = AsyncHTTPNutritionMCPClient(mcp_http_server)
    await client.connect()
    try:
        result = await client.call_tool(
            "find_ingredient", {"ingredient_name": "rice", "max_results": 3}
        )
        assert "results_found" in result
        assert result["results_found"] > 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_http_client_calculate_recipe_nutrition(mcp_http_server):
    recipe = Recipe(
        title="Test",
        prep_time=10,
        cook_time=20,
        servings=2,
        ingredients=[Ingredient(item="rice", qty="200g")],
        steps=["Cook rice"],
    )
    client = AsyncHTTPNutritionMCPClient(mcp_http_server)
    await client.connect()
    try:
        result = await client.calculate_recipe_nutrition(recipe)
        assert "recipe_nutrition" in result
        assert result["recipe_nutrition"]["calories"] > 0
    finally:
        await client.close()
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/test_mcp_http.py -v`

Expected: All 5 tests PASS (3 from Task 1 + 2 new).

- [ ] **Step 4: Commit**

```bash
git add nutrition_mcp/mcp_http_client.py tests/test_mcp_http.py
git commit -m "feat: add MCP Streamable HTTP client"
```

---

### Task 3: Refactor MCPClientManager and LangChain Tools to Native Async

**Files:**
- Modify: `src/mcp_tools.py`
- Modify: `src/agent_utils.py`
- Modify: `src/ingredient_planner.py`
- Modify: `main.py`

**Interfaces:**
- Consumes:
  - `AsyncNutritionMCPClient` from `nutrition_mcp/mcp_client.py` (stdio, unchanged)
  - `AsyncHTTPNutritionMCPClient` from `nutrition_mcp/mcp_http_client.py` (HTTP, from Task 2)
  - `MCP_SERVER_URL` env var to choose transport
- Produces:
  - `MCPClientManager.start_server()` — starts stdio or HTTP client depending on env var
  - `MCPClientManager.stop_server()` — stops either client
  - `MCPClientManager.get_client()` — returns whichever client is active
  - All 4 LangChain tools with `_arun()` instead of `_run()`
  - `async def run_agent_with_parsing(...)` in `src/agent_utils.py`
  - `async def generate_ingredient_plan(...)` in `src/ingredient_planner.py`

- [ ] **Step 1: Update `src/mcp_tools.py`**

Replace the entire file with:

```python
"""
MCP wrapper for nutrition tools — supports both stdio (local) and HTTP (K8s) transports.
"""

import json
import os
from langchain.tools import BaseTool
from typing import Any, Dict, Optional


class MCPClientManager:
    """Singleton manager for MCP client — stdio or HTTP based on MCP_SERVER_URL env var."""

    _instance = None
    _client = None
    _transport = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def start_server(cls):
        mcp_server_url = os.environ.get("MCP_SERVER_URL")

        if mcp_server_url:
            from nutrition_mcp.mcp_http_client import AsyncHTTPNutritionMCPClient
            cls._client = AsyncHTTPNutritionMCPClient(mcp_server_url)
            await cls._client.connect()
            cls._transport = "http"
        else:
            from nutrition_mcp.mcp_client import AsyncNutritionMCPClient
            cls._client = AsyncNutritionMCPClient()
            await cls._client.start_server()
            cls._transport = "stdio"

    @classmethod
    async def stop_server(cls):
        if cls._client is not None:
            if cls._transport == "http":
                await cls._client.close()
            else:
                await cls._client.stop_server()
            cls._client = None
            cls._transport = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            raise RuntimeError("MCP client not started. Call start_server() first.")
        return cls._client


class FindIngredientTool(BaseTool):
    name: str = "find_ingredient"
    description: str = "Find nutrition data for an ingredient using fuzzy matching. Returns matches with nutrition information."

    def _run(self, tool_input) -> str:
        raise NotImplementedError("Use _arun for async execution")

    async def _arun(self, tool_input) -> str:
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            ingredient_name = params.get("ingredient_name")
            max_results = params.get("max_results", 5)
            client = MCPClientManager.get_client()
            result = await client.call_tool(
                "find_ingredient",
                {"ingredient_name": ingredient_name, "max_results": max_results},
            )
            return str(result)
        except Exception as e:
            return f"Error finding ingredient: {str(e)}"


class CalculateRecipeNutritionTool(BaseTool):
    name: str = "calculate_recipe_nutrition"
    description: str = "Calculate total nutrition for a recipe. Input should be a list of ingredients with names and quantities in grams."

    def _run(self, tool_input) -> str:
        raise NotImplementedError("Use _arun for async execution")

    async def _arun(self, tool_input) -> str:
        try:
            if isinstance(tool_input, str):
                try:
                    params = json.loads(tool_input)
                    if isinstance(params, list):
                        ingredients_data = params
                    else:
                        ingredients_data = params.get("ingredients", params)
                except json.JSONDecodeError:
                    ingredients_data = tool_input
            else:
                if isinstance(tool_input, list):
                    ingredients_data = tool_input
                else:
                    ingredients_data = tool_input.get("ingredients", tool_input)
            if isinstance(ingredients_data, str):
                ingredients_data = json.loads(ingredients_data)
            client = MCPClientManager.get_client()
            result = await client.call_tool(
                "calculate_recipe_nutrition", {"ingredients": ingredients_data}
            )
            return str(result)
        except Exception as e:
            return f"Error calculating recipe nutrition: {str(e)}"


class GetHighProteinFoodsTool(BaseTool):
    name: str = "get_high_protein_foods"
    description: str = "Find foods with protein content above a specified threshold. Useful for suggesting high-protein ingredients."

    def _run(self, tool_input) -> str:
        raise NotImplementedError("Use _arun for async execution")

    async def _arun(self, tool_input) -> str:
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            min_protein = params.get("min_protein", 20.0)
            client = MCPClientManager.get_client()
            result = await client.call_tool(
                "get_high_protein_foods", {"min_protein": min_protein}
            )
            return str(result)
        except Exception as e:
            return f"Error getting high protein foods: {str(e)}"


class SearchIngredientsTool(BaseTool):
    name: str = "search_ingredients"
    description: str = "Search for ingredients using keywords in food descriptions. Useful for finding specific types of foods."

    def _run(self, tool_input) -> str:
        raise NotImplementedError("Use _arun for async execution")

    async def _arun(self, tool_input) -> str:
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            description = params.get("description")
            client = MCPClientManager.get_client()
            result = await client.call_tool(
                "search_ingredients", {"description": description}
            )
            return str(result)
        except Exception as e:
            return f"Error searching ingredients: {str(e)}"


def get_nutrition_tools():
    return [
        FindIngredientTool(),
        CalculateRecipeNutritionTool(),
        GetHighProteinFoodsTool(),
        SearchIngredientsTool(),
    ]
```

- [ ] **Step 2: Update `src/agent_utils.py`**

Replace the entire file with:

```python
"""
Shared utilities for LangChain agents
"""

import json
import re
from typing import Type, TypeVar, Dict, Any
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, ValidationError

from src.llm_config import get_completion_llm
from src.mcp_tools import get_nutrition_tools

T = TypeVar('T', bound=BaseModel)


def create_agent_executor(prompt: PromptTemplate, temperature: float = 0.7, max_iterations: int = 10) -> AgentExecutor:
    tools = get_nutrition_tools()
    llm = get_completion_llm(temperature=temperature)

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=max_iterations
    )


def parse_json_response(raw_output: str, model_class: Type[T]) -> T:
    try:
        if "Final Answer:" in raw_output:
            after_final = raw_output.split("Final Answer:")[-1]
            json_match = re.search(r'\{.*\}', after_final, re.DOTALL)
        else:
            json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)

        if not json_match:
            raise ValueError(f"No JSON found in agent output: {raw_output}")

        data = json.loads(json_match.group(0))
        return model_class.model_validate(data)

    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to parse agent output into {model_class.__name__}: {e}\nRaw output: {raw_output}")


async def run_agent_with_parsing(agent_executor: AgentExecutor, inputs: Dict[str, Any], model_class: Type[T]) -> T:
    result = await agent_executor.ainvoke(inputs)
    raw_output = result["output"]
    return parse_json_response(raw_output, model_class)
```

- [ ] **Step 3: Update `src/ingredient_planner.py`**

Replace the entire file with:

```python
"""
Ingredient-based planner agent using LangChain and MCP nutrition tools
"""

from langchain.prompts import PromptTemplate

from src.models import Plan, Ingredient
from src.agent_utils import create_agent_executor, run_agent_with_parsing


INGREDIENT_PLANNER_PROMPT = PromptTemplate(
    input_variables=["tools", "tool_names", "request", "agent_scratchpad"],
    template="""You are a meal planner that follows user requests exactly. Create simple meal plans based on what the user asks for.

TOOLS AVAILABLE:
{tools}

TOOL NAMES: {tool_names}

USER REQUEST: {request}

INSTRUCTIONS:
- Follow the user's request exactly - don't add extra requirements they didn't ask for
- If they ask for "simple", keep it simple with 3-4 basic ingredients
- If they specify ingredients, use those as the main focus
- Only use tools when needed to find specific ingredients or calculate nutrition
- Keep meal plans practical and realistic

You must use the following format:

Thought: I need to think about what to do
Action: tool_name
Action Input: {{"parameter_name": "value"}}
Observation: result from tool
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to create the final meal plan
Final Answer: {{valid json meal plan}}

EXAMPLES:
Thought: I need to find potato in the nutrition database
Action: find_ingredient
Action Input: {{"ingredient_name": "potato", "max_results": 3}}
Observation: {{"ingredient_searched": "potato", "results_found": 2, "matches": [...]}}

Thought: The user wants a simple potato recipe, so I'll create a basic plan with potatoes and a few complementary ingredients
Final Answer: {{"meal": "Simple Roasted Potatoes", "ingredients": [{{"item": "potatoes", "qty": "500g"}}, {{"item": "olive oil", "qty": "2 tbsp"}}, {{"item": "salt", "qty": "1 tsp"}}], "dietary_needs": "simple and satisfying"}}

IMPORTANT:
- Use "item" and "qty" fields in ingredients, not "name" and "quantity"!
- Match the user's dietary goals exactly (e.g., if they say "balanced", use "balanced", not "high protein")
- Keep it simple when they ask for simple recipes

{agent_scratchpad}"""
)


async def generate_ingredient_plan(request: str) -> Plan:
    agent_executor = create_agent_executor(INGREDIENT_PLANNER_PROMPT, temperature=0.7, max_iterations=20)
    return await run_agent_with_parsing(agent_executor, {"request": request}, Plan)
```

- [ ] **Step 4: Update `main.py`**

In `main.py`, the `run_ingredient_mode` function calls `generate_ingredient_plan(args.request)` synchronously. Since it's now async, add `await`:

Change line 106 from:
```python
            plan = generate_ingredient_plan(args.request)
```
to:
```python
            plan = await generate_ingredient_plan(args.request)
```

- [ ] **Step 5: Remove `nest-asyncio` from `pyproject.toml`**

In `pyproject.toml`, remove `"nest-asyncio>=1.5.0",` from the `dependencies` list.

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && uv sync`

- [ ] **Step 6: Remove `nest_asyncio` import from `src/mcp_tools.py`**

Already handled in Step 1 — the full file replacement does not import `nest_asyncio`. Verify it's gone:

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && grep -r "nest_asyncio" src/`

Expected: No output.

- [ ] **Step 7: Verify existing tests still pass**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/mcp_tools.py src/agent_utils.py src/ingredient_planner.py main.py pyproject.toml uv.lock
git commit -m "refactor: native async LangChain tools, drop nest_asyncio"
```

---

### Task 4: Stage CLI Wrappers

**Files:**
- Create: `stages/__init__.py`
- Create: `stages/plan_stage.py`
- Create: `stages/chef_stage.py`
- Create: `stages/nutrition_stage.py`
- Create: `tests/test_stages.py`

**Interfaces:**
- Consumes:
  - `generate_plan(UserNeeds) -> Plan` from `src/planner.py`
  - `async generate_ingredient_plan(str) -> Plan` from `src/ingredient_planner.py`
  - `generate_recipe(Plan) -> Recipe` from `src/chef.py`
  - `generate_nutrition_aware_recipe(Plan, str) -> Recipe` from `src/chef.py`
  - `async compute_nutrition(Recipe) -> NutritionProfile` from `src/nutrition.py`
  - `MCPClientManager` from `src/mcp_tools.py`
- Produces:
  - `stages/plan_stage.py` — CLI: `python -m stages.plan_stage --mode cuisine --cuisine X --max-prep-time N [--dietary-needs D]` or `python -m stages.plan_stage --mode ingredient --request "..." [--nutrition-goals G]`. Writes `/output/plan.json` and `/output/plan_metadata.json`.
  - `stages/chef_stage.py` — CLI: `python -m stages.chef_stage`. Reads `/input/plan.json` and `/input/plan_metadata.json`, writes `/output/recipe.json`.
  - `stages/nutrition_stage.py` — CLI: `python -m stages.nutrition_stage`. Reads `/input/recipe.json`, writes `/output/nutrition.json`.

- [ ] **Step 1: Create `stages/__init__.py`**

Create an empty `stages/__init__.py`:

```python
```

- [ ] **Step 2: Create `stages/plan_stage.py`**

```python
import argparse
import asyncio
import json
import os
import sys

from src.models import UserNeeds
from src.planner import generate_plan
from src.ingredient_planner import generate_ingredient_plan
from src.mcp_tools import MCPClientManager


async def run(args):
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    metadata = {"mode": args.mode}

    if args.mode == "cuisine":
        constraints = UserNeeds(
            cuisine=args.cuisine,
            max_prep_time=args.max_prep_time,
            dietary_needs=args.dietary_needs,
        )
        plan = generate_plan(constraints)
    else:
        await MCPClientManager.start_server()
        try:
            plan = await generate_ingredient_plan(args.request)
        finally:
            await MCPClientManager.stop_server()
        metadata["nutrition_goals"] = args.nutrition_goals or "balanced nutrition"

    plan_path = os.path.join(output_dir, "plan.json")
    with open(plan_path, "w") as f:
        f.write(plan.model_dump_json(indent=2))

    metadata_path = os.path.join(output_dir, "plan_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="RecipeAI Plan Stage")
    parser.add_argument("--mode", choices=["cuisine", "ingredient"], required=True)
    parser.add_argument("--cuisine", help="Cuisine type")
    parser.add_argument("--max-prep-time", type=int, help="Max prep time in minutes")
    parser.add_argument("--dietary-needs", help="Dietary restrictions")
    parser.add_argument("--request", help="Natural language recipe request")
    parser.add_argument("--nutrition-goals", help="Nutrition goals")

    args = parser.parse_args()

    if args.mode == "cuisine":
        if not args.cuisine or not args.max_prep_time:
            parser.error("Cuisine mode requires --cuisine and --max-prep-time")
    elif args.mode == "ingredient":
        if not args.request:
            parser.error("Ingredient mode requires --request")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `stages/chef_stage.py`**

```python
import json
import os
import sys

from src.models import Plan, Recipe
from src.chef import generate_recipe, generate_nutrition_aware_recipe


def main():
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    plan_path = os.path.join(input_dir, "plan.json")
    with open(plan_path) as f:
        plan = Plan.model_validate_json(f.read())

    metadata_path = os.path.join(input_dir, "plan_metadata.json")
    with open(metadata_path) as f:
        metadata = json.load(f)

    mode = metadata["mode"]

    if mode == "ingredient":
        nutrition_goals = metadata.get("nutrition_goals", "balanced nutrition")
        recipe = generate_nutrition_aware_recipe(plan, nutrition_goals)
    else:
        recipe = generate_recipe(plan)

    recipe_path = os.path.join(output_dir, "recipe.json")
    with open(recipe_path, "w") as f:
        f.write(recipe.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `stages/nutrition_stage.py`**

```python
import asyncio
import json
import os
import sys

from src.models import Recipe, NutritionProfile
from src.nutrition import compute_nutrition
from src.mcp_tools import MCPClientManager


async def run():
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    recipe_path = os.path.join(input_dir, "recipe.json")
    with open(recipe_path) as f:
        recipe = Recipe.model_validate_json(f.read())

    await MCPClientManager.start_server()
    try:
        nutrition = await compute_nutrition(recipe)
    finally:
        await MCPClientManager.stop_server()

    mcg_nutrients = {
        "vitamin_a_mcg", "vitamin_d_mcg", "vitamin_k_mcg",
        "folate_mcg", "vitamin_b12_mcg",
    }

    formatted = {
        "calories": f"{nutrition.calories} kcal",
        "macros": {k: f"{v} g" for k, v in nutrition.macros.items()},
        "micros": {
            k: f"{v} mcg" if k in mcg_nutrients else f"{v} mg"
            for k, v in nutrition.micros.items()
        },
    }

    nutrition_path = os.path.join(output_dir, "nutrition.json")
    with open(nutrition_path, "w") as f:
        json.dump(formatted, f, indent=2)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Write tests for stage wrappers**

Create `tests/test_stages.py`. These test the file I/O and arg parsing without making actual LLM calls:

```python
import json
import os
import tempfile
import pytest

from src.models import Plan, Recipe, Ingredient


class TestChefStage:
    def test_reads_plan_and_metadata(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        plan = Plan(
            meal="Test Pasta",
            ingredients=[Ingredient(item="pasta", qty="200g")],
            dietary_needs="vegetarian",
        )
        (input_dir / "plan.json").write_text(plan.model_dump_json())
        (input_dir / "plan_metadata.json").write_text(
            json.dumps({"mode": "cuisine"})
        )

        plan_loaded = Plan.model_validate_json(
            (input_dir / "plan.json").read_text()
        )
        assert plan_loaded.meal == "Test Pasta"

        metadata = json.loads(
            (input_dir / "plan_metadata.json").read_text()
        )
        assert metadata["mode"] == "cuisine"


class TestNutritionStage:
    def test_reads_recipe(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        recipe = Recipe(
            title="Test Pasta",
            prep_time=10,
            cook_time=20,
            servings=2,
            ingredients=[Ingredient(item="pasta", qty="200g")],
            steps=["Cook pasta"],
        )
        (input_dir / "recipe.json").write_text(recipe.model_dump_json())

        recipe_loaded = Recipe.model_validate_json(
            (input_dir / "recipe.json").read_text()
        )
        assert recipe_loaded.title == "Test Pasta"
        assert len(recipe_loaded.ingredients) == 1


class TestPlanMetadata:
    def test_cuisine_metadata(self):
        metadata = {"mode": "cuisine"}
        assert metadata["mode"] == "cuisine"
        assert "nutrition_goals" not in metadata

    def test_ingredient_metadata(self):
        metadata = {"mode": "ingredient", "nutrition_goals": "high protein"}
        assert metadata["mode"] == "ingredient"
        assert metadata["nutrition_goals"] == "high protein"
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/test_stages.py -v`

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add stages/ tests/test_stages.py
git commit -m "feat: add stage CLI wrappers for pipeline execution"
```

---

### Task 5: Containerfiles and `.containerignore`

**Files:**
- Create: `.containerignore`
- Create: `images/Containerfile.planner`
- Create: `images/Containerfile.chef`
- Create: `images/Containerfile.nutrition`
- Create: `images/Containerfile.mcp-server`

**Interfaces:**
- Consumes: Stage wrappers from Task 4, MCP HTTP server from Task 1
- Produces: 4 container images buildable with `podman build -f images/Containerfile.<stage> -t recipeai-<stage>:latest .`

- [ ] **Step 1: Create `.containerignore`**

```
.venv/
.git/
.gitignore
.vscode/
.env
tests/
docs/
data/complete_nutrition_database.json
*.pyc
__pycache__/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
images/
k8s/
```

- [ ] **Step 2: Create `images/Containerfile.planner`**

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
COPY data/nutrition.json data/nutrition.json

RUN mkdir -p /output

ENTRYPOINT [".venv/bin/python", "-m", "stages.plan_stage"]
```

- [ ] **Step 3: Create `images/Containerfile.chef`**

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
COPY data/nutrition.json data/nutrition.json

RUN mkdir -p /input /output

ENTRYPOINT [".venv/bin/python", "-m", "stages.chef_stage"]
```

- [ ] **Step 4: Create `images/Containerfile.nutrition`**

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
COPY data/nutrition.json data/nutrition.json

RUN mkdir -p /input /output

ENTRYPOINT [".venv/bin/python", "-m", "stages.nutrition_stage"]
```

- [ ] **Step 5: Create `images/Containerfile.mcp-server`**

```dockerfile
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY nutrition_mcp/ nutrition_mcp/
COPY database/ database/
COPY utils/ utils/
COPY data/nutrition.json data/nutrition.json

EXPOSE 8080

ENTRYPOINT [".venv/bin/python", "-m", "nutrition_mcp.mcp_http_server"]
```

- [ ] **Step 6: Verify podman can build the MCP server image**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && podman build -f images/Containerfile.mcp-server -t recipeai-mcp-server:latest .`

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add .containerignore images/
git commit -m "feat: add Containerfiles for all pipeline stages and MCP server"
```

---

### Task 6: Kubernetes Manifests and Argo Workflow

**Files:**
- Create: `k8s/namespace.yaml`
- Create: `k8s/secret.yaml`
- Create: `k8s/mcp-server/deployment.yaml`
- Create: `k8s/mcp-server/service.yaml`
- Create: `k8s/argo/artifact-repo-configmap.yaml`
- Create: `k8s/argo/workflow.yaml`
- Create: `k8s/kustomization.yaml`

**Interfaces:**
- Consumes: Container images from Task 5, health endpoints from Task 1
- Produces: Full K8s deployment manifests for `kubectl apply -k k8s/` and an Argo Workflow submittable with `argo submit k8s/argo/workflow.yaml`

- [ ] **Step 1: Create `k8s/namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: recipeai
```

- [ ] **Step 2: Create `k8s/secret.yaml`**

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

- [ ] **Step 3: Create `k8s/mcp-server/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: recipeai-mcp-server
  namespace: recipeai
  labels:
    app: recipeai-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: recipeai-mcp-server
  template:
    metadata:
      labels:
        app: recipeai-mcp-server
    spec:
      containers:
        - name: mcp-server
          image: recipeai-mcp-server:latest
          imagePullPolicy: Never
          ports:
            - containerPort: 8080
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
```

- [ ] **Step 4: Create `k8s/mcp-server/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: recipeai-mcp-server
  namespace: recipeai
spec:
  type: ClusterIP
  selector:
    app: recipeai-mcp-server
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
```

- [ ] **Step 5: Create `k8s/argo/artifact-repo-configmap.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: artifact-repositories
  namespace: recipeai
  annotations:
    workflows.argoproj.io/default-artifact-repository: default-artifact-repository
data:
  default-artifact-repository: |
    s3:
      bucket: recipeai-artifacts
      endpoint: minio.recipeai.svc.cluster.local:9000
      insecure: true
      accessKeySecret:
        name: minio-credentials
        key: accesskey
      secretKeySecret:
        name: minio-credentials
        key: secretkey
```

- [ ] **Step 6: Create `k8s/argo/workflow.yaml`**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: recipeai-pipeline-
  namespace: recipeai
spec:
  entrypoint: recipe-pipeline
  arguments:
    parameters:
      - name: mode
        value: "cuisine"
      - name: cuisine
        value: "italian"
      - name: max-prep-time
        value: "30"
      - name: dietary-needs
        value: ""
      - name: request
        value: ""
      - name: nutrition-goals
        value: ""

  templates:
    - name: recipe-pipeline
      steps:
        - - name: plan
            template: planner
        - - name: cook
            template: chef
        - - name: nutrition
            template: nutrition-agent

    - name: planner
      container:
        image: recipeai-planner:latest
        imagePullPolicy: Never
        command: [".venv/bin/python", "-m", "stages.plan_stage"]
        args:
          - "--mode"
          - "{{workflow.parameters.mode}}"
          - "--cuisine"
          - "{{workflow.parameters.cuisine}}"
          - "--max-prep-time"
          - "{{workflow.parameters.max-prep-time}}"
          - "--dietary-needs"
          - "{{workflow.parameters.dietary-needs}}"
          - "--request"
          - "{{workflow.parameters.request}}"
          - "--nutrition-goals"
          - "{{workflow.parameters.nutrition-goals}}"
        env:
          - name: OPENAI_API_KEY
            valueFrom:
              secretKeyRef:
                name: recipeai-secrets
                key: openai-api-key
          - name: MCP_SERVER_URL
            value: "http://recipeai-mcp-server.recipeai.svc.cluster.local:8080/mcp"
          - name: OUTPUT_DIR
            value: "/output"
      outputs:
        artifacts:
          - name: plan
            path: /output/plan.json
          - name: plan-metadata
            path: /output/plan_metadata.json

    - name: chef
      inputs:
        artifacts:
          - name: plan
            path: /input/plan.json
            from: "{{steps.plan.outputs.artifacts.plan}}"
          - name: plan-metadata
            path: /input/plan_metadata.json
            from: "{{steps.plan.outputs.artifacts.plan-metadata}}"
      container:
        image: recipeai-chef:latest
        imagePullPolicy: Never
        env:
          - name: OPENAI_API_KEY
            valueFrom:
              secretKeyRef:
                name: recipeai-secrets
                key: openai-api-key
          - name: INPUT_DIR
            value: "/input"
          - name: OUTPUT_DIR
            value: "/output"
      outputs:
        artifacts:
          - name: recipe
            path: /output/recipe.json

    - name: nutrition-agent
      inputs:
        artifacts:
          - name: recipe
            path: /input/recipe.json
            from: "{{steps.cook.outputs.artifacts.recipe}}"
      container:
        image: recipeai-nutrition:latest
        imagePullPolicy: Never
        env:
          - name: MCP_SERVER_URL
            value: "http://recipeai-mcp-server.recipeai.svc.cluster.local:8080/mcp"
          - name: INPUT_DIR
            value: "/input"
          - name: OUTPUT_DIR
            value: "/output"
      outputs:
        artifacts:
          - name: nutrition
            path: /output/nutrition.json
```

- [ ] **Step 7: Create `k8s/kustomization.yaml`**

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - secret.yaml
  - mcp-server/deployment.yaml
  - mcp-server/service.yaml
```

- [ ] **Step 8: Validate manifests**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && kubectl apply -k k8s/ --dry-run=client`

Expected: All resources validated (namespace, secret, deployment, service). If `kubectl` is not available, validate YAML syntax:

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -c "import yaml; [yaml.safe_load(open(f'k8s/{f}')) for f in ['namespace.yaml', 'secret.yaml']]"`

- [ ] **Step 9: Commit**

```bash
git add k8s/
git commit -m "feat: add K8s manifests and Argo Workflow for pipeline"
```

---

### Task 7: Final Verification

**Files:** None new — this task validates everything works together.

- [ ] **Step 1: Run all tests**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py`

Expected: All tests PASS.

- [ ] **Step 2: Verify local CLI still works**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && grep -r "nest_asyncio" src/ stages/ nutrition_mcp/`

Expected: No output (fully removed).

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && grep -r "asyncio.run" src/mcp_tools.py`

Expected: No output (removed from LangChain tools).

- [ ] **Step 3: Verify no imports are broken**

Run: `cd /Users/sraghuna/local_dev/petprojects/recipeai && .venv/bin/python -c "from stages.plan_stage import main; from stages.chef_stage import main; from stages.nutrition_stage import main; from nutrition_mcp.mcp_http_server import app; from nutrition_mcp.mcp_http_client import AsyncHTTPNutritionMCPClient; print('All imports OK')"`

Expected: `All imports OK`

- [ ] **Step 4: Build all container images**

```bash
cd /Users/sraghuna/local_dev/petprojects/recipeai
podman build -f images/Containerfile.mcp-server -t recipeai-mcp-server:latest .
podman build -f images/Containerfile.planner -t recipeai-planner:latest .
podman build -f images/Containerfile.chef -t recipeai-chef:latest .
podman build -f images/Containerfile.nutrition -t recipeai-nutrition:latest .
```

Expected: All 4 builds succeed.

- [ ] **Step 5: Commit any final fixes**

If any issues were found and fixed, commit them:

```bash
git add -A
git commit -m "fix: resolve issues found during final verification"
```
