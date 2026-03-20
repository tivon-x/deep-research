from __future__ import annotations

from evals.helpers.assertions import (
    assert_final_report,
    assert_required_artifacts,
    assert_required_trajectory,
)
from evals.helpers.datasets import find_case
from evals.helpers.runner import run_case


def test_mocked_pipeline_smoke(eval_mode: str) -> None:
    case = find_case("full_turn", "full_turn_remote_work")
    result = run_case(case, mode=eval_mode)
    assert_required_trajectory(result, case)
    assert_required_artifacts(result, case)
    assert_final_report(result, case)

