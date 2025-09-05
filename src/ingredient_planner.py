"""
Ingredient-based planner agent using LangChain and MCP nutrition tools
"""

from langchain.prompts import PromptTemplate

from src.models import Plan, Ingredient  
from src.agent_utils import create_agent_executor, run_agent_with_parsing


# ReAct prompt with clear examples
INGREDIENT_PLANNER_PROMPT = PromptTemplate(
    input_variables=["tools", "tool_names", "request", "agent_scratchpad"],
    template="""You are a meal planner that follows user requests exactly. Create simple meal plans based on what the user asks for.

TOOLS AVAILABLE:
{tools}

TOOL NAMES: {tool_names}

USER REQUEST: {request}

INSTRUCTIONS:
- Follow the user's request exactly - don't add extra requirements they didn't ask for
- If they ask for "simple", keep it simple with 3-4 basic ingredients
- If they specify ingredients, use those as the main focus
- Only use tools when needed to find specific ingredients or calculate nutrition
- Keep meal plans practical and realistic

You must use the following format:

Thought: I need to think about what to do
Action: tool_name
Action Input: {{"parameter_name": "value"}}
Observation: result from tool
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to create the final meal plan
Final Answer: {{valid json meal plan}}

EXAMPLES:
Thought: I need to find potato in the nutrition database
Action: find_ingredient
Action Input: {{"ingredient_name": "potato", "max_results": 3}}
Observation: {{"ingredient_searched": "potato", "results_found": 2, "matches": [...]}}

Thought: The user wants a simple potato recipe, so I'll create a basic plan with potatoes and a few complementary ingredients
Final Answer: {{"meal": "Simple Roasted Potatoes", "ingredients": [{{"item": "potatoes", "qty": "500g"}}, {{"item": "olive oil", "qty": "2 tbsp"}}, {{"item": "salt", "qty": "1 tsp"}}], "dietary_needs": "simple and satisfying"}}

IMPORTANT: 
- Use "item" and "qty" fields in ingredients, not "name" and "quantity"!
- Match the user's dietary goals exactly (e.g., if they say "balanced", use "balanced", not "high protein")
- Keep it simple when they ask for simple recipes

{agent_scratchpad}"""
)


def generate_ingredient_plan(request: str) -> Plan:
    """
    Generate a meal plan based on ingredient request using LLM agent with MCP tools
    """
    agent_executor = create_agent_executor(INGREDIENT_PLANNER_PROMPT, temperature=0.7, max_iterations=20)
    return run_agent_with_parsing(agent_executor, {"request": request}, Plan)
