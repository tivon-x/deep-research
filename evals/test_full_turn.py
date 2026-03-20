from __future__ import annotations

from pathlib import Path

import pytest

from evals.helpers.assertions import (
    assert_final_report,
    assert_required_artifacts,
    assert_required_trajectory,
)
from evals.helpers.runner import run_case


def _skill_case_available(case: dict) -> bool:
    skill = case.get("skills")
    if not skill:
        return True
    return (Path.cwd() / "skills" / skill).exists()


@pytest.mark.langsmith
@pytest.mark.live_model
@pytest.mark.slow
def test_full_turn_cases(full_turn_cases: list[dict], eval_mode: str) -> None:
    for case in full_turn_cases:
        if not _skill_case_available(case):
            continue

        result = run_case(case, mode=eval_mode)
        assert_required_trajectory(result, case)
        if case.get("expectations", {}).get("required_files"):
            assert_required_artifacts(result, case)
            assert_final_report(result, case)
