from pydantic import BaseModel
from typing import List, Dict

class UserNeeds(BaseModel):
    """
    Represents the user’s top-level meal planning needs.
    - cuisine: e.g. 'Italian', 'Indian', 'Mexican'
    - max_prep_time: maximum preparation time in minutes
    """
    cuisine: str
    max_prep_time: int


class Ingredient(BaseModel):
    """
    A single ingredient with its quantity.
    - item: ingredient name, e.g. 'chickpeas'
    - qty: quantity string, e.g. '100g', '1 cup'

    """
    item: str
    qty: str

class Plan(BaseModel):
    """
    Output from the Planning Agent.
    - meal: proposed dish name
    - ingredients: list of Ingredient objects
    """

    meal: str
    ingredients: List[Ingredient]

class Recipe(BaseModel):
    """
    Output from the Chef Agent.
    - title: recipe name
    - prep_time: prep time in minutes
    - cook_time: cook time in minutes
    - steps: ordered list of cooking instructions
    - servings: number of servings
    """
    title: str
    prep_time: int
    cook_time: int
    ingredients: List[Ingredient]
    steps: List[str]
    servings: int

class NutritionProfile(BaseModel):
    """
    Output from the Nutrition Agent.
    - calories: total kcal
    - macros: dict of macros, e.g. {'carbs': 60, 'protein': 20, 'fat': 10}
    - micros: dict of micronutrients, e.g. {'iron_mg': 4.5, 'vitamin_c_mg': 20}
    """
    calories: float
    macros: Dict[str, float]
    micros: Dict[str, float]