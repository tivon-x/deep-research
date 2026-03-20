from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.backends.utils import create_file_data
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree

from evals.helpers.fixtures import resolve_mock_search_results
from evals.helpers.state import get_virtual_files
from src.agent import build_agent
from src.llm import report_model, research_model, scoping_model, verify_model
from src.prompts import REPORT_INSTRUCTIONS, SCOPING_AGENT_INSTRUCTIONS, VERIFICATION_INSTRUCTIONS
from src.subagents import research_agent as research_agent_module
from src.tools import request_approval, think_tool


@dataclass
class EvalRunResult:
    final_output: str | None
    state: Any
    thread_id: str
    trace_ref: str | None
    raw_result: Any
    files: dict[str, Any]
    messages: list[Any]
    interrupts: list[dict[str, Any]] = field(default_factory=list)
    approval_mode: str = "auto_approve"
    mode: str = "mocked"
    preexisting_files: list[str] = field(default_factory=list)


def _normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks)
    return str(content)


def _extract_final_answer(result: dict[str, Any]) -> str | None:
    for message in reversed(result.get("messages", [])):
        role = getattr(message, "type", None) or getattr(message, "role", None)
        if role in {"assistant", "ai"}:
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content", "")
            return _normalize_content(content)
    return None


def _extract_interrupt_payload(interrupt_obj: Any) -> dict[str, Any]:
    payload = getattr(interrupt_obj, "value", interrupt_obj)
    if isinstance(payload, dict):
        return payload
    return {"message": str(payload)}


def _seed_files(files: dict[str, str] | None) -> dict[str, dict]:
    if not files:
        return {}
    return {path: create_file_data(content) for path, content in files.items()}


