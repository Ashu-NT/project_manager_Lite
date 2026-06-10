from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import TaskRecordViewModel


def to_skill_requirement_record_view_model(req) -> TaskRecordViewModel:
    skill_code = str(getattr(req, "skill_code", "") or "")
    cert_code = str(getattr(req, "certification_code", "") or "")
    code = skill_code or cert_code
    req_type = str(getattr(req, "requirement_type", "") or "")
    req_type_label = "Certification" if req_type == "certification" else "Skill"
    proficiency_label = str(getattr(req, "required_proficiency_label", "") or "")
    mode_label = str(getattr(req, "validation_mode_label", "") or "")
    notes = str(getattr(req, "notes", "") or "")
    state = {
        "requirementId": str(getattr(req, "id", "") or ""),
        "taskId": str(getattr(req, "task_id", "") or ""),
        "skillCode": skill_code,
        "certificationCode": cert_code,
        "requirementType": req_type,
        "requiredProficiency": str(getattr(req, "required_proficiency", "") or ""),
        "requiredProficiencyLabel": proficiency_label,
        "validationMode": str(getattr(req, "validation_mode", "") or ""),
        "validationModeLabel": mode_label,
        "notes": notes,
    }
    return TaskRecordViewModel(
        id=str(getattr(req, "id", "") or ""),
        title=code or "Unknown",
        status_label=proficiency_label,
        subtitle=f"{req_type_label} | Mode: {mode_label}",
        supporting_text=notes if notes else "No notes recorded.",
        meta_text=f"Validation: {mode_label}",
        can_primary_action=False,
        can_secondary_action=False,
        can_tertiary_action=False,
        state=state,
    )
