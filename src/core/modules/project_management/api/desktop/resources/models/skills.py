from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSkillDesktopDto:
    id: str
    resource_id: str
    skill_code: str
    skill_name: str
    proficiency: str
    proficiency_label: str
    notes: str


__all__ = ["ResourceSkillDesktopDto"]
