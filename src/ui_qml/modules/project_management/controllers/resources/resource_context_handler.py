from __future__ import annotations


def _direction(value: int) -> str:
    return "desc" if int(value) else "asc"


def _apply_projects_page(controller, result: dict[str, object], resource_id: str) -> None:
    controller._resource_projects = result
    controller._table_models.resource_projects.set_rows(result.get("items", []))
    controller._resource_projects_page = int(result.get("page", 1) or 1)
    controller._resource_projects_page_size = int(result.get("pageSize", 25) or 25)
    controller._resource_projects_total = int(result.get("total", 0) or 0)
    controller._resource_projects_sort_key = str(result.get("sortKey", "projectName"))
    controller._resource_projects_sort_direction = (
        1 if str(result.get("sortDirection", "asc")) == "desc" else 0
    )
    controller._resource_projects_loaded_for = resource_id
    controller.resourceProjectsChanged.emit()


def load_resource_projects(controller, *, force: bool = False) -> None:
    resource_id = controller._selected_resource_id
    if not resource_id:
        controller._clear_resource_projects()
        return
    if not force and controller._resource_projects_loaded_for == resource_id:
        return
    controller._resource_projects_request_id += 1
    request_id = controller._resource_projects_request_id
    controller._resource_projects_loading = True
    controller.resourceProjectsLoadingChanged.emit()
    controller._clear_section_error("projects")
    try:
        result = controller._resources_workspace_presenter.build_resource_projects_page(
            resource_id,
            search_text=controller._resource_projects_search,
            active=controller._resource_projects_active,
            status=controller._resource_projects_status,
            page=controller._resource_projects_page,
            page_size=controller._resource_projects_page_size,
            sort_key=controller._resource_projects_sort_key,
            sort_direction=_direction(controller._resource_projects_sort_direction),
        )
        if request_id == controller._resource_projects_request_id and resource_id == controller._selected_resource_id:
            _apply_projects_page(controller, result, resource_id)
    except Exception as exc:
        if request_id == controller._resource_projects_request_id:
            controller._set_section_error("projects", str(exc))
    finally:
        if request_id == controller._resource_projects_request_id:
            controller._resource_projects_loading = False
            controller.resourceProjectsLoadingChanged.emit()


def _apply_assignments_page(controller, result: dict[str, object], resource_id: str) -> None:
    controller._resource_assignments = result
    controller._table_models.resource_assignments.set_rows(result.get("items", []))
    controller._resource_assignments_page = int(result.get("page", 1) or 1)
    controller._resource_assignments_page_size = int(result.get("pageSize", 25) or 25)
    controller._resource_assignments_total = int(result.get("total", 0) or 0)
    controller._resource_assignments_sort_key = str(result.get("sortKey", "scheduledStart"))
    controller._resource_assignments_sort_direction = (
        1 if str(result.get("sortDirection", "asc")) == "desc" else 0
    )
    controller._resource_assignments_loaded_for = resource_id
    controller.resourceAssignmentsChanged.emit()


def load_resource_assignments(controller, *, force: bool = False) -> None:
    resource_id = controller._selected_resource_id
    if not resource_id:
        controller._clear_resource_assignments()
        return
    if not force and controller._resource_assignments_loaded_for == resource_id:
        return
    controller._resource_assignments_request_id += 1
    request_id = controller._resource_assignments_request_id
    controller._resource_assignments_loading = True
    controller.resourceAssignmentsLoadingChanged.emit()
    controller._clear_section_error("assignments")
    try:
        result = controller._resources_workspace_presenter.build_resource_assignments_page(
            resource_id,
            search_text=controller._resource_assignments_search,
            project_id=controller._resource_assignments_project_id,
            task_status=controller._resource_assignments_task_status,
            assignment_status=controller._resource_assignments_status,
            lifecycle=controller._resource_assignments_lifecycle,
            start_date=controller._resource_assignments_start_date,
            end_date=controller._resource_assignments_end_date,
            page=controller._resource_assignments_page,
            page_size=controller._resource_assignments_page_size,
            sort_key=controller._resource_assignments_sort_key,
            sort_direction=_direction(controller._resource_assignments_sort_direction),
        )
        if request_id == controller._resource_assignments_request_id and resource_id == controller._selected_resource_id:
            _apply_assignments_page(controller, result, resource_id)
    except Exception as exc:
        if request_id == controller._resource_assignments_request_id:
            controller._set_section_error("assignments", str(exc))
    finally:
        if request_id == controller._resource_assignments_request_id:
            controller._resource_assignments_loading = False
            controller.resourceAssignmentsLoadingChanged.emit()


def _apply_activity_page(controller, result: dict[str, object], resource_id: str) -> None:
    controller._resource_activity = result
    controller._resource_activity_page = int(result.get("page", 1) or 1)
    controller._resource_activity_page_size = int(result.get("pageSize", 25) or 25)
    controller._resource_activity_total = int(result.get("total", 0) or 0)
    controller._resource_activity_loaded_for = resource_id
    controller.resourceActivityChanged.emit()


def load_resource_activity(controller, *, force: bool = False) -> None:
    resource_id = controller._selected_resource_id
    if not resource_id:
        controller._clear_resource_activity()
        return
    if not force and controller._resource_activity_loaded_for == resource_id:
        return
    controller._resource_activity_request_id += 1
    request_id = controller._resource_activity_request_id
    controller._resource_activity_loading = True
    controller.resourceActivityLoadingChanged.emit()
    controller._clear_section_error("activity")
    try:
        result = controller._resources_workspace_presenter.build_resource_activity_page(
            resource_id,
            category=controller._resource_activity_category,
            start_date=controller._resource_activity_start_date,
            end_date=controller._resource_activity_end_date,
            page=controller._resource_activity_page,
            page_size=controller._resource_activity_page_size,
        )
        if request_id == controller._resource_activity_request_id and resource_id == controller._selected_resource_id:
            _apply_activity_page(controller, result, resource_id)
    except Exception as exc:
        if request_id == controller._resource_activity_request_id:
            controller._set_section_error("activity", str(exc))
    finally:
        if request_id == controller._resource_activity_request_id:
            controller._resource_activity_loading = False
            controller.resourceActivityLoadingChanged.emit()


def clear_resource_context(controller) -> None:
    controller._resource_projects_request_id += 1
    controller._resource_assignments_request_id += 1
    controller._resource_activity_request_id += 1
    controller._clear_resource_projects()
    controller._clear_resource_assignments()
    controller._clear_resource_activity()


__all__ = [
    "clear_resource_context",
    "load_resource_activity",
    "load_resource_assignments",
    "load_resource_projects",
]
