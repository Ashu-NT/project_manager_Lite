from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceAddSkillCommand,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceSkillViewModel,
)

from .validation import optional_text, require_text


def build_skills_state(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
) -> tuple[ResourceSkillViewModel, ...]:
    if not resource_id:
        return ()
    try:
        skills = desktop_api.list_resource_skills(resource_id)
    except Exception:
        return ()
    return tuple(
        ResourceSkillViewModel(
            id=s.id,
            skill_code=s.skill_code,
            skill_name=s.skill_name,
            proficiency=s.proficiency,
            proficiency_label=s.proficiency_label,
            notes=s.notes,
        )
        for s in skills
    )


def add_skill(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    payload: dict[str, Any],
) -> None:
    command = ResourceAddSkillCommand(
        resource_id=resource_id,
        skill_code=require_text(payload, "skillCode", "Skill code is required."),
        skill_name=optional_text(payload, "skillName") or payload.get("skillCode", ""),
        proficiency=optional_text(payload, "proficiency") or "intermediate",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.add_resource_skill(command)


def remove_skill(
    desktop_api: ProjectManagementResourcesDesktopApi,
    skill_id: str,
) -> None:
    normalized = (skill_id or "").strip()
    if not normalized:
        raise ValueError("Skill ID is required.")
    desktop_api.remove_resource_skill(normalized)
