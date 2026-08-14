from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.platform.domain.master_data.documents import DocumentStorageKind
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.tests.project_management._fake_task_workspace_query import (
    build_fake_task_workspace_page,
)


class _FakePmRuntimeApi:
    def __init__(self, organization_id: str | None = "org-1") -> None:
        self._organization_id = organization_id

    def get_runtime_context(self) -> DesktopApiResult[SimpleNamespace]:
        organization = (
            SimpleNamespace(id=self._organization_id)
            if self._organization_id is not None
            else None
        )
        return DesktopApiResult(
            ok=True,
            data=SimpleNamespace(active_organization=organization),
        )


class _FakeCollaborationService:
    def __init__(self) -> None:
        self.marked_task_ids: list[str] = []
        self.posted_comments: list[dict[str, object]] = []
        self.edited_comment_ids: list[str] = []
        self.deleted_comment_ids: list[str] = []
        self.added_reactions: list[tuple[str, str]] = []
        self.removed_reactions: list[tuple[str, str]] = []
        self.touched_presence: list[tuple[str, str]] = []
        self.cleared_presence: list[str] = []
        self._comments: list[SimpleNamespace] = [
            SimpleNamespace(
                id="comment-1",
                task_id="task-1",
                author_username="jamie",
                body="Please review the updated execution window.",
                mentions=["planner"],
                attachments=["handover.txt"],
                created_at=datetime(2026, 5, 1, 8, 45),
                version=1,
            )
        ]
        self._comment_documents: dict[str, list[SimpleNamespace]] = {
            "comment-1": [
                SimpleNamespace(
                    id="doc-1",
                    document_code="PM-ATT-001",
                    title="handover.txt",
                    document_type=SimpleNamespace(value="GENERAL"),
                    storage_kind=DocumentStorageKind.FILE_PATH,
                    storage_uri="handover.txt",
                    file_name="procedure.pdf",
                ),
                SimpleNamespace(
                    id="doc-ref-1",
                    document_code="PM-REF-001",
                    title="ticket-123",
                    document_type=SimpleNamespace(value="GENERAL"),
                    storage_kind=DocumentStorageKind.REFERENCE,
                    storage_uri="ticket-123",
                    file_name="",
                ),
            ]
        }

    def mark_task_mentions_read(self, task_id: str) -> None:
        self.marked_task_ids.append(task_id)

    def list_comments(self, task_id: str) -> list[SimpleNamespace]:
        return [comment for comment in self._comments if comment.task_id == task_id]

    def list_comment_documents(self, task_id: str) -> dict[str, list[SimpleNamespace]]:
        comment_ids = {comment.id for comment in self.list_comments(task_id)}
        return {
            comment_id: list(documents)
            for comment_id, documents in self._comment_documents.items()
            if comment_id in comment_ids
        }

    def list_mention_candidates(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(handle="planner", label="@planner  Alex Taylor  Planner"),
            SimpleNamespace(handle="supervisor", label="@supervisor  Jordan Blake  Supervisor"),
        ]

    def list_available_documents(self, *, active_only: bool = True) -> list[SimpleNamespace]:
        assert active_only is True
        return [
            SimpleNamespace(id="doc-1", document_code="PM-LINK-001", title="Shared Method Statement"),
            SimpleNamespace(id="doc-2", document_code="PM-LINK-002", title="Commissioning Checklist"),
        ]

    def list_task_presence(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(
                task_id="task-1",
                task_name="Cable Pull",
                project_id="proj-1",
                project_name="Plant Upgrade",
                username="planner",
                display_name="Alex Taylor",
                activity="reviewing",
                last_seen_at=datetime(2026, 5, 1, 9, 35),
                is_self=True,
            )
        ]

    def touch_task_presence(self, task_id: str, *, activity: str = "reviewing") -> None:
        self.touched_presence.append((task_id, activity))

    def clear_task_presence(self, task_id: str) -> None:
        self.cleared_presence.append(task_id)

    def get_task_comment_action_context(self, task_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            principal_user_id="user-alex",
            can_read=bool(task_id),
            can_manage=bool(task_id),
        )

    def post_comment(
        self, *, task_id: str, body: str, attachments=(), linked_document_ids=(), parent_comment_id=None
    ) -> SimpleNamespace:
        self.posted_comments.append(
            {
                "task_id": task_id,
                "body": body,
                "attachments": tuple(attachments),
                "linked_document_ids": tuple(linked_document_ids),
                "parent_comment_id": parent_comment_id,
            }
        )
        comment = SimpleNamespace(
            id="comment-posted-1",
            task_id=task_id,
            author_username="alex",
            body=body,
            mentions=["planner"],
            attachments=list(attachments),
            created_at=datetime(2026, 5, 1, 10, 15),
            version=1,
        )
        self._comments.append(comment)
        self._comment_documents[comment.id] = [
            SimpleNamespace(
                id="doc-2",
                document_code="PM-LINK-002",
                title="Commissioning Checklist",
                document_type=SimpleNamespace(value="GENERAL"),
                storage_kind=DocumentStorageKind.REFERENCE,
                storage_uri="ticket-456",
                file_name="",
            )
        ]
        return comment

    def edit_comment(
        self,
        comment_id: str,
        body: str,
        *,
        expected_revision: int | None = None,
    ) -> SimpleNamespace:
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        assert expected_revision == comment.version
        comment.body = body
        comment.updated_at = datetime(2026, 5, 1, 11, 0)
        comment.version += 1
        self.edited_comment_ids.append(comment_id)
        return comment

    def delete_comment(
        self,
        comment_id: str,
        *,
        expected_revision: int | None = None,
        reason: str | None = None,
    ) -> SimpleNamespace:
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        assert expected_revision == comment.version
        comment.deleted_at = datetime(2026, 5, 1, 11, 5)
        comment.deleted_by_user_id = "user-alex"
        comment.deletion_reason = reason
        comment.version += 1
        self.deleted_comment_ids.append(comment_id)
        return comment

    def react_to_comment(self, comment_id: str, emoji: str) -> SimpleNamespace:
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        reactions = dict(getattr(comment, "reactions", {}) or {})
        reactions[emoji] = ["user-alex"]
        comment.reactions = reactions
        comment.version += 1
        self.added_reactions.append((comment_id, emoji))
        return comment

    def remove_reaction(self, comment_id: str, emoji: str) -> SimpleNamespace:
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        reactions = dict(getattr(comment, "reactions", {}) or {})
        reactions.pop(emoji, None)
        comment.reactions = reactions
        comment.version += 1
        self.removed_reactions.append((comment_id, emoji))
        return comment


