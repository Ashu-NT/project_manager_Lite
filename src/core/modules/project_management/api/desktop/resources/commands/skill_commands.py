from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAddSkillCommand:
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str = "intermediate"
    notes: str = ""


__all__ = ["ResourceAddSkillCommand"]
