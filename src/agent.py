"""Research Agent - Standalone script for LangGraph deployment.

This module creates a deep research agent with custom tools and prompts
for conducting web research with strategic thinking and context management.
"""

from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from deepagents.backends import FilesystemBackend

from src.prompts import (
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from src.tools import think_tool
from src.config import max_concurrent_research_units, max_researcher_iterations
from src.llm import main_model
from src.subagents.research_agent import research_subagent
from src.subagents.scoping_agent import scoping_subagent
from src.subagents.verification_agent import verification_subagent
from src.subagents.report_agent import report_subagent


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
WORKING_DIR.mkdir(exist_ok=True)

# Create the agent
agent = create_deep_agent(
    model=main_model,
    tools=[think_tool],
    system_prompt=INSTRUCTIONS,
    subagents=[research_subagent, scoping_subagent, verification_subagent, report_subagent],
    name="research",
    checkpointer=MemorySaver(), # Comment out this line of code if you are using a langraph cli.
    backend=FilesystemBackend(root_dir=WORKING_DIR, virtual_mode=True)
)
