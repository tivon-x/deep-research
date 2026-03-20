from __future__ import annotations

import asyncio
import importlib


def test_initialize_mcp_tools_updates_status(monkeypatch) -> None:
    import src.mcp as mcp

    mcp = importlib.reload(mcp)
    monkeypatch.setattr(mcp, "mcp_servers", {"server": {"command": "demo"}}, raising=False)

    async def fake_open():
        return object(), ["tool-a", "tool-b"]

    monkeypatch.setattr(mcp, "_open_mcp_client_and_tools", fake_open)

    client, tools = asyncio.run(mcp.initialize_mcp_tools())

    assert client is not None
    assert tools == ["tool-a", "tool-b"]
    assert mcp.get_mcp_tools() == ["tool-a", "tool-b"]
    assert mcp.MCP_STATUS["enabled"] is True
    assert mcp.MCP_STATUS["tool_count"] == 2


def test_shutdown_mcp_client_resets_status(monkeypatch) -> None:
    import src.mcp as mcp

    mcp = importlib.reload(mcp)

    class FakeClient:
        def __init__(self) -> None:
            self.closed = False

        async def __aexit__(self, exc_type, exc, tb) -> None:
            self.closed = True

    client = FakeClient()
    monkeypatch.setattr(mcp, "_mcp_client", client, raising=False)
    monkeypatch.setattr(mcp, "_mcp_tools", ["tool-a"], raising=False)
    mcp.MCP_STATUS["enabled"] = True
    mcp.MCP_STATUS["tool_count"] = 1

    asyncio.run(mcp.shutdown_mcp_client())

    assert client.closed is True
    assert mcp.get_mcp_tools() == []
    assert mcp.MCP_STATUS["enabled"] is False
    assert mcp.MCP_STATUS["tool_count"] == 0
