from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_task_collection_view_model,
)


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
            resource_filter=controller._time_resource_filter,
            page=controller._time_page,
            selected_time_entry_id=controller._selected_time_entry_id or None,
        )
        controller._time_ctrl._update(ws)
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
        # "activity" (now the audit trail's own key) used to double as this
        # section's error key too, from when this was still labeled
        # "Activity" -- now "Discussion", so its own key follows.
        controller._clear_section_error("discussion")
        ws = controller._tasks_workspace_presenter.build_task_collaboration_state(
            task_id=controller._selected_task_id,
        )
        controller._collab_ctrl._update(ws)
        controller._set_collaboration_section_loaded_for_task_id(controller._selected_task_id)
    except Exception as exc:
        controller._set_section_error("discussion", str(exc))
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


def refresh_after_dependency_mutation(controller) -> None:
    """A dependency create/update/delete changes the CURRENTLY SELECTED
    task's own dates (via schedule recalculation) and the Dependencies/
    Schedule Impact sections' displayed facts -- but both sections are
    typically already active when the user makes the edit, and the lazy
    loaders above only re-fetch on a NEW tab activation (active:
    false->true), not on every property change. The generic
    _request_domain_refresh() this used to share with every other
    subcontroller only rebuilds the task LIST/workspace overview, never
    per-section detail state -- so without this, the edit is correct on
    the backend immediately, but the UI shows it only after the user
    leaves and re-enters Task Detail (which resets the loaded-for-task-id
    flags via reset_task_lazy_sections). This forces an immediate,
    targeted reload of exactly the state a dependency edit can affect.
    """
    if not controller._selected_task_id:
        return
    controller._dependencies_section_loaded_for_task_id = ""
    load_selected_task_dependencies(controller)
    controller._schedule_impact_section_loaded_for_task_id = ""
    load_selected_task_schedule_impact(controller)
    try:
        ws = controller._tasks_workspace_presenter.build_task_basic_detail_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
    except Exception:
        pass
    else:
        controller._task_list.updateSelectedTaskOnly(ws)


def load_selected_task_schedule_impact(controller) -> None:
    """Auto-loaded on section activation -- current-state facts only
    (one CPM pass, no hypothetical). The "Preview Impact" what-if is a
    separate, EXPLICIT action (see PMScheduleImpactController.previewImpact)
    never run automatically (§26)."""
    if not controller._selected_task_id:
        return
    if controller._schedule_impact_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("scheduleImpact")
        overview = controller._tasks_workspace_presenter.build_task_schedule_overview_state(
            task_id=controller._selected_task_id,
            project_id=controller._selected_project_id or None,
        )
        controller._set_schedule_impact(overview)
        controller._schedule_impact_section_loaded_for_task_id = controller._selected_task_id
    except Exception as exc:
        controller._set_section_error("scheduleImpact", str(exc))
    finally:
        controller._set_is_loading(False)


def load_selected_task_activity(controller) -> None:
    if not controller._selected_task_id:
        return
    if controller._task_activity_section_loaded_for_task_id == controller._selected_task_id:
        return
    controller._set_is_loading(True)
    try:
        controller._clear_section_error("activity")
        ws = controller._tasks_workspace_presenter.build_task_activity_state(
            task_id=controller._selected_task_id,
        )
        controller._set_task_activity(
            serialize_task_collection_view_model(ws.task_activity)
        )
        controller._task_activity_section_loaded_for_task_id = controller._selected_task_id
    except Exception as exc:
        controller._set_section_error("activity", str(exc))
    finally:
        controller._set_is_loading(False)


def refresh_time_entries_only(controller) -> None:
    """Rebuild only the task-scoped time summary + entries page after an
    entry-level mutation (docs §44 Time redesign) -- the fast path skips
    rebuilding assignment_options, since adding/editing/deleting a time
    entry never changes which assignments exist on this task."""
    if not controller._selected_task_id:
        return
    try:
        ws = controller._tasks_workspace_presenter.build_task_time_entries_refresh(
            task_id=controller._selected_task_id,
            resource_filter=controller._time_resource_filter,
            page=controller._time_page,
            selected_time_entry_id=controller._selected_time_entry_id or None,
        )
        if ws is not None:
            controller._time_ctrl._update_entries_only(ws)
            controller._set_selected_time_entry_id(ws.selected_time_entry_id)
    except Exception:  # noqa: BLE001 — scoped refresh failure must not mask user success
        pass


__all__ = [
    "load_selected_task_activity",
    "load_selected_task_assignments",
    "load_selected_task_collaboration",
    "load_selected_task_dependencies",
    "load_selected_task_schedule_impact",
    "load_selected_task_skill_requirements",
    "load_selected_task_time",
    "load_task_assignments_and_dependencies",
    "refresh_after_dependency_mutation",
    "refresh_time_entries_only",
]
