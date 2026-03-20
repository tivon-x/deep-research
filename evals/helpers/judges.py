from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field


class ReportJudgeResult(BaseModel):
    answers_question: bool
    grounded_in_findings: bool
    structure_clear: bool
    cites_sources: bool
    hallucination_risk: Literal["low", "medium", "high"]
    score: int = Field(ge=1, le=5)
    rationale: str


def judge_enabled(case: dict) -> bool:
    raw_flag = os.getenv("EVAL_ENABLE_JUDGE", "false").strip().lower()
    env_enabled = raw_flag in {"1", "true", "yes", "on"}
    case_judge = case.get("judge", {}).get("enabled", False)
    return bool(case_judge and env_enabled)


def judge_report(question: str, findings: str, report: str) -> ReportJudgeResult:
    from src.llm import main_model

    structured_model = main_model.with_structured_output(ReportJudgeResult)
    rubric = (
        "You are grading a deep-research report.\n"
        "Score the report against the question and findings.\n"
        "Be strict about unsupported claims and missing source grounding.\n"
        "Use a 1-5 score where 5 means strong and 1 means poor.\n\n"
        f"Question:\n{question}\n\n"
        f"Findings:\n{findings}\n\n"
        f"Final report:\n{report}\n"
    )
    return structured_model.invoke(rubric)
