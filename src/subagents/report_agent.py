from src.llm import report_model
from src.prompts import REPORT_INSTRUCTIONS

report_subagent = {
    "name": "report-agent",
    "description": (
        "Write the final research report clearly and professionally based on the research findings and the research brief. "
    ),
    "tools": [],
    "system_prompt": REPORT_INSTRUCTIONS,
    "model": report_model,
}