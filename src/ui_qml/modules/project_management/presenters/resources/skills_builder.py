from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceAddSkillCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateSkillCommand,
)
from .validation import optional_text, require_text


def build_skills_page(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_skills_page(resource_id, **query)
    return {
        "items": [
            {
                "id": skill.id,
                "title": skill.skill_name,
                "subtitle": skill.skill_code,
                "statusLabel": skill.proficiency_label,
                "metaText": skill.notes or "-",
                "skillCode": skill.skill_code,
                "skillName": skill.skill_name,
                "proficiency": skill.proficiency,
                "proficiencyLabel": skill.proficiency_label,
                "notes": skill.notes,
                "version": skill.version,
            }
            for skill in page.items
        ],
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }

def add_skill(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    payload: dict[str, Any],
) -> None:
    command = ResourceAddSkillCommand(
        resource_id=resource_id,
        skill_code=require_text(payload, "skillCode", "Skill code is required."),
        skill_name=require_text(payload, "skillName", "Skill name is required."),
        proficiency=require_text(
            payload, "proficiency", "Skill proficiency is required."
        ),
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
            skill_name=require_text(payload, "skillName", "Skill name is required."),
            proficiency=require_text(
                payload, "proficiency", "Skill proficiency is required."
            ),
            notes=optional_text(payload, "notes") or "",
        )
    )
