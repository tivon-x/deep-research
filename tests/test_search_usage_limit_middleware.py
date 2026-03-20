from __future__ import annotations

import asyncio

from langchain_core.messages import ToolMessage

from src.middleware.search_usage_limit import SearchUsageLimitMiddleware


class DummyRequest:
    def __init__(self, name: str, state: dict[str, int] | None = None) -> None:
        self.tool_call = {"name": name, "id": "tool-1"}
        self.state = state if state is not None else {}


def test_awrap_tool_call_increments_usage_and_stops_at_limit() -> None:
    middleware = SearchUsageLimitMiddleware(max_calls=1)
    request = DummyRequest("tavily_search", {})

    async def handler(_request):
        return ToolMessage(content="search result", tool_call_id="tool-1", name="tavily_search")

    first = asyncio.run(middleware.awrap_tool_call(request, handler))
    second = asyncio.run(middleware.awrap_tool_call(request, handler))

    assert request.state["_research_search_tool_calls"] == 1
    assert "Search budget reached: 1/1" in first.content
    assert "Search limit reached (1/1)" in second.content


def test_awrap_tool_call_bypasses_other_tools() -> None:
    middleware = SearchUsageLimitMiddleware(max_calls=1)
    request = DummyRequest("think_tool", {})

    async def handler(_request):
        return ToolMessage(content="ok", tool_call_id="tool-1", name="think_tool")

    result = asyncio.run(middleware.awrap_tool_call(request, handler))

    assert result.content == "ok"
    assert "_research_search_tool_calls" not in request.state
