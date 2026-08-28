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
    version: int


@dataclass(frozen=True)
class ResourceSkillsPageDesktopDto:
    items: tuple[ResourceSkillDesktopDto, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "skillName"
    sort_direction: str = "asc"


__all__ = ["ResourceSkillDesktopDto", "ResourceSkillsPageDesktopDto"]
