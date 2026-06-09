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
    controller._project_page = 1
    controller.refresh()


def set_status_filter(controller, status_filter: str) -> None:
    normalized = (status_filter or "").strip().lower() or "all"
    if normalized == controller._selected_status_filter.lower():
        return
    controller._set_selected_status_filter(normalized)
    controller._project_page = 1
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
    controller._project_page_size = page_size
    controller.projectPageSizeChanged.emit()
    controller._set_project_page(1)
    controller.refresh()


def reset_project_lazy_sections(controller) -> None:
    controller._project_tasks_loaded_for_project_id = ""
    controller._project_resources_loaded_for_project_id = ""
    controller._project_financials_loaded_for_project_id = ""
    controller._project_risks_loaded_for_project_id = ""
    controller._project_documents_loaded_for_project_id = ""
    controller._project_activity_loaded_for_project_id = ""


__all__ = [
    "activate_project",
    "reset_project_lazy_sections",
    "select_project",
    "set_project_page",
    "set_project_page_size",
    "set_search_text",
    "set_status_filter",
]
