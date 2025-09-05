"""
Shared utilities for LangChain agents
"""

import json
import re
from typing import Type, TypeVar, Dict, Any
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, ValidationError

from src.llm_config import get_completion_llm
from src.mcp_tools import get_nutrition_tools

T = TypeVar('T', bound=BaseModel)


def create_agent_executor(prompt: PromptTemplate, temperature: float = 0.7, max_iterations: int = 10) -> AgentExecutor:
    """Create a standardized agent executor with nutrition tools"""
    tools = get_nutrition_tools()
    llm = get_completion_llm(temperature=temperature)
    
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=max_iterations
    )


def parse_json_response(raw_output: str, model_class: Type[T]) -> T:
    """Parse agent JSON response and validate against Pydantic model"""
    try:
        # Extract JSON after "Final Answer:"
        if "Final Answer:" in raw_output:
            after_final = raw_output.split("Final Answer:")[-1]
            json_match = re.search(r'\{.*\}', after_final, re.DOTALL)
        else:
            json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        
        if not json_match:
            raise ValueError(f"No JSON found in agent output: {raw_output}")
        
        data = json.loads(json_match.group(0))
        return model_class.model_validate(data)
        
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to parse agent output into {model_class.__name__}: {e}\nRaw output: {raw_output}")


def run_agent_with_parsing(agent_executor: AgentExecutor, inputs: Dict[str, Any], model_class: Type[T]) -> T:
    """Run agent and parse response into specified Pydantic model"""
    result = agent_executor.invoke(inputs)
    raw_output = result["output"]
    return parse_json_response(raw_output, model_class)