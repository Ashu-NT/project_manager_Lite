from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.skill import (
    TaskSkillRequirementDesktopDto,
)


def serialize_skill_requirement(req) -> TaskSkillRequirementDesktopDto:
    skill_code = str(getattr(req, "skill_code", "") or "")
    cert_code = str(getattr(req, "certification_code", "") or "")
    proficiency_raw = str(
        getattr(getattr(req, "required_proficiency", None), "value", None)
        or getattr(req, "required_proficiency", "")
        or "intermediate"
    )
    mode_raw = str(
        getattr(getattr(req, "validation_mode", None), "value", None)
        or getattr(req, "validation_mode", "")
        or "warn"
    )
    proficiency_labels = {
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "expert": "Expert",
    }
    mode_labels = {"warn": "Warn", "block": "Block", "override": "Override"}
    return TaskSkillRequirementDesktopDto(
        id=str(getattr(req, "id", "") or ""),
        task_id=str(getattr(req, "task_id", "") or ""),
        skill_code=skill_code,
        certification_code=cert_code,
        requirement_type="certification" if cert_code else "skill",
        required_proficiency=proficiency_raw,
        required_proficiency_label=proficiency_labels.get(
            proficiency_raw.lower(), proficiency_raw.title()
        ),
        validation_mode=mode_raw,
        validation_mode_label=mode_labels.get(mode_raw.lower(), mode_raw.title()),
        notes=str(getattr(req, "notes", "") or ""),
        version=int(getattr(req, "version", 1) or 1),
    )


__all__ = ["serialize_skill_requirement"]
