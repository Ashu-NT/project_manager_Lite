from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.models.skills import (
    ResourceSkillDesktopDto,
)
from src.core.modules.project_management.application.resources.dto.responses.capabilities import (
    ResourceSkillResponse,
)


def serialize_skill(skill: ResourceSkillResponse) -> ResourceSkillDesktopDto:
    proficiency_raw = skill.proficiency.value
    return ResourceSkillDesktopDto(
        id=skill.id,
        resource_id=skill.resource_id,
        skill_code=skill.skill_code,
        skill_name=skill.skill_name,
        proficiency=proficiency_raw,
        proficiency_label=proficiency_raw.replace("_", " ").title(),
        notes=skill.notes or "",
        version=int(skill.version),
    )


__all__ = ["serialize_skill"]
