"""
MCP wrapper for nutrition tools
"""

import json
from nutrition_mcp.sync_mcp_client import SyncNutritionMCPClient
from langchain.tools import BaseTool
from typing import Any, Dict, List, Optional


class SyncMCPClientManager:
    """Singleton manager for sync MCP client"""
    
    _instance = None
    _client: Optional[SyncNutritionMCPClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def start_server(cls):
        """Start MCP server and client"""
        if cls._client is None:
            cls._client = SyncNutritionMCPClient()
            cls._client.start_server()
    
    @classmethod
    def stop_server(cls):
        """Stop MCP server and client"""
        if cls._client is not None:
            cls._client.stop_server()
            cls._client = None
    
    @classmethod
    def get_client(cls) -> SyncNutritionMCPClient:
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
            
            client = SyncMCPClientManager.get_client()
            result = client.call_tool(
                "find_ingredient", 
                {"ingredient_name": ingredient_name, "max_results": max_results}
            )
            return str(result)
        except Exception as e:
            return f"Error finding ingredient: {str(e)}"


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
                
            client = SyncMCPClientManager.get_client()
            result = client.call_tool(
                "calculate_recipe_nutrition",
                {"ingredients": ingredients_data}
            )
            return str(result)
        except Exception as e:
            return f"Error calculating recipe nutrition: {str(e)}"


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
            
            client = SyncMCPClientManager.get_client()
            result = client.call_tool(
                "get_high_protein_foods",
                {"min_protein": min_protein}
            )
            return str(result)
        except Exception as e:
            return f"Error getting high protein foods: {str(e)}"


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
            
            client = SyncMCPClientManager.get_client()
            result = client.call_tool(
                "search_ingredients",
                {"description": description}
            )
            return str(result)
        except Exception as e:
            return f"Error searching ingredients: {str(e)}"


def get_nutrition_tools():
    """Get all nutrition tools for LangChain agents"""
    return [
        FindIngredientTool(),
        CalculateRecipeNutritionTool(),
        GetHighProteinFoodsTool(),
        SearchIngredientsTool()
    ]