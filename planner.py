
from json import JSONDecoder, JSONDecodeError
import re
from typing import Any, Dict
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from pydantic import ValidationError

from  models import UserNeeds, Plan

llm = OpenAI(model="gpt-4o-mini",
             temperature=0.9,
             )
prompt = PromptTemplate(
    input_variables=["cuisine", "max_prep_time"],
    template="""
You are a meal planner.

User Constraints:
- Cuisine: {cuisine}
- Max prep time: {max_prep_time} minutes

Produce exactly one JSON object, and nothing else, like:

{{
  "meal": "Red Lentil Dahl",
  "ingredients": [
    {{ "item": "red lentils", "qty": "100g" }},
    {{ "item": "spinach",     "qty": "50g"   }}
  ]
}}

Do NOT include any examples, explanation, or additional JSON objects—output only that one JSON.
""",
)

chain = prompt | llm

def generate_plan(constraints: UserNeeds) -> Plan:
    # 1. Invoke LLM
    raw = chain.invoke({
        "cuisine": constraints.cuisine,
        "max_prep_time": constraints.max_prep_time,
    })


    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()


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
