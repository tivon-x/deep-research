from __future__ import annotations

import asyncio
import types
from pathlib import Path


def test_run_cli_uses_async_agent_and_persists_report(monkeypatch, tmp_path: Path) -> None:
    import src
    import src.cli as cli

    class FakeStateSnapshot:
        def __init__(self, values):
            self.values = values

    class FakeAgent:
        def __init__(self) -> None:
            self.invocations: list[tuple[object, dict]] = []

        async def ainvoke(self, graph_input, config):
            self.invocations.append((graph_input, config))
            return {
                "messages": [{"role": "assistant", "content": "Async result"}],
                "__interrupt__": [],
                "files": {
                    "/final_report.md": {
                        "content": "# Final Report\n\nDone\n",
                    }
                },
            }

        async def aget_state(self, config):
            return FakeStateSnapshot({"files": {}})

    fake_agent = FakeAgent()
    fake_agent_module = types.SimpleNamespace(
        build_agent=lambda skill=None: fake_agent,
        WORKING_DIR=tmp_path,
        MCP_STATUS={
            "enabled": False,
            "server_count": 0,
            "tool_count": 0,
            "config_error": "",
            "capabilities": "",
            "prompt_guidance_enabled": False,
        },
    )

    init_calls: list[str] = []
    shutdown_calls: list[str] = []
    monkeypatch.setattr(cli, "initialize_mcp_tools", lambda: _async_record(init_calls, "init"))
    monkeypatch.setattr(cli, "shutdown_mcp_client", lambda: _async_record(shutdown_calls, "shutdown"))
    monkeypatch.setattr(src, "agent", fake_agent_module, raising=False)

    asyncio.run(cli.run_cli(query="research this", thread_id="thread-1", skill=None, plain=True))

    report_path = tmp_path / "final_report.md"
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == "# Final Report\n\nDone\n"
    assert len(fake_agent.invocations) == 1
    assert init_calls == ["init"]
    assert shutdown_calls == ["shutdown"]


async def _async_record(records: list[str], value: str):
    records.append(value)
    return None
