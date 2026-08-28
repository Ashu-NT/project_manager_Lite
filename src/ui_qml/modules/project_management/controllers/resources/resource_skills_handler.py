from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


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


def _direction(value: int) -> str:
    return "desc" if int(value) else "asc"


def reload_skills(controller, resource_id: str) -> None:
    rid = (resource_id or "").strip()
    if not rid:
        set_resource_skills(controller, [])
        controller._resource_skills_page = 1
        controller._resource_skills_total = 0
        if controller._resource_skill_count:
            controller._resource_skill_count = 0
            controller.resourceSkillCountChanged.emit()
        controller.resourceSkillsChanged.emit()
        return
    controller._clear_section_error("skills")
    try:
        result = controller._resources_workspace_presenter.build_resource_skills_page(
            rid,
            search_text=controller._resource_skills_search,
            proficiency=controller._resource_skills_proficiency,
            page=controller._resource_skills_page,
            page_size=controller._resource_skills_page_size,
            sort_key=controller._resource_skills_sort_key,
            sort_direction=_direction(controller._resource_skills_sort_direction),
        )
        controller._resource_skills_page = int(result.get("page", 1) or 1)
        controller._resource_skills_page_size = int(result.get("pageSize", 25) or 25)
        controller._resource_skills_total = int(result.get("total", 0) or 0)
        controller._resource_skills_sort_key = str(result.get("sortKey", "skillName"))
        controller._resource_skills_sort_direction = (
            1 if str(result.get("sortDirection", "asc")) == "desc" else 0
        )
        set_resource_skills(controller, list(result.get("items", [])))
        if controller._resource_skill_count != controller._resource_skills_total:
            controller._resource_skill_count = controller._resource_skills_total
            controller.resourceSkillCountChanged.emit()
        controller.resourceSkillsChanged.emit()
    except Exception as exc:
        set_resource_skills(controller, [])
        controller._set_section_error("skills", str(exc))


def reload_certifications(controller, resource_id: str) -> None:
    rid = (resource_id or "").strip()
    if not rid:
        set_resource_certifications(controller, [])
        controller._resource_certifications_page = 1
        controller._resource_certifications_total = 0
        if controller._resource_certification_count:
            controller._resource_certification_count = 0
            controller.resourceCertificationCountChanged.emit()
        controller.resourceCertificationsChanged.emit()
        return
    controller._clear_section_error("skills")
    try:
        result = (
            controller._resources_workspace_presenter.build_resource_certifications_page(
                rid,
                search_text=controller._resource_certifications_search,
                status=controller._resource_certifications_status,
                page=controller._resource_certifications_page,
                page_size=controller._resource_certifications_page_size,
                sort_key=controller._resource_certifications_sort_key,
                sort_direction=_direction(
                    controller._resource_certifications_sort_direction
                ),
            )
        )
        controller._resource_certifications_page = int(result.get("page", 1) or 1)
        controller._resource_certifications_page_size = int(
            result.get("pageSize", 25) or 25
        )
        controller._resource_certifications_total = int(result.get("total", 0) or 0)
        controller._resource_certifications_sort_key = str(
            result.get("sortKey", "certificationName")
        )
        controller._resource_certifications_sort_direction = (
            1 if str(result.get("sortDirection", "asc")) == "desc" else 0
        )
        set_resource_certifications(controller, list(result.get("items", [])))
        if controller._resource_certification_count != controller._resource_certifications_total:
            controller._resource_certification_count = controller._resource_certifications_total
            controller.resourceCertificationCountChanged.emit()
        controller.resourceCertificationsChanged.emit()
    except Exception as exc:
        set_resource_certifications(controller, [])
        controller._set_section_error("skills", str(exc))


def reload_skills_and_certs(controller, resource_id: str) -> None:
    reload_skills(controller, resource_id)
    reload_certifications(controller, resource_id)


def load_skills_and_certs(controller, resource_id: str) -> None:
    reload_skills_and_certs(controller, (resource_id or "").strip())


def _mutate(controller, *, operation, message: str, refresh) -> dict[str, object]:
    return run_mutation(
        operation=operation,
        success_message=message,
        on_success=refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        safe_errors=True,
    )


def add_skill(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.add_skill(
            resource_id, dict(payload)
        ),
        message="Skill added.",
        refresh=lambda: reload_skills(controller, resource_id),
    )


def update_skill(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.update_skill(
            dict(payload)
        ),
        message="Skill updated.",
        refresh=lambda: reload_skills(controller, resource_id),
    )


def remove_skill(controller, skill_id: str, expected_version: int) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.remove_skill(
            skill_id, expected_version
        ),
        message="Skill removed.",
        refresh=lambda: reload_skills(controller, resource_id),
    )


def add_certification(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.add_certification(
            resource_id, dict(payload)
        ),
        message="Certification added.",
        refresh=lambda: reload_certifications(controller, resource_id),
    )


def update_certification(controller, payload: dict[str, object]) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.update_certification(
            dict(payload)
        ),
        message="Certification updated.",
        refresh=lambda: reload_certifications(controller, resource_id),
    )


def remove_certification(
    controller, cert_id: str, expected_version: int
) -> dict[str, object]:
    resource_id = str(controller._selected_resource_id or "")
    return _mutate(
        controller,
        operation=lambda: controller._resources_workspace_presenter.remove_certification(
            cert_id, expected_version
        ),
        message="Certification removed.",
        refresh=lambda: reload_certifications(controller, resource_id),
    )


__all__ = [
    "add_certification",
    "add_skill",
    "load_skills_and_certs",
    "reload_certifications",
    "reload_skills",
    "reload_skills_and_certs",
    "remove_certification",
    "remove_skill",
    "set_resource_certifications",
    "set_resource_skills",
    "update_certification",
    "update_skill",
]
