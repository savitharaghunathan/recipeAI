"""
Nutrition calculation using MCP server
"""

from src.models import Recipe, NutritionProfile
from nutrition_mcp.nutrition_mcp_client import compute_nutrition_mcp

def compute_nutrition(recipe: Recipe) -> NutritionProfile:
    """Calculate nutrition using MCP server."""
    return compute_nutrition_mcp(recipe)


