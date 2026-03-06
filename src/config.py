import os
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file


# Configuration for the research agent and sub-agents
MAIN_MODEL_ID = os.getenv("MAIN_MODEL_ID")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
SUBAGENT_MODEL_ID = {
    "report": os.getenv("REPORT_MODEL_ID", MAIN_MODEL_ID),
    "research": os.getenv("RESEARCH_MODEL_ID", MAIN_MODEL_ID),
    "scoping": os.getenv("SCOPING_MODEL_ID", MAIN_MODEL_ID),
    "verify": os.getenv("VERIFY_MODEL_ID", MAIN_MODEL_ID),
}

if not MAIN_MODEL_ID or not API_KEY or not BASE_URL:
    raise ValueError("MAIN_MODEL_ID, API_KEY, and BASE_URL must be set in the environment variables.")


# Limits
max_concurrent_research_units = 3
max_researcher_iterations = 3