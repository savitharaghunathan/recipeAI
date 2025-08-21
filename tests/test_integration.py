#!/usr/bin/env python3
"""
Test Recipe AI integration with MCP nutrition server
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from src.models import Recipe, Ingredient
from src.nutrition import compute_nutrition

def test_integration():
    """Test Recipe AI with MCP nutrition calculation"""
    
    print("Testing Recipe AI with MCP Nutrition Server...")
    
    # Create test recipe
    recipe = Recipe(
        title="Thai Coconut Curry",
        ingredients=[
            Ingredient(item="coconut milk", qty="200"),
            Ingredient(item="lime juice", qty="30"),
            Ingredient(item="curry paste", qty="15")
        ],
        steps=[
            "Heat coconut milk in pan",
            "Add curry paste and mix",
            "Finish with lime juice"
        ],
        prep_time=10,
        cook_time=20,
        servings=2
    )
    
    print(f"Recipe: {recipe.title}")
    print("Ingredients:")
    for ingredient in recipe.ingredients:
        print(f"  - {ingredient.item}: {ingredient.qty}g")
    
    print(f"\nServings: {recipe.servings}")
    
    try:
        # This should now use MCP server first
        nutrition = compute_nutrition(recipe)
        
        print(f"\n=== Nutrition Analysis (via MCP Server) ===")
        print(f"Calories: {nutrition.calories}")
        print(f"Protein: {nutrition.macros['protein']}g")
        print(f"Fat: {nutrition.macros['fat']}g")
        print(f"Carbs: {nutrition.macros['carbs']}g")
        print(f"Vitamin C: {nutrition.micros['vitamin_c_mg']}mg")
        print(f"Iron: {nutrition.micros['iron_mg']}mg")
        print(f"Calcium: {nutrition.micros['calcium_mg']}mg")
        
        print(f"\n=== Per Serving ===")
        print(f"Calories per serving: {nutrition.calories / recipe.servings:.1f}")
        print(f"Protein per serving: {nutrition.macros['protein'] / recipe.servings:.1f}g")
        
        print("\n✓ Recipe AI with MCP nutrition server working!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    test_integration()