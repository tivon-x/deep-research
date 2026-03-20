from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from evals.helpers.datasets import load_dataset


ROOT = Path(__file__).resolve().parents[1]


def _load_eval_env() -> None:
    candidates = [
        ROOT / ".env",
        ROOT.parent / "deep-research" / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return


_load_eval_env()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--eval-mode",
        action="store",
        default=os.getenv("EVAL_MODE", "mocked"),
        choices=("mocked", "live"),
        help="Evaluation execution mode.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "langsmith: emits LangSmith traces/feedback when enabled")
    config.addinivalue_line("markers", "live_model: uses the configured chat model")
    config.addinivalue_line("markers", "slow: slower end-to-end evaluation case")


@pytest.fixture(scope="session")
def eval_mode(pytestconfig: pytest.Config) -> str:
    return str(pytestconfig.getoption("--eval-mode"))


@pytest.fixture(scope="session")
def single_step_cases() -> list[dict]:
    return load_dataset("single_step")


@pytest.fixture(scope="session")
def full_turn_cases() -> list[dict]:
    return load_dataset("full_turn")


@pytest.fixture(scope="session")
def multi_turn_cases() -> list[dict]:
    return load_dataset("multi_turn")
