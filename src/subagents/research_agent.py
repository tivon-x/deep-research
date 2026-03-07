import atexit
import asyncio
import logging
from datetime import datetime
from typing import Any

from src.config import mcp_capabilities, mcp_servers, research_search_tool_limit
from src.llm import research_model
from src.middleware import SearchUsageLimitMiddleware
from src.prompts import RESEARCHER_INSTRUCTIONS, RESEARCHER_MCP_GUIDANCE
from src.tools import tavily_search, think_tool


logger = logging.getLogger(__name__)

# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")


def _build_mcp_capabilities_prompt() -> str:
    if mcp_capabilities:
        return mcp_capabilities
    if not mcp_servers:
        return ""
    return "MCP servers are configured, but no capability descriptions were provided."


MCP_STATUS: dict[str, Any] = {
    "enabled": False,
    "server_count": len(mcp_servers),
    "tool_count": 0,
    "config_error": "",
    "capabilities": _build_mcp_capabilities_prompt(),
    "prompt_guidance_enabled": False,
}

_mcp_client: Any = None
_mcp_tools: list[Any] = []


async def _open_mcp_client_and_tools() -> tuple[Any, list[Any]]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(mcp_servers)
    await client.__aenter__()
    tools = await client.get_tools()
    return client, tools


def _initialize_mcp_tools() -> tuple[Any, list[Any]]:
    if not mcp_servers:
        return None, []

    try:
        client, tools = asyncio.run(_open_mcp_client_and_tools())
        MCP_STATUS["enabled"] = True
        MCP_STATUS["tool_count"] = len(tools)
        logger.info("MCP tools loaded: %d", len(tools))
        return client, tools
    except Exception as exc:  # pragma: no cover - depends on runtime MCP availability
        MCP_STATUS["config_error"] = str(exc)
        logger.warning("Failed to load MCP tools: %s", exc)
        return None, []


async def _close_mcp_client() -> None:
    if _mcp_client is None:
        return
    await _mcp_client.__aexit__(None, None, None)


def _shutdown_mcp_client() -> None:
    if _mcp_client is None:
        return
    try:
        asyncio.run(_close_mcp_client())
    except Exception as exc:  # pragma: no cover - shutdown best effort
        logger.debug("Failed to close MCP client cleanly: %s", exc)


def _build_research_prompt() -> str:
    prompt = RESEARCHER_INSTRUCTIONS.format(date=current_date)
    if MCP_STATUS["enabled"] and MCP_STATUS["tool_count"] > 0:
        MCP_STATUS["prompt_guidance_enabled"] = True
        prompt += RESEARCHER_MCP_GUIDANCE.format(mcp_capabilities=MCP_STATUS["capabilities"])
    else:
        MCP_STATUS["prompt_guidance_enabled"] = False
    return prompt


_mcp_client, _mcp_tools = _initialize_mcp_tools()
atexit.register(_shutdown_mcp_client)

# Create research sub-agent
research_subagent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
    "system_prompt": _build_research_prompt(),
    "tools": [tavily_search, think_tool, *_mcp_tools],
    "middleware": [SearchUsageLimitMiddleware(max_calls=research_search_tool_limit)],
    "model": research_model,
}
