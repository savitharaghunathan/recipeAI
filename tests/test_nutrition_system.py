#!/usr/bin/env python3
"""
Comprehensive tests for nutrition system
"""

import pytest
from src.models import Recipe, Ingredient
from nutrition_mcp.mcp_client import AsyncNutritionMCPClient


@pytest.fixture
async def mcp_client():
    client = AsyncNutritionMCPClient()
    await client.start_server()
    yield client
    await client.stop_server()


@pytest.mark.asyncio
async def test_mcp_server_connection(mcp_client):
    """Test basic MCP server connection"""
    result = await mcp_client.call_tool("get_database_stats", {})
    assert "database_statistics" in result
    assert result["database_statistics"]["total_foods"] > 300


@pytest.mark.asyncio
async def test_ingredient_lookup(mcp_client):
    """Test individual ingredient lookup"""
    result = await mcp_client.call_tool("find_ingredient", {
        "ingredient_name": "coconut milk",
        "max_results": 3,
    })
    assert "results_found" in result
    assert result["results_found"] > 0
    assert "matches" in result


@pytest.mark.asyncio
async def test_database_stats(mcp_client):
    """Test database statistics"""
    result = await mcp_client.call_tool("get_database_stats", {})
    stats = result["database_statistics"]
    assert stats["total_foods"] > 300
    assert stats["foods_by_source"]["usda"] > 300
    assert stats["foods_with_protein_data"] > 300
