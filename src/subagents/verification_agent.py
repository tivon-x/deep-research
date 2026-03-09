"""
Verification Subagent - Subagent for verifying the quality and relevance of research outputs.
"""
from src.llm import verify_model
from src.prompts import VERIFICATION_INSTRUCTIONS


def build_verification_subagent(skills: list[str] | None = None) -> dict:
    subagent = {
        "name": "verification-agent",
        "description": (
            "Verify the quality and relevance of research outputs based on the research brief and provide feedback for possible improvement."
        ),
        "system_prompt": VERIFICATION_INSTRUCTIONS,
        "tools": [],
        "model": verify_model,
    }
    if skills:
        subagent["skills"] = skills
    return subagent


verification_subagent = build_verification_subagent()
