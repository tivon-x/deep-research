from datetime import datetime

from src.prompts import (
    RESEARCHER_INSTRUCTIONS,
)
from src.tools import tavily_search, think_tool
from src.llm import research_model


# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Create research sub-agent
research_subagent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search, think_tool],
    "model": research_model,
}
