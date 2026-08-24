from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceAddSkillCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateSkillCommand,
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
    skills = desktop_api.list_resource_skills(resource_id)
    return tuple(
        ResourceSkillViewModel(
            id=s.id,
            skill_code=s.skill_code,
            skill_name=s.skill_name,
            proficiency=s.proficiency,
            proficiency_label=s.proficiency_label,
            notes=s.notes,
            version=s.version,
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
    expected_version: int,
) -> None:
    normalized = (skill_id or "").strip()
    if not normalized:
        raise ValueError("Skill ID is required.")
    desktop_api.remove_resource_skill(
        ResourceRemoveSkillCommand(
            skill_id=normalized,
            expected_version=expected_version,
        )
    )


def update_skill(
    desktop_api: ProjectManagementResourcesDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.update_resource_skill(
        ResourceUpdateSkillCommand(
            skill_id=require_text(payload, "skillId", "Skill ID is required."),
            expected_version=int(payload.get("expectedVersion", 0) or 0),
            skill_code=require_text(payload, "skillCode", "Skill code is required."),
            skill_name=optional_text(payload, "skillName") or payload.get("skillCode", ""),
            proficiency=optional_text(payload, "proficiency") or "intermediate",
            notes=optional_text(payload, "notes") or "",
        )
    )
