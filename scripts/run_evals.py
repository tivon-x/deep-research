from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
import pytest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=root / ".env")

    parser = argparse.ArgumentParser(description="Run Deep Research evaluation suites.")
    parser.add_argument("--mode", choices=("mocked", "live"), default=os.getenv("EVAL_MODE", "mocked"))
    parser.add_argument(
        "--category",
        choices=("single_step", "full_turn", "multi_turn", "smoke", "all"),
        default="all",
    )
    parser.add_argument("-m", "--pytest-mark", default=None, help="Optional pytest mark expression.")
    args = parser.parse_args()

    target_map = {
        "single_step": ["evals/test_single_step.py"],
        "full_turn": ["evals/test_full_turn.py"],
        "multi_turn": ["evals/test_multi_turn.py"],
        "smoke": ["evals/smoke"],
        "all": ["evals"],
    }

    pytest_args = [*target_map[args.category], "--eval-mode", args.mode, "-q"]
    if args.pytest_mark:
        pytest_args.extend(["-m", args.pytest_mark])

    return pytest.main(pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())

