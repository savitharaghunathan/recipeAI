"""
Centralized LLM configuration and initialization
"""

from langchain_openai import ChatOpenAI, OpenAI
from typing import Optional

# Global LLM instances
_chat_llm: Optional[ChatOpenAI] = None
_completion_llm: Optional[OpenAI] = None

def get_chat_llm(temperature: float = 0.1) -> ChatOpenAI:
    """Get shared ChatOpenAI instance"""
    global _chat_llm
    if _chat_llm is None or _chat_llm.temperature != temperature:
        _chat_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=temperature,
            max_tokens=2000,
            timeout=30,
        )
    return _chat_llm

def get_completion_llm(temperature: float = 0.1) -> OpenAI:
    """Get shared OpenAI completion instance"""
    global _completion_llm
    if _completion_llm is None or _completion_llm.temperature != temperature:
        _completion_llm = OpenAI(
            model="gpt-4o-mini",
            temperature=temperature,
            max_tokens=2000,
            timeout=30,
        )
    return _completion_llm

def set_temperature(temperature: float):
    """Update temperature for all LLM instances"""
    global _chat_llm, _completion_llm
    _chat_llm = None  # Force recreation with new temperature
    _completion_llm = None