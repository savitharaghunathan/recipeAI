import asyncio
import json
import os
import sys

from src.models import Recipe, NutritionProfile
from src.nutrition import compute_nutrition
from src.mcp_tools import MCPClientManager


async def run():
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    recipe_path = os.path.join(input_dir, "recipe.json")
    with open(recipe_path) as f:
        recipe = Recipe.model_validate_json(f.read())

    await MCPClientManager.start_server()
    try:
        nutrition = await compute_nutrition(recipe)
    finally:
        await MCPClientManager.stop_server()

    mcg_nutrients = {
        "vitamin_a_mcg", "vitamin_d_mcg", "vitamin_k_mcg",
        "folate_mcg", "vitamin_b12_mcg",
    }

    formatted = {
        "calories": f"{nutrition.calories} kcal",
        "macros": {k: f"{v} g" for k, v in nutrition.macros.items()},
        "micros": {
            k: f"{v} mcg" if k in mcg_nutrients else f"{v} mg"
            for k, v in nutrition.micros.items()
        },
    }

    nutrition_path = os.path.join(output_dir, "nutrition.json")
    with open(nutrition_path, "w") as f:
        json.dump(formatted, f, indent=2)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
