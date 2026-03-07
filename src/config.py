import json
import os
from pathlib import Path
from typing import Any


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


def _get_positive_int_from_env(var_name: str, default: int) -> int:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


# Search tool call limit per research-agent run
research_search_tool_limit = _get_positive_int_from_env("RESEARCH_SEARCH_TOOL_LIMIT", 15)


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize_mcp_capabilities(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, list):
        return "\n".join(f"- {item}" for item in raw if str(item).strip())
    if isinstance(raw, dict):
        lines: list[str] = []
        for server_name, description in raw.items():
            if isinstance(description, str) and description.strip():
                lines.append(f"- {server_name}: {description.strip()}")
        return "\n".join(lines)
    return ""


def _load_mcp_config() -> tuple[dict[str, Any], str, Path | None]:
    config_file_raw = os.getenv("MCP_CONFIG_FILE", "mcp_config.json").strip()
    if not config_file_raw:
        return {}, "", None

    config_path = Path(config_file_raw)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    if not config_path.exists():
        return {}, "", None

    config_data = _load_json_file(config_path)
    servers = config_data.get("mcp_servers") or config_data.get("servers") or {}
    capabilities = _normalize_mcp_capabilities(
        config_data.get("mcp_capabilities") or config_data.get("capabilities") or ""
    )

    if not isinstance(servers, dict):
        servers = {}

    return servers, capabilities, config_path


mcp_servers, mcp_capabilities, mcp_config_path = _load_mcp_config()
