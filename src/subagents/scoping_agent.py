"""
Scoping Subagent - Subagent for defining research scope and goals.
"""
from src.tools import think_tool, request_approval
from src.llm import scoping_model
from src.prompts import SCOPING_AGENT_INSTRUCTIONS


scoping_subagent = {
    "name": "scoping-agent",
    "description": "Define the scope and goals of the research project. It will provide a research brief that satisfies the user's intent and demand.",
    "system_prompt": SCOPING_AGENT_INSTRUCTIONS,
    "tools": [think_tool, request_approval], 
    "model": scoping_model,
}