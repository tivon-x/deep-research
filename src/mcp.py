import json
import logging
import os
from pathlib import Path
from typing import Any

from src.prompts import RESEARCHER_MCP_GUIDANCE


logger = logging.getLogger(__name__)


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


async def initialize_mcp_tools() -> tuple[Any, list[Any]]:
    if not mcp_servers:
        MCP_STATUS["enabled"] = False
        MCP_STATUS["tool_count"] = 0
        MCP_STATUS["config_error"] = ""
        return None, []

    global _mcp_client, _mcp_tools

    if _mcp_client is not None:
        return _mcp_client, list(_mcp_tools)

    try:
        client, tools = await _open_mcp_client_and_tools()
        _mcp_client = client
        _mcp_tools = list(tools)
        MCP_STATUS["enabled"] = True
        MCP_STATUS["tool_count"] = len(_mcp_tools)
        MCP_STATUS["config_error"] = ""
        logger.info("MCP tools loaded: %d", len(tools))
        return _mcp_client, list(_mcp_tools)
    except Exception as exc:  # pragma: no cover - depends on runtime MCP availability
        _mcp_client = None
        _mcp_tools = []
        MCP_STATUS["enabled"] = False
        MCP_STATUS["tool_count"] = 0
        MCP_STATUS["config_error"] = str(exc)
        logger.warning("Failed to load MCP tools: %s", exc)
        return None, []


async def _close_mcp_client() -> None:
    if _mcp_client is None:
        return
    await _mcp_client.__aexit__(None, None, None)


async def shutdown_mcp_client() -> None:
    global _mcp_client, _mcp_tools

    if _mcp_client is None:
        return

    try:
        await _close_mcp_client()
    except Exception as exc:  # pragma: no cover - shutdown best effort
        logger.debug("Failed to close MCP client cleanly: %s", exc)
    finally:
        _mcp_client = None
        _mcp_tools = []
        MCP_STATUS["enabled"] = False
        MCP_STATUS["tool_count"] = 0


def get_mcp_tools() -> list[Any]:
    return list(_mcp_tools)


def append_mcp_guidance(base_prompt: str) -> str:
    if MCP_STATUS["enabled"] and MCP_STATUS["tool_count"] > 0:
        MCP_STATUS["prompt_guidance_enabled"] = True
        return base_prompt + RESEARCHER_MCP_GUIDANCE.format(mcp_capabilities=MCP_STATUS["capabilities"])

    MCP_STATUS["prompt_guidance_enabled"] = False
    return base_prompt
