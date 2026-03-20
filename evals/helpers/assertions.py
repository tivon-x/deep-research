from __future__ import annotations

from typing import Any

from evals.helpers.judges import judge_enabled, judge_report
from evals.helpers.runner import EvalRunResult, record_feedback
from evals.helpers.state import (
    count_citation_markers,
    count_markdown_headings,
    extract_verification_status,
    get_virtual_file,
    list_virtual_files,
)
from evals.helpers.traces import collect_tool_calls, count_tool_calls, tool_call_names


PLACEHOLDER_TOKENS = ("TODO", "TBD", "lorem ipsum", "citation needed")


def _all_findings_text(result: EvalRunResult) -> str:
    chunks: list[str] = []
    for path in list_virtual_files(result.state, prefix="/research_findings/"):
        content = get_virtual_file(result.state, path)
        if content:
            chunks.append(content)
    return "\n\n".join(chunks)


def assert_required_artifacts(result: EvalRunResult, case: dict[str, Any]) -> None:
    expectations = case.get("expectations", {})
    for path in expectations.get("required_files", []):
        content = get_virtual_file(result.state, path)
        assert content is not None, f"Required artifact missing: {path}"
        assert content.strip(), f"Artifact was empty: {path}"

    findings_expectation = expectations.get("findings", {})
    min_files = findings_expectation.get("min_files")
    if min_files is not None:
        findings_files = list_virtual_files(result.state, prefix="/research_findings/")
        assert len(findings_files) >= min_files, f"Expected at least {min_files} findings files, got {len(findings_files)}."

    verification_text = get_virtual_file(result.state, "/research_verification.md")
    allowed_statuses = expectations.get("verification_status_allowed", [])
    if allowed_statuses:
        actual_status = extract_verification_status(verification_text)
        assert actual_status in allowed_statuses, f"Unexpected verification status: {actual_status}"
        record_feedback(result.trace_ref, "verification_status_correct", 1.0, actual_status)


def assert_required_trajectory(result: EvalRunResult, case: dict[str, Any]) -> None:
    expectations = case.get("expectations", {})
    collect_tool_calls(result.messages)
    executed_tool_names = tool_call_names(result.messages, executed_only=True)

    for tool_name in expectations.get("required_tools_any_order", []):
        if tool_name in executed_tool_names:
            continue
        if result.mode == "live" and tool_name == "tavily_search":
            findings_files = list_virtual_files(result.state, prefix="/research_findings/")
            assert findings_files, (
                "Did not observe top-level tavily_search calls in live mode, and no research findings files were present "
                "to support the inference that research ran."
            )
            continue
        assert tool_name in executed_tool_names, f"Required tool was not executed: {tool_name}"

    for tool_name in expectations.get("forbidden_tools", []):
        assert tool_name not in executed_tool_names, f"Forbidden tool was executed: {tool_name}"

    budgets = expectations.get("budgets", {})
    max_calls = budgets.get("max_search_calls")
    if max_calls is not None:
        actual_calls = count_tool_calls(result.messages, "tavily_search", executed_only=True)
        if result.mode == "live" and actual_calls == 0:
            findings_files = list_virtual_files(result.state, prefix="/research_findings/")
            assert findings_files, "Budget check could not observe search calls and no findings files were produced."
        else:
            assert actual_calls <= max_calls, f"tavily_search exceeded budget: {actual_calls} > {max_calls}"
            record_feedback(result.trace_ref, "search_budget_ok", 1.0 if actual_calls <= max_calls else 0.0, f"{actual_calls}/{max_calls}")

    if expectations.get("must_interrupt_for_approval"):
        assert result.interrupts, "Expected an approval interrupt but none was observed."
        assert result.interrupts[0].get("type") == "approval_request"

    if expectations.get("should_not_search_before_approval"):
        actual_calls = count_tool_calls(result.messages, "tavily_search", executed_only=True)
        assert actual_calls == 0, "Search tool should not run before approval is resumed."


