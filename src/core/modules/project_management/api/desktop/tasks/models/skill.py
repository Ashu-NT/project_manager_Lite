from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSkillRequirementDesktopDto:
    id: str
    task_id: str
    skill_code: str
    certification_code: str
    requirement_type: str
    required_proficiency: str
    required_proficiency_label: str
    validation_mode: str
    validation_mode_label: str
    notes: str
    version: int


__all__ = ["TaskSkillRequirementDesktopDto"]
