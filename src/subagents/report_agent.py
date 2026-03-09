from src.llm import report_model
from src.prompts import REPORT_INSTRUCTIONS


def build_report_subagent(skills: list[str] | None = None) -> dict:
    subagent = {
        "name": "report-agent",
        "description": (
            "Write the final research report clearly and professionally based on the research findings and the research brief. "
        ),
        "tools": [],
        "system_prompt": REPORT_INSTRUCTIONS,
        "model": report_model,
    }
    if skills:
        subagent["skills"] = skills
    return subagent


report_subagent = build_report_subagent()
