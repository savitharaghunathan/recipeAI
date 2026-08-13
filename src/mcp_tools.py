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
        if cls._client is not None:
            return
        mcp_server_url = os.environ.get("MCP_SERVER_URL")

        if mcp_server_url:
            from nutrition_mcp.mcp_http_client import AsyncHTTPNutritionMCPClient
            client = AsyncHTTPNutritionMCPClient(mcp_server_url)
            await client.connect()
            cls._client = client
            cls._transport = "http"
        else:
            from nutrition_mcp.mcp_client import AsyncNutritionMCPClient
            client = AsyncNutritionMCPClient()
            await client.start_server()
            cls._client = client
            cls._transport = "stdio"

    @classmethod
    async def stop_server(cls):
        if cls._client is None:
            return
        client = cls._client
        transport = cls._transport
        try:
            if transport == "http":
                await client.close()
            else:
                await client.stop_server()
        finally:
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
