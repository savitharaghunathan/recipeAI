import json
import re
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from pydantic import ValidationError

from models import Plan,Recipe

llm = OpenAI(
    model= "gpt-4o-mini",
    temperature=0.7,
)

prompt = PromptTemplate(
    input_variables=["plan_json"],
    template="""
You are a skilled chef. Given this meal plan:

{plan_json}

Generate a JSON object matching this schema:

{{
  "title": "string",
  "prep_time": 0,
  "cook_time": 0,
  "servings": 0,
  "ingredients": [
    {{ "item": "string", "qty": "string" }}
  ],
  "steps": ["string"]
}}

Only output the JSON.
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
    
    # Try direct JSON load, else extract substring
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Failed to parse JSON from chef output:\n{raw}")
        data = json.loads(match.group(0))

    # Validate against Recipe model
    try:
        recipe = Recipe.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Chef output did not match Recipe schema:\n{e}")
    
    return recipe

