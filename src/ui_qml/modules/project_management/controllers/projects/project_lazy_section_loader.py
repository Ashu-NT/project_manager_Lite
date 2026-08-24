from __future__ import annotations

from .project_serializers import serialize_project_section


def _section_state(controller, name: str) -> dict[str, object]:
    return dict(getattr(controller, f"_project_{name}", {}) or {})


def _page_state(title: str, page: dict[str, object]) -> dict[str, object]:
    return {"title": title, "subtitle": f"{int(page.get('total', 0))} matching record(s).",
            "emptyState": f"No {title.lower()} match the selected filters.", **page}


def load_project_tasks(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_tasks_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("tasks")
        state = _section_state(controller, "tasks")
        page = controller._projects_workspace_presenter.build_project_tasks_page(
            project_id=controller._selected_project_id,
            search_text=str(state.get("searchText", "")), status=str(state.get("status", "all")),
            schedule=str(state.get("schedule", "all")), page=int(state.get("page", 1)),
            page_size=int(state.get("pageSize", 25)), sort_key=str(state.get("sortKey", "wbsCode")),
            sort_direction=str(state.get("sortDirection", "asc")))
        controller._set_project_tasks(_page_state("Tasks", {**state, **page}))
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
        state = _section_state(controller, "resources")
        page = controller._projects_workspace_presenter.build_project_resources_page(
            project_id=controller._selected_project_id,
            search_text=str(state.get("searchText", "")), active=str(state.get("active", "all")),
            page=int(state.get("page", 1)), page_size=int(state.get("pageSize", 25)),
            sort_key=str(state.get("sortKey", "resourceName")),
            sort_direction=str(state.get("sortDirection", "asc")))
        controller._set_project_resources(_page_state("Resources", {**state, **page}))
        controller._project_resources_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("resources", str(exc))
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


def load_project_activity(controller) -> None:
    if not controller._selected_project_id:
        return
    if controller._project_activity_loaded_for_project_id == controller._selected_project_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("activity")
        state = _section_state(controller, "activity")
        page = controller._projects_workspace_presenter.build_project_activity_page(
            project_id=controller._selected_project_id,
            search_text=str(state.get("searchText", "")), category=str(state.get("category", "all")),
            page=int(state.get("page", 1)), page_size=int(state.get("pageSize", 25)))
        controller._set_project_activity(_page_state("Activity", {**state, **page}))
        controller._project_activity_loaded_for_project_id = controller._selected_project_id
    except Exception as exc:
        controller._set_section_error("activity", str(exc))
    finally:
        controller._set_is_loading(False)


def update_project_detail_query(controller, section: str, **changes) -> None:
    attr = f"_project_{section}"
    state = dict(getattr(controller, attr, {}) or {})
    state.update(changes)
    if any(key not in {"page", "pageSize"} for key in changes):
        state["page"] = 1
    getattr(controller, f"_set_project_{section}")(state)
    setattr(controller, f"_project_{section}_loaded_for_project_id", "")
    {"tasks": load_project_tasks, "resources": load_project_resources,
     "activity": load_project_activity}[section](controller)


__all__ = [
    "load_project_activity",
    "load_project_resources",
    "load_project_risks",
    "load_project_tasks",
    "update_project_detail_query",
]
