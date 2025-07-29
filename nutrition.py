import json
import re
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from models import Recipe, NutritionProfile
from pydantic import ValidationError

llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
)

prompt = PromptTemplate(
    input_variables=["recipe_json"],
    template="""
You are a nutrition expert. Given this recipe with ingredients and quantities:

{recipe_json}

Estimate the total nutritional profile and output a JSON matching this schema:

{{
  "calories": float,   // total kilocalories
  "macros": {{
    "carbs": float,    // grams of carbohydrates
    "protein": float,  // grams of protein
    "fat": float       // grams of fat
  }},
  "micros": {{
    "iron_mg": float,        // milligrams of iron
    "vitamin_c_mg": float    // milligrams of vitamin C
  }}
}}

Be concise and output ONLY the JSON object.
"""
)


chain = prompt | llm

def _parse_json(raw: str) -> dict:
    """
    Attempt to load JSON, fallback by extracting substring.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"Cannot parse JSON: {raw}")
        return json.loads(m.group(0))


def compute_nutrition(recipe: Recipe) -> NutritionProfile:
    """
    Given a Recipe, use the LLM to estimate a NutritionProfile.
    """
    recipe_json = recipe.model_dump_json()
    raw: str = chain.invoke({"recipe_json": recipe_json}).strip()
    data = _parse_json(raw)

    try:
        return NutritionProfile.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Nutrition schema mismatch:\n{e}")


