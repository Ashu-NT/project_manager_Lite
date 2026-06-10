from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    run_mutation,
    serialize_resource_certification_view_models,
    serialize_resource_skill_view_models,
)


def set_resource_skills(controller, skills: list[dict[str, object]]) -> None:
    if skills == controller._resource_skills:
        return
    controller._resource_skills = skills
    controller._table_models.resource_skills.set_rows(skills)
    controller.resourceSkillsChanged.emit()


def set_resource_certifications(controller, certs: list[dict[str, object]]) -> None:
    if certs == controller._resource_certifications:
        return
    controller._resource_certifications = certs
    controller._table_models.resource_certifications.set_rows(certs)
    controller.resourceCertificationsChanged.emit()


def reload_skills_and_certs(controller, resource_id: str) -> None:
    rid = (resource_id or "").strip()
    if not rid:
        set_resource_skills(controller, [])
        set_resource_certifications(controller, [])
        return
    controller._clear_section_error("skills")
    try:
        skills = controller._resources_workspace_presenter.build_skills_state(rid)
        set_resource_skills(controller, serialize_resource_skill_view_models(skills))
    except Exception as exc:
        set_resource_skills(controller, [])
        controller._set_section_error("skills", str(exc))
    try:
        certs = controller._resources_workspace_presenter.build_certifications_state(rid)
        set_resource_certifications(controller, serialize_resource_certification_view_models(certs))
    except Exception as exc:
        set_resource_certifications(controller, [])
        controller._set_section_error("skills", str(exc))


def load_skills_and_certs(controller, resource_id: str) -> None:
    reload_skills_and_certs(controller, (resource_id or "").strip())


def add_skill(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.add_skill(
            resource_id, dict(payload)
        ),
        success_message="Skill added.",
        on_success=lambda: reload_skills_and_certs(controller, resource_id),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def remove_skill(controller, skill_id: str) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.remove_skill(skill_id),
        success_message="Skill removed.",
        on_success=lambda: reload_skills_and_certs(controller, resource_id),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def add_certification(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.add_certification(
            resource_id, dict(payload)
        ),
        success_message="Certification added.",
        on_success=lambda: reload_skills_and_certs(controller, resource_id),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def remove_certification(controller, cert_id: str) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return run_mutation(
        operation=lambda: controller._resources_workspace_presenter.remove_certification(cert_id),
        success_message="Certification removed.",
        on_success=lambda: reload_skills_and_certs(controller, resource_id),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


__all__ = [
    "add_certification",
    "add_skill",
    "load_skills_and_certs",
    "reload_skills_and_certs",
    "remove_certification",
    "remove_skill",
    "set_resource_certifications",
    "set_resource_skills",
]
