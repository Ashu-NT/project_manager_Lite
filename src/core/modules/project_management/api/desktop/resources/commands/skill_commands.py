from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAddSkillCommand:
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str = "intermediate"
    notes: str = ""


@dataclass(frozen=True)
class ResourceUpdateSkillCommand:
    skill_id: str
    expected_version: int
    skill_code: str
    skill_name: str
    proficiency: str = "intermediate"
    notes: str = ""


@dataclass(frozen=True)
class ResourceRemoveSkillCommand:
    skill_id: str
    expected_version: int


__all__ = [
    "ResourceAddSkillCommand",
    "ResourceRemoveSkillCommand",
    "ResourceUpdateSkillCommand",
]
