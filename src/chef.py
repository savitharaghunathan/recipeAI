import json
import re
from langchain.prompts import PromptTemplate
from pydantic import ValidationError

from src.models import Plan, Recipe
from src.llm_config import get_completion_llm
from src.agent_utils import create_agent_executor, run_agent_with_parsing

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

# Chain created dynamically with increased temperature for recipe variation
def get_chef_chain():
    return prompt | get_completion_llm(temperature=1.1)

def generate_recipe(plan: Plan) -> Recipe:
    """
    Take a Plan, call the LLM, parse and validate into a Recipe.
    """
    # Serialize the Plan to JSON for the prompt
    plan_json = plan.model_dump_json()
    
    # Invoke the chain
    raw: str = get_chef_chain().invoke({"plan_json": plan_json}).strip()
    
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


# Simplified nutrition-aware chef prompt
NUTRITION_CHEF_PROMPT = PromptTemplate(
    input_variables=["plan_json", "nutrition_goals"],
    template="""
You are a nutrition-aware chef. Create a detailed recipe from the meal plan optimized for the nutrition goals.

MEAL PLAN: {plan_json}
NUTRITION GOALS: {nutrition_goals}

Instructions:
1. Create a complete recipe with realistic cooking steps
2. Respect the nutrition goals exactly as specified:
   - "balanced" = keep it balanced, don't add extra high-protein ingredients
   - "high protein" = add protein-rich ingredients like beans, nuts, tofu
   - "low carb" = minimize carbohydrates
   - If no specific goals, keep it simple and tasty
3. Include prep time, cook time, and servings
4. Use realistic quantities and clear cooking instructions
5. Don't change the core ingredients from the meal plan unless nutrition goals require it

Return ONLY a valid JSON object with this exact format:

{{
  "title": "descriptive recipe title",
  "prep_time": 15,
  "cook_time": 30,
  "servings": 4,
  "ingredients": [
    {{"item": "ingredient name", "qty": "realistic quantity"}}
  ],
  "steps": [
    "Step 1 description",
    "Step 2 description"
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text.
"""
)


def generate_nutrition_aware_recipe(plan: Plan, nutrition_goals: str = "balanced nutrition") -> Recipe:
    """
    Generate a nutrition-optimized recipe using direct LLM call
    """
    # Create a simple LLM chain instead of agent
    chain = NUTRITION_CHEF_PROMPT | get_completion_llm(temperature=0.8)
    
    # Get response from LLM
    raw_response = chain.invoke({
        "plan_json": plan.model_dump_json(),
        "nutrition_goals": nutrition_goals
    }).strip()
    
    # Parse JSON response
    try:
        # Extract first valid JSON block from response
        # Look for JSON between ```json and ``` or standalone JSON
        json_pattern = r'```json\s*(\{.*?\})\s*```|\{.*?\}'
        matches = re.findall(json_pattern, raw_response, re.DOTALL)
        
        if matches:
            # Use first match - either from code block or standalone
            json_text = matches[0] if matches[0] else raw_response[raw_response.find('{'):raw_response.rfind('}')+1]
        else:
            # Fallback to simple extraction
            json_match = re.search(r'\{.*?\}', raw_response, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON found in response: {raw_response}")
            json_text = json_match.group(0)
        
        data = json.loads(json_text)
        
        # Validate and create Recipe object
        recipe = Recipe.model_validate(data)
        return recipe
        
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to parse response into Recipe: {e}\nRaw response: {raw_response}")

