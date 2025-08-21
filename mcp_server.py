#!/usr/bin/env python3
"""
MCP Server for Nutrition Database

Provides nutrition data from TinyDB as MCP resources and tools for AI agents.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from database import NutritionDB

class NutritionMCPServer:
    """MCP Server for nutrition database operations"""
    
    def __init__(self):
        self.server = Server("nutrition-db")
        self.db_path = "data/nutrition.json"
        self.nutrition_db = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all MCP handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="find_ingredient",
                    description="Find nutrition data for an ingredient using fuzzy matching",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ingredient_name": {
                                "type": "string",
                                "description": "Name of the ingredient to search for"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["ingredient_name"]
                    }
                ),
                types.Tool(
                    name="get_nutrition_by_id",
                    description="Get nutrition data by exact food_id",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "food_id": {
                                "type": "string",
                                "description": "Exact food_id to look up"
                            }
                        },
                        "required": ["food_id"]
                    }
                ),
                types.Tool(
                    name="search_ingredients",
                    description="Search ingredients by description keywords",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Keywords to search for in food descriptions"
                            }
                        },
                        "required": ["description"]
                    }
                ),
                types.Tool(
                    name="add_ingredient",
                    description="Add new ingredient using LLM nutrition estimation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ingredient_name": {
                                "type": "string",
                                "description": "Name of the ingredient to add"
                            }
                        },
                        "required": ["ingredient_name"]
                    }
                ),
                types.Tool(
                    name="get_high_protein_foods",
                    description="Find foods with protein content above threshold",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "min_protein": {
                                "type": "number",
                                "description": "Minimum protein content in grams per 100g",
                                "default": 20.0
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_database_stats",
                    description="Get comprehensive database statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="calculate_recipe_nutrition",
                    description="Calculate total nutrition for a recipe with ingredients and quantities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "description": "List of ingredients with names and quantities",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Ingredient name"},
                                        "quantity_grams": {"type": "number", "description": "Quantity in grams"}
                                    },
                                    "required": ["name", "quantity_grams"]
                                }
                            }
                        },
                        "required": ["ingredients"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Handle tool calls"""
            
            # Initialize database if needed (without LLM to avoid API key requirements)
            if not self.nutrition_db:
                self.nutrition_db = NutritionDB(self.db_path, enable_llm=False)
            
            try:
                if name == "find_ingredient":
                    ingredient_name = arguments["ingredient_name"]
                    max_results = arguments.get("max_results", 5)
                    
                    results = self.nutrition_db.find_ingredient(ingredient_name, max_results)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "ingredient_searched": ingredient_name,
                            "results_found": len(results),
                            "matches": results
                        }, indent=2)
                    )]
                
                elif name == "get_nutrition_by_id":
                    food_id = arguments["food_id"]
                    result = self.nutrition_db.get_food_by_id(food_id)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "food_id": food_id,
                            "found": result is not None,
                            "data": result
                        }, indent=2)
                    )]
                
                elif name == "search_ingredients":
                    description = arguments["description"]
                    results = self.nutrition_db.search_by_description(description)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "search_term": description,
                            "results_found": len(results),
                            "matches": results
                        }, indent=2)
                    )]
                
                elif name == "add_ingredient":
                    ingredient_name = arguments["ingredient_name"]
                    result = self.nutrition_db.find_or_create_ingredient(ingredient_name, auto_add=False)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "ingredient_name": ingredient_name,
                            "added": result is not None,
                            "data": result
                        }, indent=2)
                    )]
                
                elif name == "get_high_protein_foods":
                    min_protein = arguments.get("min_protein", 20.0)
                    results = self.nutrition_db.get_high_protein_foods(min_protein)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "min_protein_threshold": min_protein,
                            "foods_found": len(results),
                            "high_protein_foods": results
                        }, indent=2)
                    )]
                
                elif name == "get_database_stats":
                    stats = self.nutrition_db.get_database_stats()
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "database_statistics": stats
                        }, indent=2)
                    )]
                
                elif name == "calculate_recipe_nutrition":
                    ingredients = arguments["ingredients"]
                    
                    # Calculate total nutrition for recipe
                    # All nutrition fields from database
                    total_nutrition = {
                        "calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0,
                        "iron_mg": 0, "calcium_mg": 0, "zinc_mg": 0, "magnesium_mg": 0,
                        "potassium_mg": 0, "sodium_mg": 0, "vitamin_c_mg": 0,
                        "vitamin_a_mcg": 0, "vitamin_d_mcg": 0, "vitamin_e_mg": 0,
                        "vitamin_k_mcg": 0, "thiamin_mg": 0, "riboflavin_mg": 0,
                        "niacin_mg": 0, "vitamin_b6_mg": 0, "folate_mcg": 0, "vitamin_b12_mcg": 0
                    }
                    
                    ingredient_details = []
                    
                    for ingredient in ingredients:
                        name = ingredient["name"]
                        quantity_grams = ingredient["quantity_grams"]
                        
                        # Find ingredient nutrition data (no auto-add to avoid LLM)
                        food_data = self.nutrition_db.find_or_create_ingredient(name, auto_add=False)
                        
                        # If not found, try fuzzy matching only
                        if not food_data:
                            matches = self.nutrition_db.find_ingredient(name, max_results=1)
                            if matches and matches[0].get('match_score', 0) >= 0.7:
                                food_data = matches[0]
                            else:
                                ingredient_details.append({
                                    "name": name,
                                    "quantity_grams": quantity_grams,
                                    "error": f"No nutrition data found for '{name}'"
                                })
                                continue
                        
                        if food_data:
                            # Scale nutrition data based on quantity (data is per 100g)
                            scale_factor = quantity_grams / 100.0
                            
                            ingredient_nutrition = {}
                            for nutrient in total_nutrition.keys():
                                value = food_data.get(nutrient, 0) * scale_factor
                                total_nutrition[nutrient] += value
                                ingredient_nutrition[nutrient] = round(value, 2)
                            
                            ingredient_details.append({
                                "name": name,
                                "quantity_grams": quantity_grams,
                                "nutrition": ingredient_nutrition,
                                "food_id": food_data.get("food_id"),
                                "source": food_data.get("source")
                            })
                        else:
                            ingredient_details.append({
                                "name": name,
                                "quantity_grams": quantity_grams,
                                "error": "Could not find or estimate nutrition data"
                            })
                    
                    # Round total values
                    for nutrient in total_nutrition:
                        total_nutrition[nutrient] = round(total_nutrition[nutrient], 2)
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "recipe_nutrition": total_nutrition,
                            "ingredient_breakdown": ingredient_details
                        }, indent=2)
                    )]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, indent=2)
                )]
    
    def cleanup(self):
        """Clean up resources"""
        if self.nutrition_db:
            self.nutrition_db.close()
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="nutrition-db",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

async def main():
    """Main entry point"""
    server = NutritionMCPServer()
    try:
        await server.run()
    finally:
        server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())