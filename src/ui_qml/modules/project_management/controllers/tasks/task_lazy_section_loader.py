from __future__ import annotations


def load_task_assignments_and_dependencies(controller) -> None:
    load_selected_task_assignments(controller)
    load_selected_task_dependencies(controller)


def load_selected_task_assignments(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller._assignments_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("assignments")
        ws = controller._tasks_workspace_presenter.build_task_assignments_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
        controller._assignments_ctrl._update(ws)
        controller._assignments_section_loaded_for_task_id = controller._selected_task_id
        if not controller._selected_assignment_id:
            assignment_items = getattr(ws.assignments, "items", ()) or ()
            if assignment_items:
                first = assignment_items[0]
                controller._set_selected_assignment_id(str(getattr(first, "id", "") or ""))
    except Exception as exc:
        controller._set_section_error("assignments", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_dependencies(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller._dependencies_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("dependencies")
        ws = controller._tasks_workspace_presenter.build_task_dependencies_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
        controller._dependencies_ctrl._update(ws)
        controller._dependencies_section_loaded_for_task_id = controller._selected_task_id
    except Exception as exc:
        controller._set_section_error("dependencies", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_time(controller) -> None:
    if not controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("time")
        ws = controller._tasks_workspace_presenter.build_task_time_state(
            task_id=controller._selected_task_id,
            selected_assignment_id=controller._selected_assignment_id or None,
            selected_time_period_start=controller._selected_time_period_start,
            selected_time_entry_id=controller._selected_time_entry_id or None,
        )
        controller._time_ctrl._update(ws)
        controller._set_selected_assignment_id(ws.selected_assignment_id)
        controller._set_selected_time_period_start(ws.selected_time_period_start)
        controller._set_selected_time_entry_id(ws.selected_time_entry_id)
        controller._set_time_section_loaded_for_task_id(controller._selected_task_id)
    except Exception as exc:
        controller._set_section_error("time", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_collaboration(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller.isCollaborationSectionLoaded:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("activity")
        ws = controller._tasks_workspace_presenter.build_task_collaboration_state(
            task_id=controller._selected_task_id,
        )
        controller._collab_ctrl._update(ws)
        controller._set_collaboration_section_loaded_for_task_id(controller._selected_task_id)
    except Exception as exc:
        controller._set_section_error("activity", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_skill_requirements(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller._skill_requirements_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("skills")
        ws = controller._tasks_workspace_presenter.build_task_skill_requirements_state(
            task_id=controller._selected_task_id,
        )
        controller._assignments_ctrl._update_skill_requirements(ws)
        controller._skill_requirements_section_loaded_for_task_id = controller._selected_task_id
    except Exception as exc:
        controller._set_section_error("skills", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_schedule_impact(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller._schedule_impact_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("scheduleImpact")
        impact = controller._tasks_workspace_presenter.build_task_schedule_impact_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
        controller._set_schedule_impact(impact)
        controller._schedule_impact_section_loaded_for_task_id = controller._selected_task_id
    except Exception as exc:
        controller._set_section_error("scheduleImpact", str(exc))
    finally:
        controller._set_is_loading(False)


def refresh_time_entries_only(controller) -> None:
    """Rebuild only the time-entries section after an entry-level mutation.

    Uses the fast path (build_task_time_entries_refresh) which skips
    list_assignments() and directly rebuilds from the known assignment snapshot.
    Period-level mutations (submit/lock/unlock) still call _request_domain_refresh.
    """
    try:
        ws = controller._tasks_workspace_presenter.build_task_time_entries_refresh(
            assignment_id=controller._selected_assignment_id or None,
            period_start=controller._selected_time_period_start,
            selected_time_entry_id=controller._selected_time_entry_id or None,
        )
        if ws is not None:
            controller._time_ctrl._update_entries_only(ws)
    except Exception:  # noqa: BLE001 — scoped refresh failure must not mask user success
        pass


__all__ = [
    "load_selected_task_assignments",
    "load_selected_task_collaboration",
    "load_selected_task_dependencies",
    "load_selected_task_schedule_impact",
    "load_selected_task_skill_requirements",
    "load_selected_task_time",
    "load_task_assignments_and_dependencies",
    "refresh_time_entries_only",
]
