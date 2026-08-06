#!/usr/bin/env python3
"""
Test MCP server communication
"""

import pytest
from nutrition_mcp.mcp_client import AsyncNutritionMCPClient


@pytest.mark.asyncio
async def test_mcp():
    """Test basic MCP communication"""
    client = AsyncNutritionMCPClient()
    await client.start_server()
    try:
        result = await client.call_tool("get_database_stats", {})
        assert "database_statistics" in result
    finally:
        await client.stop_server()