def assert_final_report(result: EvalRunResult, case: dict[str, Any]) -> None:
    expectations = case.get("expectations", {})
    report_expectations = expectations.get("final_report", {})
    report = get_virtual_file(result.state, "/final_report.md")
    assert report is not None, "Missing /final_report.md"
    assert report.strip(), "Final report was empty"

    min_headings = report_expectations.get("min_headings")
    if min_headings is not None:
        actual_headings = count_markdown_headings(report)
        assert actual_headings >= min_headings, f"Expected >= {min_headings} headings, got {actual_headings}"

    min_citations = report_expectations.get("min_citations")
    if min_citations is not None:
        actual_citations = count_citation_markers(report)
        assert actual_citations >= min_citations, f"Expected >= {min_citations} citation markers, got {actual_citations}"
        record_feedback(result.trace_ref, "citation_quality", 1.0 if actual_citations >= min_citations else 0.0, str(actual_citations))

    for token in PLACEHOLDER_TOKENS:
        assert token.lower() not in report.lower(), f"Placeholder token found in report: {token}"

    for snippet in report_expectations.get("report_must_include", []):
        assert snippet.lower() in report.lower(), f"Expected report to mention: {snippet}"

    if report_expectations.get("must_answer_user_question"):
        question = case.get("input") or ""
        keywords = [word.lower() for word in question.split() if len(word) > 4][:4]
        if keywords:
            assert any(keyword in report.lower() for keyword in keywords), "Report did not appear to answer the user question."
        record_feedback(result.trace_ref, "answers_question", 1.0, "Heuristic keyword match passed")

    if judge_enabled(case):
        judge_result = judge_report(case["input"], _all_findings_text(result), report)
        assert judge_result.score >= case.get("judge", {}).get("min_score", 3), judge_result.rationale
        record_feedback(result.trace_ref, "report_judge_score", float(judge_result.score), judge_result.rationale)
        record_feedback(result.trace_ref, "grounded_in_findings", 1.0 if judge_result.grounded_in_findings else 0.0, judge_result.rationale)


def assert_scoping_step(result: EvalRunResult, case: dict[str, Any]) -> None:
    assert result.interrupts, "Scoping step should interrupt for approval."
    brief = result.interrupts[0].get("approval_item", "")
    expectations = case.get("expectations", {})
    for text in expectations.get("brief_must_include", []):
        assert text.lower() in brief.lower(), f"Research brief missing expected text: {text}"
    min_subquestions, max_subquestions = expectations.get("subquestions_between", [2, 5])
    subquestion_lines = [
        line for line in brief.splitlines() if line.strip().startswith(("1.", "2.", "3.", "4.", "5."))
    ]
    assert min_subquestions <= len(subquestion_lines) <= max_subquestions


def assert_research_first_tool(step_result: dict[str, Any], case: dict[str, Any]) -> None:
    messages = step_result.get("messages", [])
    calls = collect_tool_calls(messages)
    assistant_calls = [call for call in calls if call["event"] == "assistant_tool_call"]
    assert assistant_calls, "Expected at least one pre-tool call."
    first_call = assistant_calls[0]
    expected_tool = case.get("expectations", {}).get("required_first_tool")
    assert first_call["name"] == expected_tool, f"Expected first tool {expected_tool}, got {first_call['name']}"
    query = str(first_call.get("args", {}).get("query", ""))
    for term in case.get("expectations", {}).get("required_query_terms", []):
        assert term.lower() in query.lower(), f"Expected tool query to include term: {term}"


def assert_verification_step(result: EvalRunResult, case: dict[str, Any]) -> None:
    text = get_virtual_file(result.state, "/research_verification.md") or result.final_output or ""
    expected_statuses = case.get("expectations", {}).get("verification_status_allowed", [])
    actual_status = extract_verification_status(text)
    assert actual_status in expected_statuses, f"Unexpected verification status: {actual_status}"


def assert_report_step(result: EvalRunResult, case: dict[str, Any]) -> None:
    report = get_virtual_file(result.state, "/final_report.md")
    assert report is not None, "Report step did not write /final_report.md"
    min_headings = case.get("expectations", {}).get("min_headings", 3)
    assert count_markdown_headings(report) >= min_headings
    for snippet in case.get("expectations", {}).get("report_must_include", []):
        assert snippet.lower() in report.lower()
