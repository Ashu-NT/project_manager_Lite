from __future__ import annotations

from .project_serializers import serialize_project_section


def load_project_tasks(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_tasks_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("tasks")
        ws = controller._projects_workspace_presenter.build_project_tasks_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_tasks(serialize_project_section(ws.project_tasks))
        controller._project_tasks_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("tasks", str(exc))
    finally:
        controller._set_is_loading(False)


def load_project_resources(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_resources_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("resources")
        ws = controller._projects_workspace_presenter.build_project_resources_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_resources(serialize_project_section(ws.project_resources))
        controller._project_resources_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("resources", str(exc))
    finally:
        controller._set_is_loading(False)


def load_project_financials(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_financials_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("financials")
        ws = controller._projects_workspace_presenter.build_project_financials_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_financials(serialize_project_section(ws.project_financials))
        controller._project_financials_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("financials", str(exc))
    finally:
        controller._set_is_loading(False)


def load_project_risks(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_risks_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("risks")
        ws = controller._projects_workspace_presenter.build_project_risks_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_risks(serialize_project_section(ws.project_risks))
        controller._project_risks_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("risks", str(exc))
    finally:
        controller._set_is_loading(False)


def load_project_documents(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_documents_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("documents")
        ws = controller._projects_workspace_presenter.build_project_documents_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_documents(serialize_project_section(ws.project_documents))
        controller._project_documents_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("documents", str(exc))
    finally:
        controller._set_is_loading(False)


def load_project_activity(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_activity_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("activity")
        ws = controller._projects_workspace_presenter.build_project_activity_state(
            project_id=controller._selected_project_id
        )
        controller._set_project_activity(serialize_project_section(ws.project_activity))
        controller._project_activity_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("activity", str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = [
    "load_project_activity",
    "load_project_documents",
    "load_project_financials",
    "load_project_resources",
    "load_project_risks",
    "load_project_tasks",
]
