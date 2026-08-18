from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_project_detail_view_model,
)


def select_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip()
    if normalized == controller._selected_project_id:
        return
    controller._set_selected_project_id(normalized)


def activate_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip()
    if not normalized:
        return
    controller._set_selected_project_id(normalized)
    reset_project_lazy_sections(controller)
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        ws = controller._projects_workspace_presenter.build_project_detail_state(
            project_id=normalized,
        )
        controller._set_selected_project_id(ws.selected_project_id)
        controller._set_selected_project(
            serialize_project_detail_view_model(ws.selected_project_detail)
        )
    except Exception as exc:
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


def set_search_text(controller, text: str) -> None:
    normalized = (text or "").strip()
    if normalized == controller._search_text:
        return
    controller._set_search_text(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_status_filter(controller, status_filter: str) -> None:
    normalized = (status_filter or "").strip().lower() or "all"
    if normalized == controller._selected_status_filter.lower():
        return
    controller._set_selected_status_filter(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_site_filter(controller, site_filter: str) -> None:
    normalized = (site_filter or "").strip().lower() or "all"
    if normalized == controller._selected_site_filter.lower():
        return
    controller._set_selected_site_filter(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_department_filter(controller, department_filter: str) -> None:
    normalized = (department_filter or "").strip().lower() or "all"
    if normalized == controller._selected_department_filter.lower():
        return
    controller._set_selected_department_filter(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_manager_filter(controller, manager_filter: str) -> None:
    normalized = (manager_filter or "").strip().lower() or "all"
    if normalized == controller._selected_manager_filter.lower():
        return
    controller._set_selected_manager_filter(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_start_date_from(controller, value: str) -> None:
    normalized = (value or "").strip()
    if normalized == controller._start_date_from:
        return
    controller._set_start_date_from(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_start_date_to(controller, value: str) -> None:
    normalized = (value or "").strip()
    if normalized == controller._start_date_to:
        return
    controller._set_start_date_to(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_end_date_from(controller, value: str) -> None:
    normalized = (value or "").strip()
    if normalized == controller._end_date_from:
        return
    controller._set_end_date_from(normalized)
    controller._set_project_page(1)
    controller.refresh()


def set_end_date_to(controller, value: str) -> None:
    normalized = (value or "").strip()
    if normalized == controller._end_date_to:
        return
    controller._set_end_date_to(normalized)
    controller._set_project_page(1)
    controller.refresh()


def clear_filters(controller) -> None:
    if (
        not controller._search_text
        and controller._selected_status_filter == "all"
        and controller._selected_site_filter == "all"
        and controller._selected_department_filter == "all"
        and controller._selected_manager_filter == "all"
        and not controller._start_date_from
        and not controller._start_date_to
        and not controller._end_date_from
        and not controller._end_date_to
    ):
        return
    controller._set_search_text("")
    controller._set_selected_status_filter("all")
    controller._set_selected_site_filter("all")
    controller._set_selected_department_filter("all")
    controller._set_selected_manager_filter("all")
    controller._set_start_date_from("")
    controller._set_start_date_to("")
    controller._set_end_date_from("")
    controller._set_end_date_to("")
    controller._set_project_page(1)
    controller.refresh()


def set_project_page(controller, page: int) -> None:
    p = max(1, page)
    if p == controller._project_page:
        return
    controller._set_project_page(p)
    controller.refresh()


def set_project_page_size(controller, page_size: int) -> None:
    if page_size <= 0 or page_size == controller._project_page_size:
        return
    controller._set_project_page_size(page_size)
    controller._set_project_page(1)
    controller.refresh()


def set_project_sort(controller, sort_key: str, sort_direction: int) -> None:
    normalized_key = (sort_key or "").strip()
    if not normalized_key:
        return
    changed = (
        normalized_key != controller._project_sort_key
        or sort_direction != controller._project_sort_direction
    )
    if not changed:
        return
    controller._set_project_sort_key(normalized_key)
    controller._set_project_sort_direction(sort_direction)
    controller._set_project_page(1)
    controller.refresh()


def reset_project_lazy_sections(controller) -> None:
    controller._project_tasks_loaded_for_project_id = ""
    controller._project_resources_loaded_for_project_id = ""
    controller._project_risks_loaded_for_project_id = ""
    controller._project_activity_loaded_for_project_id = ""


__all__ = [
    "activate_project",
    "clear_filters",
    "reset_project_lazy_sections",
    "select_project",
    "set_end_date_from",
    "set_end_date_to",
    "set_department_filter",
    "set_manager_filter",
    "set_project_page",
    "set_project_page_size",
    "set_project_sort",
    "set_search_text",
    "set_site_filter",
    "set_start_date_from",
    "set_start_date_to",
    "set_status_filter",
]
