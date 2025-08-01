import json
import re
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from pydantic import ValidationError

from models import Plan,Recipe

llm = OpenAI(
    model= "gpt-4o-mini",
    temperature=0.7,
    max_tokens=2000,  
    timeout=30,  
)

prompt = PromptTemplate(
    input_variables=["plan_json"],
    template="""
You are a skilled chef. Given this meal plan:

{plan_json}

Generate a complete JSON object matching this schema:

{{
  "title": "string",
  "prep_time": int,
  "cook_time": int,
  "servings": int,
  "ingredients": [
    {{ "item": "string", "qty": "string" }}
  ],
  "steps": ["string"]
}}

IMPORTANT: If the meal plan includes dietary needs (e.g., vegan, vegetarian), ensure your recipe and ingredients comply with those restrictions.

CRITICAL: Return ONLY the JSON object. No other text, no explanations, no markdown formatting.
""",
)

chain = prompt | llm

def generate_recipe(plan: Plan) -> Recipe:
    """
    Take a Plan, call the LLM, parse and validate into a Recipe.
    """
    # Serialize the Plan to JSON for the prompt
    plan_json = plan.model_dump_json()
    
    # Invoke the chain
    raw: str = chain.invoke({"plan_json": plan_json}).strip()
    
    # Check for empty response
    if not raw:
        raise ValueError("Chef returned an empty response. Please try again.")
    

    
    # Try direct JSON load, else extract substring
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Failed to parse JSON from chef output:\n{raw}")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse extracted JSON. Raw response:\n{raw}")

    # Validate against Recipe model
    try:
        recipe = Recipe.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Chef output did not match Recipe schema:\n{e}")
    
    return recipe

