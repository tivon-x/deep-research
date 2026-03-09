"""Research Agent - Standalone script for LangGraph deployment.

This module creates a deep research agent with custom tools and prompts
for conducting web research with strategic thinking and context management.
"""

from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import MemorySaver

from src.config import max_concurrent_research_units, max_researcher_iterations
from src.llm import main_model
from src.prompts import (
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from src.skills import resolve_role_skills
from src.subagents.report_agent import build_report_subagent
from src.subagents.research_agent import (
    MCP_STATUS as RESEARCH_MCP_STATUS,
    build_research_subagent,
)
from src.subagents.scoping_agent import build_scoping_subagent
from src.subagents.verification_agent import build_verification_subagent
from src.tools import think_tool


# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Combine orchestrator instructions and inject config limits into both sections
_format_kwargs = dict(
    max_concurrent_research_units=max_concurrent_research_units,
    max_researcher_iterations=max_researcher_iterations,
)

INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS.format(**_format_kwargs)
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(**_format_kwargs)
)

WORKING_DIR = Path.cwd() / "research"


def build_agent(skill: str | None = None):
    role_skill_map = resolve_role_skills(skill)
    return create_deep_agent(
        model=main_model,
        tools=[think_tool],
        system_prompt=INSTRUCTIONS,
        subagents=[
            build_research_subagent(skills=role_skill_map["research"]),
            build_scoping_subagent(skills=role_skill_map["scoping"]),
            build_verification_subagent(skills=role_skill_map["verification"]),
            build_report_subagent(skills=role_skill_map["report"]),
        ],
        name="research",
        checkpointer=MemorySaver(),  # Comment out this line of code if you are using a langraph cli.
        backend=lambda runtime: StateBackend(runtime),
        skills=role_skill_map["orchestrator"],
    )


# Default graph entrypoint used by LangGraph and CLI import paths.
agent = build_agent()


MCP_STATUS = RESEARCH_MCP_STATUS
