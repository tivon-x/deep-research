from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DATASET_DIR = Path(__file__).resolve().parents[1] / "datasets"


def load_dataset(name: str) -> list[dict[str, Any]]:
    dataset_path = DATASET_DIR / f"{name}.yaml"
    payload = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or []
    if not isinstance(payload, list):
        raise TypeError(f"Dataset {dataset_path} must contain a top-level list.")
    return payload


def find_case(dataset_name: str, case_id: str) -> dict[str, Any]:
    for case in load_dataset(dataset_name):
        if case.get("id") == case_id:
            return case
    raise KeyError(f"Case '{case_id}' not found in dataset '{dataset_name}'.")

