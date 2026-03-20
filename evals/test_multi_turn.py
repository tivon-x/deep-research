from __future__ import annotations

import pytest

from evals.helpers.assertions import assert_final_report, assert_required_artifacts
from evals.helpers.runner import run_multi_turn_case


@pytest.mark.langsmith
@pytest.mark.live_model
@pytest.mark.slow
def test_multi_turn_cases(multi_turn_cases: list[dict], eval_mode: str) -> None:
    for case in multi_turn_cases:
        results = run_multi_turn_case(case, mode=eval_mode)
        assert len(results) == len(case["turns"])

        for result, turn in zip(results, case["turns"], strict=True):
            turn_case = {
                "input": turn["user"],
                "expectations": {
                    "required_files": turn.get("assertions", {}).get("required_files", []),
                    "final_report": {
                        "report_must_include": turn.get("assertions", {}).get("report_must_include", []),
                    },
                },
            }
            assert_required_artifacts(result, turn_case)
            assert_final_report(result, turn_case)
            if turn.get("assertions", {}).get("should_reuse_existing_context"):
                assert result.preexisting_files, "Expected prior state to be present before follow-up turn."
                assert "/final_report.md" in result.preexisting_files