class _FakeTaskService:
    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {task.id: task for task in (tasks or [])}
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def query_workspace_page(self, **kwargs):
        return build_fake_task_workspace_page(self._tasks.values(), **kwargs)

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def move_task(
        self,
        task_id: str,
        *,
        parent_task_id: str | None,
        wbs_code: str | None = None,
        sort_order: int | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
        task = self._tasks[task_id]
        if expected_version is not None and task.version != expected_version:
            raise ValueError("Task version is stale.")
        task.parent_task_id = parent_task_id
        if wbs_code:
            task.wbs_code = wbs_code
        if sort_order is not None:
            task.sort_order = sort_order
        task.version += 1
        return task

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def set_tasks_status(
        self,
        task_ids: tuple[str, ...],
        status: TaskStatus,
        *,
        reopen_percent_complete: float | None = None,
    ) -> list[SimpleNamespace]:
        changed: list[SimpleNamespace] = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status == status:
                continue
            if reopen_percent_complete is not None and status == TaskStatus.IN_PROGRESS:
                task.percent_complete = reopen_percent_complete
            self.set_status(task_id, status)
            changed.append(task)
        return changed

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = float(percent_complete)
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        deleted: list[str] = []
        for task_id in task_ids:
            if task_id in self._tasks:
                self.delete_task(task_id)
                deleted.append(task_id)
        return tuple(deleted)

    def register_project_resource(self, project_resource_id: str, resource_id: str) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def assign_project_resource(
        self,
        *,
        task_id: str,
        project_resource_id: str,
        allocation_percent: float,
    ) -> SimpleNamespace:
        assignment = SimpleNamespace(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=self._project_resource_lookup.get(project_resource_id, project_resource_id),
            allocation_percent=allocation_percent,
            hours_logged=0.0,
            project_resource_id=project_resource_id,
            response_status="pending",
            responded_at=None,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def get_assignment_action_context(self, assignment_id: str) -> SimpleNamespace:
        assignment = self._assignments[assignment_id]
        can_respond = assignment.response_status == "pending"
        return SimpleNamespace(
            can_manage=True,
            can_accept=can_respond,
            can_decline=can_respond,
        )

    def accept_assignment(self, assignment_id: str) -> SimpleNamespace:
        assignment = self._assignments[assignment_id]
        assignment.response_status = "accepted"
        assignment.responded_at = datetime(2026, 5, 1, 12, 0)
        return assignment

    def decline_assignment(
        self,
        assignment_id: str,
        reason: str | None = None,
    ) -> SimpleNamespace:
        assignment = self._assignments[assignment_id]
        assignment.response_status = "declined"
        assignment.responded_at = datetime(2026, 5, 1, 12, 0)
        assignment.decline_reason = reason
        return assignment

    def add_dependency(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: str,
        lag_days: int = 0,
    ) -> SimpleNamespace:
        dependency = SimpleNamespace(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=DependencyType(str(dependency_type)),
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return dependency

    def list_dependencies_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            d for d in self._dependencies.values()
            if d.predecessor_task_id == task_id or d.successor_task_id == task_id
        ]


def _build_task_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    status: TaskStatus,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    priority: int,
    percent_complete: float,
    deadline: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id=project_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        priority=priority,
        percent_complete=percent_complete,
        actual_start=None,
        actual_end=None,
        deadline=deadline,
        version=1,
    )


class _FakeTaskTimesheetsDesktopApi:
    def __init__(self) -> None:
        self.added_entries: list[dict[str, object]] = []

    def build_assignment_snapshot(self, assignment_id, *, period_start=None):
        assert assignment_id == "assign-1"
        selected_period_start = period_start.isoformat() if period_start is not None else "2026-05-01"
        entry_rows = [
            SimpleNamespace(
                entry_id="entry-1",
                entry_date_label="2026-05-03",
                hours=6.0,
                hours_label="6.00h",
                note="Cable tray installation",
                author_username="alex",
            ),
            *[
                SimpleNamespace(
                    entry_id=row["entry_id"],
                    entry_date_label=row["entry_date"],
                    hours=row["hours"],
                    hours_label=f"{float(row['hours']):.2f}h",
                    note=row["note"],
                    author_username="alex",
                )
                for row in self.added_entries
            ],
        ]
        total_hours = sum(float(entry.hours or 0.0) for entry in entry_rows)
        return SimpleNamespace(
            assignment=SimpleNamespace(
                value="assign-1",
                label="Plant Upgrade | Cable Pull | Alex Taylor",
                project_id="proj-1",
            ),
            period_options=(
                SimpleNamespace(value="2026-05-01", label="May 2026"),
                SimpleNamespace(value="2026-04-01", label="Apr 2026"),
            ),
            selected_period_start=selected_period_start,
            period_summary=SimpleNamespace(
                period_id="period-1",
                period_start_label="May 2026",
                period_end_label="2026-05-31",
                status="OPEN",
                status_label="Open",
                resource_id="res-1",
                resource_name="Alex Taylor",
                total_hours_label=f"{total_hours:.2f}h",
                entry_count=len(entry_rows),
                submitted_by_username="-",
                submitted_at_label="-",
                decided_by_username="-",
                decided_at_label="-",
                decision_note="",
            ),
            entries=tuple(entry_rows),
            resource_period_total_hours_label=f"{total_hours:.2f}h",
            scope_summary=(
                f"Task period entries: {len(entry_rows)} | "
                f"Resource month total: {total_hours:.2f}h"
            ),
        )

    def add_time_entry(self, command):
        entry_id = f"entry-{len(self.added_entries) + 2}"
        self.added_entries.append(
            {
                "entry_id": entry_id,
                "entry_date": command.entry_date.isoformat(),
                "hours": float(command.hours),
                "note": command.note or "",
            }
        )
        return SimpleNamespace(id=entry_id)

    def update_time_entry(self, command):
        for row in self.added_entries:
            if row["entry_id"] == command.entry_id:
                row["entry_date"] = command.entry_date.isoformat()
                row["hours"] = float(command.hours)
                row["note"] = command.note or ""
                return SimpleNamespace(id=command.entry_id)
        return SimpleNamespace(id=command.entry_id)

    def delete_time_entry(self, entry_id):
        self.added_entries = [row for row in self.added_entries if row["entry_id"] != entry_id]

    def submit_period(self, *, resource_id, period_start, note=""):
        return SimpleNamespace(resource_id=resource_id, period_start=period_start, note=note)

    def lock_period(self, *, resource_id, period_start, note=""):
        return SimpleNamespace(resource_id=resource_id, period_start=period_start, note=note)

    def unlock_period(self, period_id, *, note=""):
        return SimpleNamespace(period_id=period_id, note=note)


def build_task_controller_bundle(tmp_path: Path) -> dict:
    task_service = _FakeTaskService(
        [
            _build_task_record(
                task_id="task-1", project_id="proj-1", name="Cable Pull",
                description="Primary feeder cable installation.", status=TaskStatus.IN_PROGRESS,
                start_date=date(2026, 5, 3), end_date=date(2026, 5, 6), duration_days=4,
                priority=70, percent_complete=45.0, deadline=date(2026, 5, 7),
            ),
            _build_task_record(
                task_id="task-2", project_id="proj-1", name="Punchlist Closeout",
                description="Commissioning closeout walkdown.", status=TaskStatus.BLOCKED,
                start_date=date(2026, 5, 8), end_date=date(2026, 5, 9), duration_days=2,
                priority=95, percent_complete=0.0, deadline=date(2026, 5, 9),
            ),
            _build_task_record(
                task_id="task-3", project_id="proj-2", name="Lighting Retrofit",
                description="Warehouse fixture replacement.", status=TaskStatus.TODO,
                start_date=date(2026, 5, 10), end_date=date(2026, 5, 12), duration_days=3,
                priority=40, percent_complete=0.0, deadline=date(2026, 5, 13),
            ),
            _build_task_record(
                task_id="task-4", project_id="proj-1", name="As-Built Handover",
                description="Finalize turnover package and as-built dossier.", status=TaskStatus.DONE,
                start_date=date(2026, 5, 10), end_date=date(2026, 5, 10), duration_days=1,
                priority=50, percent_complete=100.0, deadline=date(2026, 5, 10),
            ),
        ]
    )
    task_service.register_project_resource("pr-1", "res-1")
    task_service.assign_project_resource(
        task_id="task-1",
        project_resource_id="pr-1",
        allocation_percent=55.0,
    )
    task_service.add_dependency(
        predecessor_id="task-1",
        successor_id="task-2",
        dependency_type="FS",
        lag_days=2,
    )
    tasks_api = build_project_management_tasks_desktop_api(
        project_service=SimpleNamespace(
            list_for_task_workspace=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_service=task_service,
        project_resource_service=SimpleNamespace(
            list_for_task_workspace=lambda project_id: [
                SimpleNamespace(
                    id="pr-1",
                    project_id="proj-1",
                    resource_id="res-1",
                    hourly_rate=90.0,
                    currency_code="EUR",
                    is_active=True,
                )
            ]
            if project_id == "proj-1"
            else []
        ),
        resource_service=SimpleNamespace(
            list_for_task_workspace=lambda **_kwargs: [
                SimpleNamespace(
                    id="res-1",
                    name="Alex Taylor",
                    is_active=True,
                    hourly_rate=85.0,
                    currency_code="EUR",
                )
            ]
        ),
    )
    collaboration_service = _FakeCollaborationService()
    collaboration_api = build_project_management_collaboration_desktop_api(
        collaboration_service=collaboration_service
    )
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    settings = QSettings(str(tmp_path / "pm-task-views.ini"), QSettings.IniFormat)
    settings.clear()
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            platform_runtime=_FakePmRuntimeApi("org-1"),
            project_management_tasks=tasks_api,
            project_management_collaboration=collaboration_api,
            project_management_timesheets=timesheets_api,
        ),
        task_view_store=ProjectManagementTaskViewStore(settings),
    )
    return {
        "controller": catalog.tasksWorkspace,
        "task_service": task_service,
        "collaboration_service": collaboration_service,
        "timesheets_api": timesheets_api,
        "settings": settings,
    }
