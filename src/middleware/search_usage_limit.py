from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command


class SearchUsageLimitMiddleware(AgentMiddleware):
    """Track and cap search tool usage for a subagent.

    The middleware intercepts calls to one search tool, tracks usage count in
    request state, and blocks additional calls after the configured limit.
    """

    def __init__(self, max_calls: int = 15, search_tool_name: str = "tavily_search") -> None:
        if max_calls <= 0:
            raise ValueError("max_calls must be a positive integer")
        self.max_calls = max_calls
        self.search_tool_name = search_tool_name

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        return self._handle_sync_tool_call(request, handler)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool_call.get("name")
        if tool_name != self.search_tool_name:
            return await handler(request)

        state = request.state if isinstance(request.state, dict) else {}
        current_count = self._read_count(state)

        if current_count >= self.max_calls:
            return self._limit_reached_message(request)

        result = await handler(request)
        return self._finalize_tool_result(request, state, current_count, result)

    def _handle_sync_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool_call.get("name")
        if tool_name != self.search_tool_name:
            return handler(request)

        state = request.state if isinstance(request.state, dict) else {}
        current_count = self._read_count(state)

        if current_count >= self.max_calls:
            return self._limit_reached_message(request)

        result = handler(request)
        return self._finalize_tool_result(request, state, current_count, result)

    def _finalize_tool_result(
        self,
        request: ToolCallRequest,
        state: dict[str, Any],
        current_count: int,
        result: ToolMessage | Command[Any],
    ) -> ToolMessage | Command[Any]:
        updated_count = current_count + 1
        self._write_count(state, updated_count)

        if updated_count == self.max_calls and isinstance(result, ToolMessage):
            result.content = (
                f"{result.content}\n\n"
                f"[Search budget reached: {updated_count}/{self.max_calls}] "
                "Stop searching now and move to synthesis: summarize findings, identify gaps, "
                "and produce the output file."
            )

        return result

    def _limit_reached_message(self, request: ToolCallRequest) -> ToolMessage:
        return ToolMessage(
            content=(
                f"Search limit reached ({self.max_calls}/{self.max_calls}) for this research task. "
                "Do not call tavily_search again. Use think_tool to summarize findings, "
                "note remaining gaps/uncertainties, and then write your final findings file."
            ),
            tool_call_id=request.tool_call.get("id") or "search-limit-reached",
            name=self.search_tool_name,
            status="success",
        )

    @staticmethod
    def _read_count(state: dict[str, Any]) -> int:
        value = state.get("_research_search_tool_calls", 0)
        if isinstance(value, int) and value >= 0:
            return value
        return 0

    @staticmethod
    def _write_count(state: dict[str, Any], count: int) -> None:
        state["_research_search_tool_calls"] = count
