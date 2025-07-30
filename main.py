import json
import argparse
from models import UserNeeds
from planner import generate_plan
from chef import generate_recipe
from nutrition import compute_nutrition


def main():

    parser = argparse.ArgumentParser(description="Generate a recipe and nutrition profile based on cuisine and prep time.")
    parser.add_argument(
        "--cuisine", required=True,
        help="Cuisine type (e.g., Indian, Italian, Mexican)"
    )
    parser.add_argument(
        "--max-prep-time", type=int, required=True,
        help="Maximum preparation time in minutes"
    )
    parser.add_argument(
        "--dietary-needs", required=False,
        help="Dietary needs (e.g., vegan, vegetarian, gluten-free)"
    )
    args = parser.parse_args()


    constraints = UserNeeds(
        cuisine=args.cuisine,
        max_prep_time=args.max_prep_time,
        dietary_needs=args.dietary_needs
    )
    plan = generate_plan(constraints)


    recipe = generate_recipe(plan)


    nutrition = compute_nutrition(recipe)


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

if __name__ == "__main__":
    main()