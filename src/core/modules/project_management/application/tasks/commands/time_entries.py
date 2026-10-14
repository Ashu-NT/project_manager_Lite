from __future__ import annotations

from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskTimeEntriesPage,
    TaskTimeEntryRow,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.time_management.time import TimeEntryQueryHandler
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskTimeEntryHandler:
    def __init__(
        self,
        *,
        time_queries: TimeEntryQueryHandler | None,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        user_session: UserSessionContext | None,
    ) -> None:
        self._time_queries = time_queries
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._user_session = user_session

    def _require_time_queries(self) -> TimeEntryQueryHandler:
        queries = self._time_queries
        if queries is None:
            raise RuntimeError("Time query handler is not configured.")
        return queries

    def list_time_entries_for_task_page(
        self,
        task_id: str,
        *,
        resource_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_direction: str = "desc",
    ) -> TaskTimeEntriesPage:
        """Task-scoped (every TaskAssignment on this task, never just one) and
        all-time (not period-bound) Time Entries listing.

        Fetches the complete, authoritative entry set for this task's
        assignments in one batched repository call (`list_by_work_
        allocations`, a real SQL IN(...), never a per-assignment loop),
        then filters/sorts/paginates over that bounded, accurate dataset in
        this layer. This is deliberately NOT a dedicated SQL reader with
        pushed-down LIMIT/OFFSET (unlike the Timesheets Review Queue's
        `SqlAlchemyTimesheetReviewReader`) -- a single task's own logged
        time realistically stays small, so honest in-memory paging over
        the true total is proportionate here. If a task's entry volume
        ever grows large enough for that to stop holding, migrating to a
        dedicated reader is the natural next step.
        """
        require_permission(
            self._user_session, "task.read", operation_label="list task assignments"
        )
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="list task assignments",
        )
        assignments = self._assignment_repo.list_by_task(task_id)
        resource_by_assignment_id = {a.id: a.resource_id for a in assignments}
        assignment_ids = list(resource_by_assignment_id)
        entries = (
            self._require_time_queries().list_time_entries_for_work_allocations(
                assignment_ids
            )
            if assignment_ids
            else []
        )

        rows: list[TaskTimeEntryRow] = []
        for entry in entries:
            entry_resource_id = resource_by_assignment_id.get(entry.work_allocation_id, "")
            if resource_id and entry_resource_id != resource_id:
                continue
            if date_from is not None and entry.entry_date < date_from:
                continue
            if date_to is not None and entry.entry_date > date_to:
                continue
            rows.append(
                TaskTimeEntryRow(
                    entry_id=entry.id,
                    work_allocation_id=entry.work_allocation_id,
                    resource_id=entry_resource_id,
                    entry_date=entry.entry_date,
                    hours=entry.hours,
                    note=entry.note,
                    author_username=entry.author_username,
                    version=entry.version,
                )
            )

        reverse = sort_direction != "asc"
        rows.sort(key=lambda row: row.entry_date, reverse=reverse)

        total = len(rows)
        normalized_page = max(page, 1)
        start = (normalized_page - 1) * page_size
        page_items = tuple(rows[start : start + page_size])

        return TaskTimeEntriesPage(
            items=page_items,
            total=total,
            page=normalized_page,
            page_size=page_size,
        )


__all__ = ["TaskTimeEntryHandler"]
