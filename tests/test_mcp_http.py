import asyncio
import pytest
import threading
import time
import uvicorn
from starlette.testclient import TestClient

from nutrition_mcp.mcp_http_server import create_app
from nutrition_mcp.mcp_http_client import AsyncHTTPNutritionMCPClient
from src.models import Recipe, Ingredient


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as client:
        yield client


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


@pytest.fixture(scope="module")
def mcp_http_server():
    """Start MCP HTTP server in a background thread for testing."""
    app = create_app()
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


@pytest.mark.asyncio
async def test_mcp_client_manager_http_connect_failure_does_not_leak(monkeypatch):
    """Failed HTTP connect must not leave _client set without _transport."""
    from src.mcp_tools import MCPClientManager

    MCPClientManager._client = None
    MCPClientManager._transport = None
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:9/mcp")

    class FailingHTTPClient:
        def __init__(self, url):
            pass

        async def connect(self):
            raise ConnectionError("unreachable")

        async def close(self):
            pass

        async def stop_server(self):
            raise AssertionError("HTTP client has no stop_server()")

    monkeypatch.setattr(
        "nutrition_mcp.mcp_http_client.AsyncHTTPNutritionMCPClient",
        FailingHTTPClient,
    )

    with pytest.raises(ConnectionError, match="unreachable"):
        await MCPClientManager.start_server()

    assert MCPClientManager._client is None
    assert MCPClientManager._transport is None
    await MCPClientManager.stop_server()
