"""
Verification Subagent - Subagent for verifying the quality and relevance of research outputs.
"""
from src.llm import verify_model
from src.prompts import VERIFICATION_INSTRUCTIONS


verification_subagent = {
    "name": "verification-agent",
    "description": (
        "Verify the quality and relevance of research outputs based on the research brief and provide feedback for possible improvement."
    ),
    "system_prompt": VERIFICATION_INSTRUCTIONS,
    "tools": [],
    "model": verify_model,
}