from __future__ import annotations

from .pm_assignment_controller import PMAssignmentController
from .pm_collaboration_controller import PMCollaborationController
from .pm_dependency_controller import PMDependencyController
from .pm_task_list_controller import PMTaskListController
from .pm_time_controller import PMTimeController
from .task_facade_signal_binder import bind_task_facade_signals


def create_subcontrollers(controller) -> None:
    _cb = dict(
        presenter=controller._tasks_workspace_presenter,
        facade_refresh=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
        parent=controller,
    )
    controller._task_list = PMTaskListController(**_cb)
    controller._assignments_ctrl = PMAssignmentController(**_cb)
    controller._dependencies_ctrl = PMDependencyController(**_cb)
    controller._time_ctrl = PMTimeController(
        **_cb, refresh_time_entries=controller._refresh_time_entries_only
    )
    controller._collab_ctrl = PMCollaborationController(**_cb)
    bind_task_facade_signals(
        controller,
        controller._task_list,
        controller._assignments_ctrl,
        controller._dependencies_ctrl,
        controller._time_ctrl,
        controller._collab_ctrl,
    )


__all__ = ["create_subcontrollers"]
