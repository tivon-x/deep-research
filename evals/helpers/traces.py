from __future__ import annotations

import json
from typing import Any


def _tool_args_from_openai_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    raw_args = function.get("arguments")
    if not raw_args:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        return {"raw": raw_args}


def collect_tool_calls(source: Any) -> list[dict[str, Any]]:
    messages = source
    if not isinstance(messages, list):
        messages = getattr(source, "messages", None) or getattr(source, "state_messages", None) or []

    calls: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        tool_message_name = getattr(message, "name", None)
        if tool_message_name:
            calls.append(
                {
                    "event": "tool_message",
                    "name": tool_message_name,
                    "args": {},
                    "message_index": index,
                }
            )

        for tool_call in getattr(message, "tool_calls", None) or []:
            calls.append(
                {
                    "event": "assistant_tool_call",
                    "name": tool_call.get("name"),
                    "args": tool_call.get("args") or {},
                    "message_index": index,
                }
            )

        additional_kwargs = getattr(message, "additional_kwargs", None) or {}
        for tool_call in additional_kwargs.get("tool_calls", []):
            function = tool_call.get("function") or {}
            calls.append(
                {
                    "event": "assistant_tool_call",
                    "name": function.get("name"),
                    "args": _tool_args_from_openai_call(tool_call),
                    "message_index": index,
                }
            )

    return calls


def tool_call_names(source: Any, *, executed_only: bool = False) -> list[str]:
    names: list[str] = []
    for call in collect_tool_calls(source):
        if executed_only and call["event"] != "tool_message":
            continue
        if call.get("name"):
            names.append(str(call["name"]))
    return names


def count_tool_calls(source: Any, tool_name: str, *, executed_only: bool = False) -> int:
    return sum(1 for name in tool_call_names(source, executed_only=executed_only) if name == tool_name)

