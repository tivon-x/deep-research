from __future__ import annotations

import pytest

from evals.helpers.assertions import (
    assert_report_step,
    assert_research_first_tool,
    assert_scoping_step,
    assert_verification_step,
)
from evals.helpers.runner import (
    run_report_step,
    run_research_first_tool_step,
    run_scoping_step,
    run_verification_step,
)


@pytest.mark.langsmith
@pytest.mark.live_model
@pytest.mark.parametrize(
    "case",
    [
        pytest.param("scoping_remote_work_brief", id="scoping"),
        pytest.param("research_first_tool_open_source_llm", id="research-first-tool"),
        pytest.param("verification_incomplete_findings", id="verification"),
        pytest.param("report_structure_remote_work", id="report"),
    ],
)
def test_single_step_cases(case: str, single_step_cases: list[dict], eval_mode: str) -> None:
    selected = next(item for item in single_step_cases if item["id"] == case)
    kind = selected["kind"]

    if kind == "scoping":
        result = run_scoping_step(selected, mode=eval_mode)
        assert_scoping_step(result, selected)
        return

    if kind == "research_first_tool":
        result = run_research_first_tool_step(selected, mode=eval_mode)
        assert_research_first_tool(result, selected)
        return

    if kind == "verification":
        result = run_verification_step(selected, mode=eval_mode)
        assert_verification_step(result, selected)
        return

    if kind == "report":
        result = run_report_step(selected, mode=eval_mode)
        assert_report_step(result, selected)
        return

    raise AssertionError(f"Unhandled single-step kind: {kind}")
