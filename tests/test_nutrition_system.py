#!/usr/bin/env python3
"""
Comprehensive tests for nutrition system
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.models import Recipe, Ingredient
from src.nutrition import compute_nutrition
from nutrition_mcp.sync_mcp_client import SyncNutritionMCPClient

def test_mcp_server_connection():
    """Test basic MCP server connection"""
    print("Testing MCP server connection...")
    
    client = SyncNutritionMCPClient()
    try:
        client.start_server()
        result = client.call_tool("get_database_stats", {})
        assert "database_statistics" in result
        assert result["database_statistics"]["total_foods"] > 300
        print("✓ MCP server connection successful")
        return True
    except Exception as e:
        print(f"✗ MCP server connection failed: {e}")
        return False
    finally:
        client.stop_server()

def test_recipe_nutrition_calculation():
    """Test complete recipe nutrition calculation"""
    print("Testing recipe nutrition calculation...")
    
    recipe = Recipe(
        title="Test Coconut Curry",
        ingredients=[
            Ingredient(item="coconut milk", qty="200"),
            Ingredient(item="lime juice", qty="30")
        ],
        steps=["Mix ingredients", "Serve"],
        prep_time=5,
        cook_time=10,
        servings=2
    )
    
    try:
        nutrition = compute_nutrition(recipe)
        
        # Basic nutrition checks
        assert nutrition.calories > 0, "Calories should be > 0"
        assert nutrition.macros['protein'] >= 0, "Protein should be >= 0"
        assert nutrition.macros['fat'] > 0, "Fat should be > 0 (coconut milk)"
        assert nutrition.micros['vitamin_c_mg'] > 0, "Vitamin C should be > 0 (lime juice)"
        
        print(f" Recipe nutrition: {nutrition.calories} cal, {nutrition.macros['protein']}g protein")
        return True
        
    except Exception as e:
        print(f" Recipe nutrition calculation failed: {e}")
        return False

def test_ingredient_lookup():
    """Test individual ingredient lookup"""
    print("Testing ingredient lookup...")
    
    client = SyncNutritionMCPClient()
    try:
        client.start_server()
        
        # Test finding coconut milk
        result = client.call_tool("find_ingredient", {
            "ingredient_name": "coconut milk",
            "max_results": 3
        })
        
        assert "results_found" in result
        assert result["results_found"] > 0
        assert "matches" in result
        
        print(f"✓ Found {result['results_found']} matches for coconut milk")
        return True
        
    except Exception as e:
        print(f"✗ Ingredient lookup failed: {e}")
        return False
    finally:
        client.stop_server()

def test_database_stats():
    """Test database statistics"""
    print("Testing database statistics...")
    
    client = SyncNutritionMCPClient()
    try:
        client.start_server()
        
        result = client.call_tool("get_database_stats", {})
        stats = result["database_statistics"]
        
        assert stats["total_foods"] > 300
        assert stats["foods_by_source"]["usda"] > 300
        assert stats["foods_with_protein_data"] > 300
        
        print(f"✓ Database has {stats['total_foods']} foods")
        print(f"  USDA foods: {stats['foods_by_source']['usda']}")
        print(f"  LLM estimates: {stats['foods_by_source']['llm_estimate']}")
        return True
        
    except Exception as e:
        print(f"✗ Database stats failed: {e}")
        return False
    finally:
        client.stop_server()

def run_all_tests():
    """Run all nutrition system tests"""
    print("=== Nutrition System Tests ===\n")
    
    tests = [
        test_mcp_server_connection,
        test_database_stats,
        test_ingredient_lookup,
        test_recipe_nutrition_calculation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f" Test {test.__name__} crashed: {e}")
        print()
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)