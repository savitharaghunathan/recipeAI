import argparse
import asyncio
import json
import os
import sys

from src.models import UserNeeds
from src.planner import generate_plan
from src.ingredient_planner import generate_ingredient_plan
from src.mcp_tools import MCPClientManager


async def run(args):
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    metadata = {"mode": args.mode}

    if args.mode == "cuisine":
        constraints = UserNeeds(
            cuisine=args.cuisine,
            max_prep_time=args.max_prep_time,
            dietary_needs=args.dietary_needs,
        )
        plan = generate_plan(constraints)
    else:
        await MCPClientManager.start_server()
        try:
            plan = await generate_ingredient_plan(args.request)
        finally:
            await MCPClientManager.stop_server()
        metadata["nutrition_goals"] = args.nutrition_goals or "balanced nutrition"

    plan_path = os.path.join(output_dir, "plan.json")
    with open(plan_path, "w") as f:
        f.write(plan.model_dump_json(indent=2))

    metadata_path = os.path.join(output_dir, "plan_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="RecipeAI Plan Stage")
    parser.add_argument("--mode", choices=["cuisine", "ingredient"], required=True)
    parser.add_argument("--cuisine", help="Cuisine type")
    parser.add_argument("--max-prep-time", type=int, help="Max prep time in minutes")
    parser.add_argument("--dietary-needs", help="Dietary restrictions")
    parser.add_argument("--request", help="Natural language recipe request")
    parser.add_argument("--nutrition-goals", help="Nutrition goals")

    args = parser.parse_args()

    if args.mode == "cuisine":
        if not args.cuisine or not args.max_prep_time:
            parser.error("Cuisine mode requires --cuisine and --max-prep-time")
    elif args.mode == "ingredient":
        if not args.request:
            parser.error("Ingredient mode requires --request")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
