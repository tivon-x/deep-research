from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.helpers.datasets import load_dataset


def main() -> None:
    summary = {
        "single_step_cases": len(load_dataset("single_step")),
        "full_turn_cases": len(load_dataset("full_turn")),
        "multi_turn_cases": len(load_dataset("multi_turn")),
    }
    output_path = ROOT / "evals" / "eval_summary.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
