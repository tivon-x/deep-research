from datetime import datetime

from src.config import research_search_tool_limit
from src.llm import research_model
from src.mcp import MCP_STATUS, append_mcp_guidance, get_mcp_tools
from src.middleware import SearchUsageLimitMiddleware
from src.prompts import RESEARCHER_INSTRUCTIONS
from src.tools import record_source_metadata, tavily_search, think_tool


# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")


def _build_research_prompt() -> str:
    base_prompt = RESEARCHER_INSTRUCTIONS.format(date=current_date)
    return append_mcp_guidance(base_prompt)


def build_research_subagent(skills: list[str] | None = None) -> dict:
    subagent = {
        "name": "research-agent",
        "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
        "system_prompt": _build_research_prompt(),
        "tools": [tavily_search, think_tool, record_source_metadata, *get_mcp_tools()],
        "middleware": [SearchUsageLimitMiddleware(max_calls=research_search_tool_limit)],
        "model": research_model,
    }
    if skills:
        subagent["skills"] = skills
    return subagent


research_subagent = build_research_subagent()
