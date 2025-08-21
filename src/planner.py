
from json import JSONDecoder, JSONDecodeError
import re
from typing import Any, Dict
from langchain.prompts import PromptTemplate
from pydantic import ValidationError

from src.models import UserNeeds, Plan
from src.llm_config import get_completion_llm
prompt = PromptTemplate(
    input_variables=["cuisine", "max_prep_time", "dietary_needs"],
    template="""
You are a CREATIVE meal planner. Generate DIVERSE meals - avoid repetition!

User Constraints:
- Cuisine: {cuisine}
- Max prep time: {max_prep_time} minutes
- Dietary needs: {dietary_needs}

VARIETY IS KEY! Consider diverse options:
- Indian: biryani, dosa, samosas, different regional curries, street food, paneer dishes
- For any cuisine: think beyond the obvious - be creative with ingredients and techniques!

Produce exactly one JSON object, and nothing else, like:

{{
  "meal": "Vegetable Biryani",
  "ingredients": [
    {{ "item": "basmati rice", "qty": "200g" }},
    {{ "item": "mixed vegetables", "qty": "300g" }}
  ],
  "dietary_needs": "vegetarian"
}}

IMPORTANT: If dietary needs are specified (e.g., vegan, vegetarian), ensure the meal and ingredients comply with those restrictions.

Do NOT include any examples, explanation, or additional JSON objects—output only that one JSON.
""",
)

# Chain created dynamically with higher temperature for creativity
def get_planner_chain():
    return prompt | get_completion_llm(temperature=1.2)

def generate_plan(constraints: UserNeeds) -> Plan:
    # 1. Invoke LLM with higher temperature for creativity
    raw = get_planner_chain().invoke({
        "cuisine": constraints.cuisine,
        "max_prep_time": constraints.max_prep_time,
        "dietary_needs": constraints.dietary_needs
    })


    # Remove code blocks and extract JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    
    # Extract JSON object from response (handle extra text from higher temperature)
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)


    decoder = JSONDecoder()
    try:
        data: Dict[str, Any]
        data, _ = decoder.raw_decode(raw)
    except JSONDecodeError:
        raise ValueError(f"Could not parse JSON from planner output:\n{raw}")


    try:
        return Plan.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Planner output did not match Plan schema:\n{e}")
