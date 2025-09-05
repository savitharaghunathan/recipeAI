import json
import argparse
import asyncio
from src.models import UserNeeds
from src.planner import generate_plan
from src.chef import generate_recipe, generate_nutrition_aware_recipe
from src.nutrition import compute_nutrition
from src.ingredient_planner import generate_ingredient_plan
from src.mcp_tools import MCPClientManager


def main():
    parser = argparse.ArgumentParser(description="Generate a recipe and nutrition profile.")
    
    parser.add_argument(
        "--mode", choices=["cuisine", "ingredient"], default="cuisine",
        help="Recipe generation mode: 'cuisine' (traditional) or 'ingredient' (AI agent-based)"
    )
    
    parser.add_argument(
        "--cuisine", 
        help="Cuisine type (e.g., Indian, Italian, Mexican) - required for cuisine mode"
    )
    parser.add_argument(
        "--max-prep-time", type=int,
        help="Maximum preparation time in minutes - required for cuisine mode"
    )
    parser.add_argument(
        "--dietary-needs", 
        help="Dietary needs (e.g., vegan, vegetarian, gluten-free)"
    )
    
    parser.add_argument(
        "--request",
        help="Natural language recipe request (e.g., 'high protein vegetarian recipe with potatoes') - required for ingredient mode"
    )
    parser.add_argument(
        "--nutrition-goals",
        help="Nutrition optimization goals (e.g., 'high protein', 'low carb', 'balanced')"
    )
    
    args = parser.parse_args()
    
    if args.mode == "cuisine":
        if not args.cuisine or not args.max_prep_time:
            parser.error("Cuisine mode requires --cuisine and --max-prep-time")
    elif args.mode == "ingredient":
        if not args.request:
            parser.error("Ingredient mode requires --request")


    if args.mode == "cuisine":
        asyncio.run(run_cuisine_mode(args))
        
    elif args.mode == "ingredient":
        asyncio.run(run_ingredient_mode(args))


async def run_cuisine_mode(args):
    """Run traditional cuisine-based recipe generation"""
    try:
        await MCPClientManager.start_server()
        
        try:
            constraints = UserNeeds(
                cuisine=args.cuisine,
                max_prep_time=args.max_prep_time,
                dietary_needs=args.dietary_needs
            )
            plan = generate_plan(constraints)
            recipe = generate_recipe(plan)
            nutrition = await compute_nutrition(recipe)
        except Exception:
            await MCPClientManager.stop_server()
            raise
        
        formatted_nutrition = {
            "calories": f"{nutrition.calories} kcal",
            "macros": {k: f"{v} g" for k, v in nutrition.macros.items()},
            "micros": {k: f"{v} mg" for k, v in nutrition.micros.items()},
        }

        output = {
            "plan": plan.model_dump(),
            "recipe": recipe.model_dump(),
            "nutrition": formatted_nutrition,
        }
        print(json.dumps(output, indent=2))
        
    finally:
        await MCPClientManager.stop_server()


async def run_ingredient_mode(args):
    """Run ingredient-based recipe generation with AI agents"""
    try:
        await MCPClientManager.start_server()
        
        try:
            plan = generate_ingredient_plan(args.request)
            
            nutrition_goals = args.nutrition_goals or "balanced nutrition"
            recipe = generate_nutrition_aware_recipe(plan, nutrition_goals)
            
            nutrition = await compute_nutrition(recipe)
        except Exception:
            await MCPClientManager.stop_server()
            raise
        
        formatted_nutrition = {
            "calories": f"{nutrition.calories} kcal",
            "macros": {k: f"{v} g" for k, v in nutrition.macros.items()},
            "micros": {k: f"{v} mg" for k, v in nutrition.micros.items()},
        }

        output = {
            "plan": plan.model_dump(),
            "recipe": recipe.model_dump(),
            "nutrition": formatted_nutrition,
        }
        print(json.dumps(output, indent=2))
        
    finally:
        await MCPClientManager.stop_server()

if __name__ == "__main__":
    main()