import json
import os

from src.models import Plan, Recipe
from src.chef import generate_recipe, generate_nutrition_aware_recipe


def main():
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    plan_path = os.path.join(input_dir, "plan.json")
    with open(plan_path) as f:
        plan = Plan.model_validate_json(f.read())

    metadata_path = os.path.join(input_dir, "plan_metadata.json")
    with open(metadata_path) as f:
        metadata = json.load(f)

    mode = metadata["mode"]

    if mode == "ingredient":
        nutrition_goals = metadata.get("nutrition_goals", "balanced nutrition")
        recipe = generate_nutrition_aware_recipe(plan, nutrition_goals)
    else:
        recipe = generate_recipe(plan)

    recipe_path = os.path.join(output_dir, "recipe.json")
    with open(recipe_path, "w") as f:
        f.write(recipe.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
