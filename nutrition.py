import json
import re
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from models import Recipe, NutritionProfile
from pydantic import ValidationError

llm = OpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    max_tokens=2000,
    timeout=30,
)

prompt = PromptTemplate(
    input_variables=["recipe_json"],
    template="""
You are a nutrition expert. Given this recipe with ingredients and quantities:

{recipe_json}

Calculate the total nutritional profile by:
1. Looking at each ingredient and its quantity
2. Estimating the nutritional content based on typical values for that ingredient

Output a JSON matching this schema:

{{
  "calories": float,   // total kilocalories per serving
  "macros": {{
    "carbs": float,    // grams of carbohydrates per serving
    "protein": float,  // grams of protein per serving
    "fat": float       // grams of fat per serving
  }},
  "micros": {{
    "iron_mg": float,        // milligrams of iron per serving
    "vitamin_c_mg": float,   // milligrams of vitamin C per serving
    "calcium_mg": float,     // milligrams of calcium per serving
    "vitamin_a_mcg": float,  // micrograms of vitamin A per serving
    "vitamin_d_mcg": float,  // micrograms of vitamin D per serving
    "vitamin_e_mg": float,   // milligrams of vitamin E per serving
    "vitamin_k_mcg": float,  // micrograms of vitamin K per serving
    "thiamin_mg": float,     // milligrams of thiamin (B1) per serving
    "riboflavin_mg": float,  // milligrams of riboflavin (B2) per serving
    "niacin_mg": float,      // milligrams of niacin (B3) per serving
    "vitamin_b6_mg": float,  // milligrams of vitamin B6 per serving
    "folate_mcg": float,     // micrograms of folate per serving
    "vitamin_b12_mcg": float, // micrograms of vitamin B12 per serving
    "zinc_mg": float,        // milligrams of zinc per serving
    "magnesium_mg": float,   // milligrams of magnesium per serving
    "potassium_mg": float,   // milligrams of potassium per serving
    "sodium_mg": float       // milligrams of sodium per serving
  }}
}}

IMPORTANT: Calculate based on the actual ingredients and quantities listed. Different ingredients should result in different nutritional profiles. Focus on micronutrients that are actually present in the ingredients (e.g., vitamin C in citrus, iron in leafy greens, calcium in dairy, etc.).

Be concise and output ONLY the JSON object.
"""
)


chain = prompt | llm

def _parse_json(raw: str) -> dict:
    """
    Attempt to load JSON, fallback by extracting substring.
    """
    # Check for empty response
    if not raw:
        raise ValueError("Nutrition expert returned an empty response. Please try again.")
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Try to extract JSON using regex
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"Failed to find JSON in nutrition output. Raw response:\n{raw}\n\nError: {e}")
        
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e2:
            raise ValueError(f"Failed to parse extracted JSON. Raw response:\n{raw}\n\nExtracted JSON:\n{m.group(0)}\n\nError: {e2}")


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
        raise ValueError(f"Nutrition schema mismatch:\n{e}\n\nParsed data:\n{data}")


