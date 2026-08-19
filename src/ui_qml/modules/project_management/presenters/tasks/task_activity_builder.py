from __future__ import annotations

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    build_activity_records,
    build_actor_lookup,
    fetch_entity_activity_entries,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
    TaskExecutionCollectionViewModel,
    TaskRecordViewModel,
)

from .overview_builder import build_empty_overview


def build_task_activity_state(
    activity_api: PlatformActivityDesktopApi | None,
    *,
    task_id: str,
    user_api: PlatformUserDesktopApi | None = None,
    employee_api: PlatformEmployeeDesktopApi | None = None,
) -> TaskCatalogWorkspaceViewModel:
    """Real audit trail for one task: its own lifecycle events
    (`task.create`/`task.update`/`task.delete`/`task.set_status`/
    `task.update_progress`/`task.wbs_move`) plus this task's assignment
    events (`task_assignment.*`, scoped via the real `parent_entity_id`
    column rather than `workspace_id`, which the owning project's other
    tasks also share).

    Task lifecycle commands don't record a field-level `changes` diff the
    way Projects' do (`_diff_project_fields`) -- entries here show actor,
    action, and timestamp without a diff-summary line. Adding that diff
    tracking is a natural follow-up, not required for this feed to be
    real and useful.
    """
    normalized_task_id = (task_id or "").strip()
    items: tuple[TaskRecordViewModel, ...] = ()
    if activity_api is not None and normalized_task_id:
        entries = fetch_entity_activity_entries(
            activity_api,
            entity_type="task",
            entity_id=normalized_task_id,
            child_specs=[("task_assignment", normalized_task_id)],
            limit=50,
        )
        if entries:
            actor_lookup = build_actor_lookup(
                user_api.list_users() if user_api is not None else DesktopApiResult(ok=False),
                employee_api.list_employees() if employee_api is not None else None,
            )
            items = build_activity_records(
                entries,
                record_factory=TaskRecordViewModel,
                actor_lookup=actor_lookup,
                field_labels={},
            )
    return TaskCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_task_id=normalized_task_id,
        task_activity=TaskExecutionCollectionViewModel(
            title="Activity",
            subtitle=f"{len(items)} recent event(s) for this task." if items else "Recent task activity.",
            empty_state="No activity has been recorded for this task yet.",
            items=items,
        ),
    )


__all__ = ["build_task_activity_state"]
