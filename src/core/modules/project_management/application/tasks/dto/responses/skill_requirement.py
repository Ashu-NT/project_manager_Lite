"""Neutral skill requirement response; labels belong to the presenter."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSkillRequirementResponseDto:
    id: str
    task_id: str
    skill_code: str | None
    certification_code: str | None
    required_proficiency: str
    validation_mode: str
    notes: str
    version: int
