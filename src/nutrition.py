"""
Nutrition calculation using MCP server
"""

import asyncio
import nest_asyncio
from src.models import Recipe, NutritionProfile
from src.mcp_tools import MCPClientManager

def compute_nutrition(recipe: Recipe) -> NutritionProfile:
    """Calculate nutrition using MCP server"""
    async def _compute_nutrition_async():
        client = MCPClientManager.get_client()
        result = await client.calculate_recipe_nutrition(recipe)
        
        if "error" in result:
            raise ValueError(f"MCP nutrition calculation failed: {result['error']}")
        
        recipe_nutrition = result.get("recipe_nutrition", {})
        
        nutrition_data = {
            "calories": recipe_nutrition.get("calories", 0.0),
            "macros": {
                "protein": recipe_nutrition.get("protein", 0.0),
                "fat": recipe_nutrition.get("fat", 0.0),
                "carbs": recipe_nutrition.get("carbs", 0.0)
            },
            "micros": {
                "iron_mg": recipe_nutrition.get("iron_mg", 0.0),
                "vitamin_c_mg": recipe_nutrition.get("vitamin_c_mg", 0.0),
                "calcium_mg": recipe_nutrition.get("calcium_mg", 0.0),
                "vitamin_a_mcg": recipe_nutrition.get("vitamin_a_mcg", 0.0),
                "vitamin_d_mcg": recipe_nutrition.get("vitamin_d_mcg", 0.0),
                "vitamin_e_mg": recipe_nutrition.get("vitamin_e_mg", 0.0),
                "vitamin_k_mcg": recipe_nutrition.get("vitamin_k_mcg", 0.0),
                "thiamin_mg": recipe_nutrition.get("thiamin_mg", 0.0),
                "riboflavin_mg": recipe_nutrition.get("riboflavin_mg", 0.0),
                "niacin_mg": recipe_nutrition.get("niacin_mg", 0.0),
                "vitamin_b6_mg": recipe_nutrition.get("vitamin_b6_mg", 0.0),
                "folate_mcg": recipe_nutrition.get("folate_mcg", 0.0),
                "vitamin_b12_mcg": recipe_nutrition.get("vitamin_b12_mcg", 0.0),
                "zinc_mg": recipe_nutrition.get("zinc_mg", 0.0),
                "magnesium_mg": recipe_nutrition.get("magnesium_mg", 0.0),
                "potassium_mg": recipe_nutrition.get("potassium_mg", 0.0),
                "sodium_mg": recipe_nutrition.get("sodium_mg", 0.0)
            }
        }
        
        return NutritionProfile.model_validate(nutrition_data)
    
    nest_asyncio.apply()
    return asyncio.run(_compute_nutrition_async())


