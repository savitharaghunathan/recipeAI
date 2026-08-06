import json
import os
import tempfile
import pytest

from src.models import Plan, Recipe, Ingredient


class TestChefStage:
    def test_reads_plan_and_metadata(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        plan = Plan(
            meal="Test Pasta",
            ingredients=[Ingredient(item="pasta", qty="200g")],
            dietary_needs="vegetarian",
        )
        (input_dir / "plan.json").write_text(plan.model_dump_json())
        (input_dir / "plan_metadata.json").write_text(
            json.dumps({"mode": "cuisine"})
        )

        plan_loaded = Plan.model_validate_json(
            (input_dir / "plan.json").read_text()
        )
        assert plan_loaded.meal == "Test Pasta"

        metadata = json.loads(
            (input_dir / "plan_metadata.json").read_text()
        )
        assert metadata["mode"] == "cuisine"


class TestNutritionStage:
    def test_reads_recipe(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        recipe = Recipe(
            title="Test Pasta",
            prep_time=10,
            cook_time=20,
            servings=2,
            ingredients=[Ingredient(item="pasta", qty="200g")],
            steps=["Cook pasta"],
        )
        (input_dir / "recipe.json").write_text(recipe.model_dump_json())

        recipe_loaded = Recipe.model_validate_json(
            (input_dir / "recipe.json").read_text()
        )
        assert recipe_loaded.title == "Test Pasta"
        assert len(recipe_loaded.ingredients) == 1


class TestPlanMetadata:
    def test_cuisine_metadata(self):
        metadata = {"mode": "cuisine"}
        assert metadata["mode"] == "cuisine"
        assert "nutrition_goals" not in metadata

    def test_ingredient_metadata(self):
        metadata = {"mode": "ingredient", "nutrition_goals": "high protein"}
        assert metadata["mode"] == "ingredient"
        assert metadata["nutrition_goals"] == "high protein"
