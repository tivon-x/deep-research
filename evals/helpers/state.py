from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def file_data_to_text(file_data: Any) -> str:
    if isinstance(file_data, str):
        return file_data
    if isinstance(file_data, Mapping):
        content = file_data.get("content")
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        if isinstance(content, str):
            return content
    return str(file_data)


def get_virtual_files(state: Any) -> dict[str, Any]:
    if isinstance(state, Mapping):
        files = state.get("files")
        if isinstance(files, dict):
            return files
    values = getattr(state, "values", None)
    if isinstance(values, Mapping):
        files = values.get("files")
        if isinstance(files, dict):
            return files
    return {}


def get_virtual_file(state: Any, path: str) -> str | None:
    files = get_virtual_files(state)
    raw = files.get(path)
    if raw is None:
        return None
    return file_data_to_text(raw)


def list_virtual_files(state: Any, prefix: str | None = None) -> list[str]:
    paths = sorted(get_virtual_files(state).keys())
    if prefix is None:
        return paths
    return [path for path in paths if path.startswith(prefix)]


def extract_verification_status(text: str | None) -> str | None:
    if not text:
        return None
    allowed = ("COMPLETE", "NEEDS_MINOR_ADDITIONS", "NEEDS_MAJOR_REWORK")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in allowed:
            return stripped
    return None


def count_markdown_headings(text: str | None) -> int:
    if not text:
        return 0
    return sum(1 for line in text.splitlines() if line.strip().startswith("#"))


def count_citation_markers(text: str | None) -> int:
    if not text:
        return 0
    total = 0
    for token in ("[1]", "[2]", "[3]", "[4]", "[5]", "[6]"):
        total += text.count(token)
    return total

