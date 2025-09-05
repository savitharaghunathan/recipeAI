"""
MCP wrapper for nutrition tools
"""

import json
import asyncio
from nutrition_mcp.mcp_client import AsyncNutritionMCPClient
from langchain.tools import BaseTool
from typing import Any, Dict, List, Optional
import nest_asyncio


class MCPClientManager:
    """Singleton manager for async MCP client"""
    
    _instance = None
    _client: Optional[AsyncNutritionMCPClient] = None
    _nest_asyncio_applied = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def start_server(cls):
        """Start MCP server and client"""
        if not cls._nest_asyncio_applied:
            nest_asyncio.apply()
            cls._nest_asyncio_applied = True
            
        if cls._client is None:
            cls._client = AsyncNutritionMCPClient()
            await cls._client.start_server()
    
    @classmethod
    async def stop_server(cls):
        """Stop MCP server and client"""
        if cls._client is not None:
            await cls._client.stop_server()
            cls._client = None
    
    @classmethod
    def get_client(cls) -> AsyncNutritionMCPClient:
        """Get the running MCP client"""
        if cls._client is None:
            raise RuntimeError("MCP client not started. Call start_server() first.")
        return cls._client


class FindIngredientTool(BaseTool):
    """Tool to find nutrition data for ingredients using fuzzy matching"""
    
    name: str = "find_ingredient"
    description: str = "Find nutrition data for an ingredient using fuzzy matching. Returns matches with nutrition information."
    
    def _run(self, tool_input) -> str:
        """Find ingredient nutrition data"""
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            
            ingredient_name = params.get("ingredient_name")
            max_results = params.get("max_results", 5)
            
            return asyncio.run(self._find_ingredient_async(ingredient_name, max_results))
        except Exception as e:
            return f"Error finding ingredient: {str(e)}"
    
    async def _find_ingredient_async(self, ingredient_name: str, max_results: int) -> str:
        """Async implementation for finding ingredient nutrition data"""
        client = MCPClientManager.get_client()
        result = await client.call_tool(
            "find_ingredient", 
            {"ingredient_name": ingredient_name, "max_results": max_results}
        )
        return str(result)


class CalculateRecipeNutritionTool(BaseTool):
    """Tool to calculate total nutrition for a recipe with ingredients and quantities"""
    
    name: str = "calculate_recipe_nutrition"
    description: str = "Calculate total nutrition for a recipe. Input should be a list of ingredients with names and quantities in grams."
    
    def _run(self, tool_input) -> str:
        """Calculate recipe nutrition"""
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
                
            return asyncio.run(self._calculate_nutrition_async(ingredients_data))
        except Exception as e:
            return f"Error calculating recipe nutrition: {str(e)}"
    
    async def _calculate_nutrition_async(self, ingredients_data: list) -> str:
        """Async implementation for calculating recipe nutrition"""
        client = MCPClientManager.get_client()
        result = await client.call_tool(
            "calculate_recipe_nutrition",
            {"ingredients": ingredients_data}
        )
        return str(result)


class GetHighProteinFoodsTool(BaseTool):
    """Tool to find foods with high protein content"""
    
    name: str = "get_high_protein_foods"
    description: str = "Find foods with protein content above a specified threshold. Useful for suggesting high-protein ingredients."
    
    def _run(self, tool_input) -> str:
        """Get high protein foods"""
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            
            min_protein = params.get("min_protein", 20.0)
            
            return asyncio.run(self._get_high_protein_async(min_protein))
        except Exception as e:
            return f"Error getting high protein foods: {str(e)}"
    
    async def _get_high_protein_async(self, min_protein: float) -> str:
        """Async implementation for getting high protein foods"""
        client = MCPClientManager.get_client()
        result = await client.call_tool(
            "get_high_protein_foods",
            {"min_protein": min_protein}
        )
        return str(result)


class SearchIngredientsTool(BaseTool):
    """Tool to search ingredients by description keywords"""
    
    name: str = "search_ingredients"
    description: str = "Search for ingredients using keywords in food descriptions. Useful for finding specific types of foods."
    
    def _run(self, tool_input) -> str:
        """Search ingredients by description"""
        try:
            if isinstance(tool_input, str):
                params = json.loads(tool_input)
            else:
                params = tool_input
            
            description = params.get("description")
            
            return asyncio.run(self._search_ingredients_async(description))
        except Exception as e:
            return f"Error searching ingredients: {str(e)}"
    
    async def _search_ingredients_async(self, description: str) -> str:
        """Async implementation for searching ingredients by description"""
        client = MCPClientManager.get_client()
        result = await client.call_tool(
            "search_ingredients",
            {"description": description}
        )
        return str(result)


def get_nutrition_tools():
    """Get all nutrition tools for LangChain agents"""
    return [
        FindIngredientTool(),
        CalculateRecipeNutritionTool(),
        GetHighProteinFoodsTool(),
        SearchIngredientsTool()
    ]