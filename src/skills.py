"""Skill loading helpers for Deep Agents role-based skills."""

from __future__ import annotations

import re
from pathlib import Path

from deepagents.backends.utils import create_file_data

ROLE_NAMES = ("orchestrator", "scoping", "research", "verification", "report")


def normalize_skill_name(skill: str | None) -> str | None:
    if skill is None:
        return None
    normalized = skill.strip().strip("/")
    if not normalized:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]+", normalized):
        raise ValueError(
            "Invalid skill name. Use only letters, numbers, hyphens, and underscores."
        )
    return normalized


def role_skill_paths(skill: str | None, role: str) -> list[str]:
    normalized = normalize_skill_name(skill)
    if normalized is None:
        return []
    candidate = Path.cwd() / "skills" / normalized / role
    skill_file = candidate / "SKILL.md"
    if skill_file.is_file():
        return [f"/skills/{normalized}/{role}/"]
    return []


def resolve_role_skills(skill: str | None) -> dict[str, list[str]]:
    return {role: role_skill_paths(skill, role) for role in ROLE_NAMES}


def resolve_skill_seed_files(skill: str | None) -> dict[str, dict]:
    normalized = normalize_skill_name(skill)
    if normalized is None:
        return {}

    files: dict[str, dict] = {}
    for role in ROLE_NAMES:
        local_skill_file = Path.cwd() / "skills" / normalized / role / "SKILL.md"
        if not local_skill_file.is_file():
            continue
        content = local_skill_file.read_text(encoding="utf-8")
        virtual_path = f"/skills/{normalized}/{role}/SKILL.md"
        files[virtual_path] = create_file_data(content)

    return files