def _is_langsmith_enabled() -> bool:
    from os import getenv

    return getenv("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}


def record_feedback(trace_ref: str | None, key: str, score: float, comment: str | None = None) -> None:
    if not trace_ref or not _is_langsmith_enabled():
        return
    Client().create_feedback(run_id=trace_ref, key=key, score=score, comment=comment)


def _default_thread_id(case_id: str) -> str:
    return f"eval-{case_id}-{uuid4().hex[:8]}"


def _current_trace_ref() -> str | None:
    run_tree = get_current_run_tree()
    if run_tree is None:
        return None
    return str(run_tree.id)


def _normalize_title(text: str) -> str:
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned[:80].strip(" .,:;") or "Research Topic"


def _normalize_slug(text: str) -> str:
    chars = [ch.lower() if ch.isalnum() else "_" for ch in text]
    slug = "".join(chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")[:40] or "research_topic"


def _keyword_phrases(text: str) -> list[str]:
    lowered = text.lower()
    candidates = [
        "remote work",
        "software engineering",
        "onboarding",
        "collaboration",
        "open-source llm",
        "export controls",
        "compliance",
        "monitoring",
        "supply chain",
        "risk",
        "recommendation",
        "operational",
    ]
    return [item for item in candidates if item in lowered]


def _build_mock_brief(query: str) -> str:
    title = _normalize_title(query)
    key_terms = _keyword_phrases(query) or ["core topic", "tradeoffs", "recommendation"]
    return (
        "## Research Brief\n\n"
        "### User Intent\n"
        f"Understand {title} with evidence, tradeoffs, and decision-useful synthesis.\n\n"
        "### Core Research Question\n"
        f"What matters most about {title}, and what should a decision-maker conclude?\n\n"
        "### Sub-Questions\n"
        f"1. What are the most important facts or recent developments related to {key_terms[0]}?\n"
        f"2. What risks, limitations, or implementation constraints affect {key_terms[1] if len(key_terms) > 1 else key_terms[0]}?\n"
        f"3. What practical recommendation follows from the evidence on {key_terms[-1]}?\n\n"
        "### Recommended Research Tasks\n"
        "**Number of parallel research tasks: 3**\n"
        "3 tasks: landscape, risks, and recommendation synthesis.\n\n"
        "### Out of Scope\n"
        "- Unsourced anecdotes\n"
        "- Irrelevant background material\n\n"
        "### Success Criteria\n"
        "- Answer the user question directly\n"
        "- Include grounded evidence and explicit uncertainty\n"
        "- End with a clear recommendation or implication\n\n"
        "### Suggested Research Strategy\n"
        "- Use focused keyword searches\n"
        "- Prefer recent reports, official sources, and comparative analysis\n"
    )


def _build_mock_findings(query: str) -> str:
    title = _normalize_title(query)
    phrases = _keyword_phrases(query)
    primary = phrases[0] if len(phrases) > 0 else "the topic"
    secondary = phrases[1] if len(phrases) > 1 else "operational risk"
    return (
        f"## Research Findings: {title}\n\n"
        "### Summary\n"
        f"The available evidence suggests {primary} has meaningful upside, but outcomes depend heavily on execution quality, coordination, and measurement discipline. [1][2]\n\n"
        "### Key Findings\n\n"
        f"{primary.capitalize()} benefits are strongest when teams use explicit processes, documentation, and clear accountability. [1]\n\n"
        f"{secondary.capitalize()} problems appear when organizations underinvest in onboarding, cross-functional alignment, or monitoring. [2]\n\n"
        f"A balanced recommendation is to keep the advantages while adding controls for the main risks. [1][2]\n\n"
        "### Gaps and Limitations\n"
        "The mocked corpus is intentionally small, so effect sizes and edge cases should be validated in live mode.\n\n"
        "### Sources\n"
        "[1] Mock Source One: https://example.com/source-one\n"
        "[2] Mock Source Two: https://example.com/source-two\n"
    )


def _build_mock_sources(query: str) -> str:
    title = _normalize_title(query)
    return (
        f"# Source Metadata Log: {title}\n\n"
        "## Source 1\n"
        "- Citation ID: [1]\n"
        "- Title: Mock Source One\n"
        "- URL: https://example.com/source-one\n"
        "- Publisher / Organization: Example Research\n"
        "- Author(s): Unknown\n"
        "- Published Date: 2026-01-15\n"
        "- Accessed Date: 2026-03-20\n"
        "- Evidence Type: report\n"
        "- Relevance: Establishes the main evidence-backed benefits.\n\n"
        "## Source 2\n"
        "- Citation ID: [2]\n"
        "- Title: Mock Source Two\n"
        "- URL: https://example.com/source-two\n"
        "- Publisher / Organization: Example Analysis\n"
        "- Author(s): Unknown\n"
        "- Published Date: 2026-02-01\n"
        "- Accessed Date: 2026-03-20\n"
        "- Evidence Type: analysis\n"
        "- Relevance: Covers the primary risks and operational constraints.\n"
    )


def _build_mock_verification(case: dict[str, Any], query: str) -> str:
    if case["id"] == "verification_incomplete_findings":
        return (
            "# Research Verification Report\n\n"
            "## Overall Rating\n"
            "NEEDS_MAJOR_REWORK\n\n"
            "## Coverage by Sub-Question\n\n"
            "### Sub-Question 1: Supplier concentration risks\n"
            "Status: PARTIALLY COVERED\n"
            "Notes: One findings file exists, but scope is narrow.\n\n"
            "### Sub-Question 2: Logistics risks\n"
            "Status: MISSING\n"
            "Notes: No evidence provided.\n\n"
            "### Sub-Question 3: Mitigations\n"
            "Status: MISSING\n"
            "Notes: No mitigation analysis provided.\n\n"
            "## Quality Issues\n"
            "- Evidence set is incomplete.\n\n"
            "## Gaps Requiring Additional Research\n"
            "- Add logistics risk evidence. Priority: CRITICAL\n"
            "- Add mitigation strategies. Priority: HIGH\n\n"
            "## Summary\n"
            "The findings are not yet sufficient for report writing.\n"
        )
    return (
        "# Research Verification Report\n\n"
        "## Overall Rating\n"
        "COMPLETE\n\n"
        "## Summary\n"
        f"Findings for {_normalize_title(query)} cover the main sub-questions with enough evidence for report writing.\n"
    )


def _build_mock_report(case: dict[str, Any], query: str) -> str:
    setup_context = " ".join((case.get("setup_files") or {}).values()) if case.get("setup_files") else ""
    combined_context = f"{query}\n{setup_context}".strip()
    title = _normalize_title(combined_context)
    phrases = _keyword_phrases(combined_context)
    focus = phrases[0] if phrases else "the topic"
    secondary = phrases[1] if len(phrases) > 1 else "execution"
    tertiary = phrases[2] if len(phrases) > 2 else "recommendation"
    return (
        f"## {title}\n\n"
        "### Introduction\n"
        f"This report addresses {title} and focuses on the practical evidence that matters for decisions. The evidence suggests {focus} is valuable when paired with deliberate operating practices. [1]\n\n"
        f"### Benefits And Opportunities\n"
        f"The main upside comes from better focus, clearer prioritization, and the ability to structure work around measurable outcomes. These gains are strongest when teams invest in documentation and role clarity. [1]\n\n"
        f"### Risks And Constraints\n"
        f"The primary risks center on {secondary}, uneven execution, and weak visibility into emerging problems. Organizations that do not monitor these areas often trade short-term convenience for longer-term coordination costs. [2]\n\n"
        f"### Recommendation\n"
        f"A balanced recommendation is to keep the benefits while adding explicit safeguards for {tertiary}. Leaders should define success metrics, inspect evidence regularly, and revise the operating model when signals deteriorate. [1][2]\n\n"
        "### Sources\n"
        "[1] Mock Source One: https://example.com/source-one\n"
        "[2] Mock Source Two: https://example.com/source-two\n"
    )


def _mock_state_snapshot(values: dict[str, Any]) -> Any:
    return SimpleNamespace(values=values)


def _build_mock_messages(query: str, *, include_search: bool = True, final_answer: str | None = None) -> list[Any]:
    messages: list[Any] = [HumanMessage(content=query)]
    messages.append(ToolMessage(content="Updated todo list", name="write_todos", tool_call_id="todo-1"))
    if include_search:
        messages.append(
            AIMessage(
                content="Searching for evidence.",
                tool_calls=[{"name": "tavily_search", "args": {"query": query}, "id": "call-search-1", "type": "tool_call"}],
            )
        )
        messages.append(ToolMessage(content=resolve_mock_search_results(query), name="tavily_search", tool_call_id="call-search-1"))
    if final_answer:
        messages.append(AIMessage(content=final_answer))
    return messages


def _run_mock_case(case: dict[str, Any]) -> EvalRunResult:
    query = case["input"]
    thread_id = case.get("thread_id") or _default_thread_id(case["id"])
    approval_mode = case.get("approval_mode", "auto_approve")
    request_file = create_file_data(query)
    brief = _build_mock_brief(query)
    interrupts = [
        {
            "type": "approval_request",
            "action": "Review and approve/reject the research brief",
            "approval_item": brief,
        }
    ]

    files: dict[str, Any] = {"/research_request.md": request_file}
    messages = _build_mock_messages(query, include_search=False)

    if approval_mode == "auto_reject" or case.get("stop_at_first_interrupt"):
        state = _mock_state_snapshot({"messages": messages, "files": files})
        return EvalRunResult(
            final_output=None,
            state=state,
            thread_id=thread_id,
            trace_ref=_current_trace_ref(),
            raw_result={"messages": messages, "files": files, "__interrupt__": interrupts},
            files=files,
            messages=messages,
            interrupts=interrupts,
            approval_mode=approval_mode,
            mode="mocked",
            preexisting_files=[],
        )

    findings_path = f"/research_findings/{_normalize_slug(query)}.md"
    sources_path = f"/research_sources/{_normalize_slug(query)}.sources.md"
    report = _build_mock_report(case, query)
    files.update(
        {
            "/research_brief.md": create_file_data(brief),
            findings_path: create_file_data(_build_mock_findings(query)),
            sources_path: create_file_data(_build_mock_sources(query)),
            "/research_verification.md": create_file_data(_build_mock_verification(case, query)),
            "/final_report.md": create_file_data(report),
        }
    )
    final_answer = f"Research completed for {_normalize_title(query)}. Final report saved to /final_report.md."
    messages = _build_mock_messages(query, include_search=True, final_answer=final_answer)
    state = _mock_state_snapshot({"messages": messages, "files": files})
    return EvalRunResult(
        final_output=final_answer,
        state=state,
        thread_id=thread_id,
        trace_ref=_current_trace_ref(),
        raw_result={"messages": messages, "files": files},
        files=files,
        messages=messages,
        interrupts=interrupts,
        approval_mode=approval_mode,
        mode="mocked",
        preexisting_files=[],
    )


def _run_mock_multi_turn_case(case: dict[str, Any]) -> list[EvalRunResult]:
    thread_id = _default_thread_id(case["id"])
    cumulative_files: dict[str, Any] = {}
    results: list[EvalRunResult] = []

    for index, turn in enumerate(case.get("turns", [])):
        turn_case = {
            "id": f"{case['id']}::{turn.get('id', index + 1)}",
            "input": turn["user"],
            "approval_mode": turn.get("approval_mode", "auto_approve"),
        }
        result = _run_mock_case(turn_case)
        preexisting = sorted(cumulative_files.keys())
        current_files = dict(cumulative_files)
        current_files.update(result.files)
        state = _mock_state_snapshot({"messages": result.messages, "files": current_files})
        results.append(
            EvalRunResult(
                final_output=result.final_output,
                state=state,
                thread_id=thread_id,
                trace_ref=result.trace_ref,
                raw_result={"messages": result.messages, "files": current_files},
                files=current_files,
                messages=result.messages,
                interrupts=result.interrupts,
                approval_mode=result.approval_mode,
                mode="mocked",
                preexisting_files=preexisting,
            )
        )
        cumulative_files = current_files
    return results


def _run_mock_scoping_step(case: dict[str, Any]) -> EvalRunResult:
    brief = _build_mock_brief(case["input"])
    messages = [HumanMessage(content=case["input"])]
    state = _mock_state_snapshot({"messages": messages, "files": {}})
    interrupts = [
        {
            "type": "approval_request",
            "action": "Review and approve/reject the research brief",
            "approval_item": brief,
        }
    ]
    return EvalRunResult(
        final_output=None,
        state=state,
        thread_id=_default_thread_id(case["id"]),
        trace_ref=_current_trace_ref(),
        raw_result={"messages": messages, "__interrupt__": interrupts},
        files={},
        messages=messages,
        interrupts=interrupts,
        approval_mode=case.get("approval_mode", "auto_approve"),
        mode="mocked",
        preexisting_files=[],
    )


def _run_mock_research_first_tool_step(case: dict[str, Any]) -> dict[str, Any]:
    query = "Research the current open-source LLM landscape for enterprise teams."
    return {
        "messages": [
            HumanMessage(content=case["input"]),
            AIMessage(
                content="I should search first.",
                tool_calls=[{"name": "tavily_search", "args": {"query": query}, "id": "call-search-1", "type": "tool_call"}],
            ),
        ]
    }


def _run_mock_verification_step(case: dict[str, Any]) -> EvalRunResult:
    files = dict(_seed_files(case.get("setup_files")))
    verification = _build_mock_verification(case, case["input"])
    files["/research_verification.md"] = create_file_data(verification)
    messages = [HumanMessage(content=case["input"]), AIMessage(content="Verification completed.")]
    state = _mock_state_snapshot({"messages": messages, "files": files})
    return EvalRunResult(
        final_output="Verification completed.",
        state=state,
        thread_id=_default_thread_id(case["id"]),
        trace_ref=_current_trace_ref(),
        raw_result={"messages": messages, "files": files},
        files=files,
        messages=messages,
        interrupts=[],
        approval_mode="auto_approve",
        mode="mocked",
        preexisting_files=[],
    )


def _run_mock_report_step(case: dict[str, Any]) -> EvalRunResult:
    files = dict(_seed_files(case.get("setup_files")))
    report = _build_mock_report(case, case["input"])
    files["/final_report.md"] = create_file_data(report)
    messages = [HumanMessage(content=case["input"]), AIMessage(content="Report written to /final_report.md.")]
    state = _mock_state_snapshot({"messages": messages, "files": files})
    return EvalRunResult(
        final_output="Report written to /final_report.md.",
        state=state,
        thread_id=_default_thread_id(case["id"]),
        trace_ref=_current_trace_ref(),
        raw_result={"messages": messages, "files": files},
        files=files,
        messages=messages,
        interrupts=[],
        approval_mode="auto_approve",
        mode="mocked",
        preexisting_files=[],
    )


@contextmanager
def patched_search_tool(mode: str):
    if mode != "mocked":
        yield
        return

    @tool(parse_docstring=True)
    def fake_tavily_search(query: str, max_results: int = 1, topic: str = "general") -> str:
        """Search the web for information on a given query.

        Args:
            query: Search query to execute.
            max_results: Maximum number of results to return.
            topic: Topic filter.
        """
        return resolve_mock_search_results(query)

    with patch.object(research_agent_module, "tavily_search", fake_tavily_search):
        yield


def _finalize_result(
    *,
    agent: Any,
    config: dict[str, Any],
    raw_result: dict[str, Any],
    thread_id: str,
    mode: str,
    approval_mode: str,
    interrupts: list[dict[str, Any]],
    preexisting_files: list[str],
) -> EvalRunResult:
    state = agent.get_state(config)
    values = getattr(state, "values", {}) or {}
    files = raw_result.get("files")
    if not isinstance(files, dict):
        files = values.get("files", {})
    messages = list(values.get("messages") or raw_result.get("messages") or [])
    return EvalRunResult(
        final_output=_extract_final_answer({"messages": messages}) or _extract_final_answer(raw_result),
        state=state,
        thread_id=thread_id,
        trace_ref=_current_trace_ref(),
        raw_result=raw_result,
        files=files,
        messages=messages,
        interrupts=interrupts,
        approval_mode=approval_mode,
        mode=mode,
        preexisting_files=preexisting_files,
    )


def _invoke_until_complete(
    agent: Any,
    graph_input: dict[str, Any],
    *,
    config: dict[str, Any],
    approval_mode: str,
    stop_at_first_interrupt: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current_input: dict[str, Any] | Command = graph_input
    interrupts: list[dict[str, Any]] = []

    while True:
        result = agent.invoke(current_input, config=config)
        raw_interrupts = result.get("__interrupt__", [])
        if not raw_interrupts:
            return result, interrupts

        payload = _extract_interrupt_payload(raw_interrupts[0])
        interrupts.append(payload)
        if stop_at_first_interrupt or approval_mode == "auto_reject":
            return result, interrupts
        if approval_mode == "auto_approve":
            current_input = Command(resume={"approved": True})
            continue
        raise ValueError(f"Unsupported approval_mode: {approval_mode}")


def _run_case_with_agent(agent: Any, case: dict[str, Any], *, mode: str) -> EvalRunResult:
    thread_id = case.get("thread_id") or _default_thread_id(case["id"])
    config = {"configurable": {"thread_id": thread_id}}
    try:
        preexisting_files = list(get_virtual_files(agent.get_state(config)).keys())
    except Exception:
        preexisting_files = []
    graph_input: dict[str, Any] = {"messages": [{"role": "user", "content": case["input"]}]}
    seeded_files = _seed_files(case.get("setup_files"))
    if seeded_files:
        graph_input["files"] = seeded_files

    raw_result, interrupts = _invoke_until_complete(
        agent,
        graph_input,
        config=config,
        approval_mode=case.get("approval_mode", "auto_approve"),
        stop_at_first_interrupt=bool(case.get("stop_at_first_interrupt", False)),
    )
    return _finalize_result(
        agent=agent,
        config=config,
        raw_result=raw_result,
        thread_id=thread_id,
        mode=mode,
        approval_mode=case.get("approval_mode", "auto_approve"),
        interrupts=interrupts,
        preexisting_files=preexisting_files,
    )


@traceable(name="deep-research-eval-case", run_type="chain")
def run_case(case: dict[str, Any], *, mode: str = "mocked") -> EvalRunResult:
    if mode == "mocked":
        return _run_mock_case(case)
    with patched_search_tool(mode):
        agent = build_agent(skill=case.get("skills"))
    return _run_case_with_agent(agent, case, mode=mode)


@traceable(name="deep-research-eval-multi-turn", run_type="chain")
def run_multi_turn_case(case: dict[str, Any], *, mode: str = "mocked") -> list[EvalRunResult]:
    if mode == "mocked":
        return _run_mock_multi_turn_case(case)
    thread_id = _default_thread_id(case["id"])
    turns = case.get("turns", [])
    with patched_search_tool(mode):
        agent = build_agent(skill=case.get("skills"))

    results: list[EvalRunResult] = []
    for turn in turns:
        turn_case = {
            "id": f"{case['id']}::{turn.get('id', len(results) + 1)}",
            "input": turn["user"],
            "approval_mode": turn.get("approval_mode", "auto_approve"),
            "stop_at_first_interrupt": turn.get("stop_at_first_interrupt", False),
            "setup_files": case.get("setup_files") if not results else None,
            "thread_id": thread_id,
        }
        results.append(_run_case_with_agent(agent, turn_case, mode=mode))
    return results


def run_scoping_step(case: dict[str, Any], *, mode: str = "mocked") -> EvalRunResult:
    if mode == "mocked":
        return _run_mock_scoping_step(case)
    agent = create_deep_agent(
        model=scoping_model,
        tools=[think_tool, request_approval],
        system_prompt=SCOPING_AGENT_INSTRUCTIONS,
        backend=lambda runtime: StateBackend(runtime),
        checkpointer=MemorySaver(),
        name="eval-scoping-step",
    )
    scoped_case = {
        "id": case["id"],
        "input": case["input"],
        "approval_mode": case.get("approval_mode", "auto_approve"),
        "stop_at_first_interrupt": True,
    }
    return _run_case_with_agent(agent, scoped_case, mode="single-step")


def run_research_first_tool_step(case: dict[str, Any], *, mode: str = "mocked") -> dict[str, Any]:
    if mode == "mocked":
        return _run_mock_research_first_tool_step(case)
    with patched_search_tool(mode):
        subagent = research_agent_module.build_research_subagent()
    graph = create_agent(
        model=research_model,
        tools=subagent["tools"],
        middleware=subagent.get("middleware", []),
        system_prompt=subagent["system_prompt"],
        interrupt_before=["tools"],
        name="eval-research-first-tool",
    )
    return graph.invoke({"messages": [{"role": "user", "content": case["input"]}]})


def _run_role_agent(case: dict[str, Any], *, model: Any, system_prompt: str, tools: list[Any] | None = None) -> EvalRunResult:
    agent = create_deep_agent(
        model=model,
        tools=tools or [],
        system_prompt=system_prompt,
        backend=lambda runtime: StateBackend(runtime),
        checkpointer=MemorySaver(),
        name=f"eval-{case['id']}",
    )
    role_case = {
        "id": case["id"],
        "input": case["input"],
        "approval_mode": "auto_approve",
        "setup_files": case.get("setup_files"),
    }
    return _run_case_with_agent(agent, role_case, mode="single-step")


def run_verification_step(case: dict[str, Any], *, mode: str = "mocked") -> EvalRunResult:
    if mode == "mocked":
        return _run_mock_verification_step(case)
    return _run_role_agent(case, model=verify_model, system_prompt=VERIFICATION_INSTRUCTIONS)


def run_report_step(case: dict[str, Any], *, mode: str = "mocked") -> EvalRunResult:
    if mode == "mocked":
        return _run_mock_report_step(case)
    return _run_role_agent(case, model=report_model, system_prompt=REPORT_INSTRUCTIONS)
