from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.models.skills import (
    ResourceSkillDesktopDto,
)


def serialize_skill(skill) -> ResourceSkillDesktopDto:
    proficiency_raw = str(getattr(skill, "proficiency", "") or "intermediate")
    if hasattr(proficiency_raw, "value"):
        proficiency_raw = proficiency_raw.value
    return ResourceSkillDesktopDto(
        id=skill.id,
        resource_id=skill.resource_id,
        skill_code=skill.skill_code,
        skill_name=skill.skill_name,
        proficiency=proficiency_raw,
        proficiency_label=proficiency_raw.replace("_", " ").title(),
        notes=skill.notes or "",
    )


__all__ = ["serialize_skill"]
