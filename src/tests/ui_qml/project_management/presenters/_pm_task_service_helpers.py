from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_hierarchy import (
    TaskWbsMoveCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
    TaskProgressCommand,
)
from src.core.modules.project_management.application.tasks.mappers.assignment import (
    map_assignment,
)
from src.core.modules.project_management.application.tasks.mappers.dependency import (
    map_dependency,
    map_dependency_read_item,
)
from src.core.modules.project_management.application.tasks.mappers.task import map_task
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskAssignmentReadItem,
    TaskAssignmentReadPage,
    TaskDependencyReadItem,
    TaskDependencyReadPage,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.master_data.documents import DocumentStorageKind
from src.tests.ui_qml.project_management.presenters._fake_task_workspace_query import (
    build_fake_task_workspace_page,
)
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)


def _collaboration_api(service):
    """Feed one fake (implementing every collaboration handler method) to each handler slot."""
    return build_project_management_collaboration_desktop_api(
        inbox_query=service,
        comment_query=service,
        document_query=service,
        presence_query=service,
        comment_commands=service,
        comment_engagement=service,
        presence_commands=service,
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

    def query_task_comments_page(self, task_id: str, *, page: int = 1, page_size: int = 25):
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_page,
        )
        return comment_page(self._comments, task_id, page=page, page_size=page_size)

    def list_comment_documents_for_ids(self, task_id: str, comment_ids: tuple[str, ...]) -> dict[str, list[SimpleNamespace]]:
        visible = {comment.id for comment in self._comments if comment.task_id == task_id}
        return {
            comment_id: list(documents)
            for comment_id, documents in self._comment_documents.items()
            if comment_id in visible and comment_id in comment_ids
        }

    def list_mention_candidates(self, task_id: str, *, query: str = "", limit: int = 50) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        options = [
            SimpleNamespace(handle="planner", label="@planner  Alex Taylor  Planner"),
            SimpleNamespace(handle="supervisor", label="@supervisor  Jordan Blake  Supervisor"),
        ]
        return [option for option in options if query.casefold() in option.label.casefold()][:limit]

    def search_available_documents(self, task_id: str, *, query: str = "", limit: int = 50) -> list[SimpleNamespace]:
        options = [
            SimpleNamespace(id="doc-1", document_code="PM-LINK-001", title="Shared Method Statement"),
            SimpleNamespace(id="doc-2", document_code="PM-LINK-002", title="Commissioning Checklist"),
        ]
        return [option for option in options if query.casefold() in f"{option.document_code} {option.title}".casefold()][:limit]

    def list_task_presence(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(
                task_id="task-1",
                task_name="Cable Pull",
                project_id="proj-1",
                project_name="Plant Upgrade",
                user_id="user-alex", username="planner",
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

    def post_comment(self, command):
        task_id, body = command.task_id, command.body
        attachments, linked_document_ids = command.attachments, command.linked_document_ids
        parent_comment_id = command.parent_comment_id
        task_id, body = command.task_id, command.body
        attachments, linked_document_ids = command.attachments, command.linked_document_ids
        parent_comment_id = command.parent_comment_id
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
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_response,
        )
        return comment_response(comment)

    def edit_comment(self, command) -> SimpleNamespace:
        comment_id, body, expected_revision = command.comment_id, command.body, command.expected_revision
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        assert expected_revision == comment.version
        comment.body = body
        comment.updated_at = datetime(2026, 5, 1, 11, 0)
        comment.version += 1
        self.edited_comment_ids.append(comment_id)
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_response,
        )
        return comment_response(comment)

    def delete_comment(self, command) -> SimpleNamespace:
        comment_id, expected_revision, reason = command.comment_id, command.expected_revision, command.reason
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        assert expected_revision == comment.version
        comment.deleted_at = datetime(2026, 5, 1, 11, 5)
        comment.deleted_by_user_id = "user-alex"
        comment.deletion_reason = reason
        comment.version += 1
        self.deleted_comment_ids.append(comment_id)
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_response,
        )
        return comment_response(comment)

    def react_to_comment(self, command) -> SimpleNamespace:
        comment_id, emoji = command.comment_id, command.emoji
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        reactions = dict(getattr(comment, "reactions", {}) or {})
        reactions[emoji] = ["user-alex"]
        comment.reactions = reactions
        comment.version += 1
        self.added_reactions.append((comment_id, emoji))
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_response,
        )
        return comment_response(comment)

    def remove_reaction(self, command) -> SimpleNamespace:
        comment_id, emoji = command.comment_id, command.emoji
        comment = next(comment for comment in self._comments if comment.id == comment_id)
        reactions = dict(getattr(comment, "reactions", {}) or {})
        reactions.pop(emoji, None)
        comment.reactions = reactions
        comment.version += 1
        self.removed_reactions.append((comment_id, emoji))
        from src.tests.ui_qml.project_management.presenters._collaboration_fixtures import (
            comment_response,
        )
        return comment_response(comment)


class _FakeTaskService:
    def query_task_responses(self, project_id):
        return tuple(map_task(task, project_name="") for task in self.list_tasks_for_project(project_id))

    def get_task_time_summary(self, task_id):
        return None

    def list_time_entries_for_task_page(self, task_id, **kwargs):
        return SimpleNamespace(items=(), total=0, page=kwargs.get("page", 1), page_size=kwargs.get("page_size", 25))

    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {task.id: task for task in (tasks or [])}
        self._assignments: dict[str, SimpleNamespace] = {}
        self._dependencies: dict[str, SimpleNamespace] = {}
        self._project_resource_lookup: dict[str, str] = {}
        self._resource_names: dict[str, str] = {}

    def _assignment_response(self, assignment, *, with_context=False):
        context_method = getattr(self, "get_assignment_action_context", None)
        context = context_method(assignment.id) if with_context and context_method is not None else None
        return map_assignment(
            assignment, resource_name=getattr(self, "_resource_names", {}).get(assignment.resource_id, assignment.resource_id),
            can_manage=bool(getattr(context, "can_manage", False)),
            can_accept=bool(getattr(context, "can_accept", False)),
            can_decline=bool(getattr(context, "can_decline", False)),
        )

    def query_assignment_responses(self, task_id):
        return tuple(self._assignment_response(row, with_context=True) for row in self.list_assignments_for_task(task_id))

    def query_dependency_responses(self, task_id):
        return tuple(map_dependency_read_item(edge, task_id=task_id, tasks_by_id=self._tasks)
                     for edge in self.list_dependencies_for_task(task_id))

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def query_workspace_page(self, **kwargs):
        return build_fake_task_workspace_page(self._tasks.values(), **kwargs)

    def get_task(self, task_id: str) -> SimpleNamespace | None:
        return self._tasks.get(task_id)

    def move_task(self, command: TaskWbsMoveCommand):
        task_id = command.task_id
        parent_task_id = command.parent_task_id
        wbs_code = command.wbs_code
        sort_order = command.sort_order
        expected_version = command.expected_version
        task = self._tasks[task_id]
        if expected_version is not None and task.version != expected_version:
            raise ValueError("Task version is stale.")
        task.parent_task_id = parent_task_id
        if wbs_code:
            task.wbs_code = wbs_code
        if sort_order is not None:
            task.sort_order = sort_order
        task.version += 1
        return map_task(task, project_name="")

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def set_tasks_status(self, command: TaskBulkStatusCommand):
        task_ids = command.task_ids
        status = TaskStatus(command.status)
        reopen_percent_complete = command.reopen_percent_complete
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
        return [map_task(task, project_name="") for task in changed]

    def update_progress(self, command: TaskProgressCommand):
        task_id = command.task_id
        percent_complete = command.percent_complete
        actual_start = command.actual_start
        actual_end = command.actual_end
        status = TaskStatus(command.status) if command.status is not None else None
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
        return map_task(task, project_name="")

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        deleted: list[str] = []
        for task_id in task_ids:
            if task_id in self._tasks:
                self.delete_task(task_id)
                deleted.append(task_id)
        return tuple(deleted)

    def register_project_resource(
        self,
        project_resource_id: str,
        resource_id: str,
        resource_name: str = "",
    ) -> None:
        self._project_resource_lookup[project_resource_id] = resource_id
        if resource_name:
            self._resource_names[resource_id] = resource_name

    def list_assignments_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def query_task_assignments_page(
        self,
        task_id: str,
        *,
        search_text: str = "",
        response_status: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> TaskAssignmentReadPage:
        rows = self.list_assignments_for_task(task_id)
        if response_status != "all":
            rows = [row for row in rows if row.response_status == response_status]
        if search_text:
            needle = search_text.casefold()
            rows = [row for row in rows if needle in str(row.resource_id).casefold()]
        rows.sort(key=lambda row: (str(row.resource_id).casefold(), str(row.id)))
        if sort_direction == "desc":
            rows.reverse()
        start = (page - 1) * page_size
        selected = rows[start : start + page_size]
        return TaskAssignmentReadPage(
            items=tuple(
                TaskAssignmentReadItem(
                    assignment_id=row.id,
                    resource_id=row.resource_id,
                    resource_code="",
                    resource_name=self._resource_names.get(row.resource_id, row.resource_id),
                    role="",
                    allocation_percent=Decimal(str(row.allocation_percent)),
                    planned_hours=Decimal(str(getattr(row, "allocated_planned_hours", 0))),
                    actual_hours=Decimal(str(row.hours_logged)),
                    response_status=row.response_status,
                    project_resource_id=row.project_resource_id,
                    version=int(getattr(row, "version", 1)),
                    can_manage=True,
                    can_accept=row.response_status == "pending",
                    can_decline=row.response_status == "pending",
                )
                for row in selected
            ),
            filtered_total=len(rows),
            page=page,
            page_size=page_size,
            sort=ReadSort.normalize(
                key=sort_key,
                direction=sort_direction,
                allowed_keys={
                    "resourceName", "resourceCode", "role", "allocationPercent",
                    "plannedHours", "actualHours", "remainingHours", "responseStatus",
                },
                default_key="resourceName",
            ),
        )

    def assign_project_resource(self, command: TaskAssignmentCreateCommand):
        task_id = command.task_id
        project_resource_id = command.project_resource_id
        allocation_percent = command.allocation_percent
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
        return self._assignment_response(assignment)

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
        return self._assignment_response(assignment)

    def decline_assignment(
        self,
        assignment_id: str,
        reason: str | None = None,
    ) -> SimpleNamespace:
        assignment = self._assignments[assignment_id]
        assignment.response_status = "declined"
        assignment.responded_at = datetime(2026, 5, 1, 12, 0)
        assignment.decline_reason = reason
        return self._assignment_response(assignment)

    def add_dependency(self, command: TaskDependencyCreateCommand):
        predecessor_id = command.linked_task_id if command.relationship_direction.upper() == "PREDECESSOR" else command.task_id
        successor_id = command.task_id if command.relationship_direction.upper() == "PREDECESSOR" else command.linked_task_id
        dependency_type = command.dependency_type
        lag_days = command.lag_days
        dependency = SimpleNamespace(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=DependencyType(str(dependency_type)),
            lag_days=lag_days,
        )
        self._dependencies[dependency.id] = dependency
        return map_dependency(dependency)

    def list_dependencies_for_task(self, task_id: str) -> list[SimpleNamespace]:
        return [
            d for d in self._dependencies.values()
            if d.predecessor_task_id == task_id or d.successor_task_id == task_id
        ]

    def query_task_dependencies_page(
        self,
        task_id: str,
        *,
        search_text: str = "",
        direction: str = "all",
        dependency_type: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "linkedTask",
        sort_direction: str = "asc",
    ) -> TaskDependencyReadPage:
        facts: list[TaskDependencyReadItem] = []
        for dependency in self.list_dependencies_for_task(task_id):
            is_predecessor = dependency.successor_task_id == task_id
            row_direction = "PREDECESSOR" if is_predecessor else "SUCCESSOR"
            linked_id = (
                dependency.predecessor_task_id
                if is_predecessor
                else dependency.successor_task_id
            )
            linked = self._tasks[linked_id]
            facts.append(
                TaskDependencyReadItem(
                    dependency_id=dependency.id,
                    direction=row_direction,
                    linked_task_id=linked.id,
                    linked_task_code=getattr(linked, "task_code", ""),
                    linked_task_name=linked.name,
                    linked_task_status=linked.status.value,
                    linked_task_start=linked.start_date,
                    linked_task_end=linked.end_date,
                    dependency_type=dependency.dependency_type.value,
                    lag_days=dependency.lag_days,
                    version=int(getattr(dependency, "version", 1)),
                )
            )
        predecessor_total = sum(row.direction == "PREDECESSOR" for row in facts)
        successor_total = sum(row.direction == "SUCCESSOR" for row in facts)
        if direction.upper() in {"PREDECESSOR", "SUCCESSOR"}:
            facts = [row for row in facts if row.direction == direction.upper()]
        if dependency_type.upper() in {"FS", "FF", "SS", "SF"}:
            facts = [row for row in facts if row.dependency_type == dependency_type.upper()]
        if search_text:
            needle = search_text.casefold()
            facts = [
                row for row in facts
                if needle in row.linked_task_name.casefold()
                or needle in row.linked_task_code.casefold()
            ]
        facts.sort(key=lambda row: (row.linked_task_name.casefold(), row.dependency_id))
        if sort_direction == "desc":
            facts.reverse()
        total = len(facts)
        start = (page - 1) * page_size
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "direction", "linkedTask", "taskCode", "dependencyType",
                "lagDays", "startDate", "endDate", "statusLabel",
            },
            default_key="linkedTask",
        )
        return TaskDependencyReadPage(
            items=tuple(facts[start : start + page_size]),
            filtered_total=total,
            predecessor_total=predecessor_total,
            successor_total=successor_total,
            page=page,
            page_size=page_size,
            sort=sort,
        )


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
    task_service.register_project_resource("pr-1", "res-1", "Alex Taylor")
    task_service.assign_project_resource(TaskAssignmentCreateCommand(
        task_id="task-1",
        project_resource_id="pr-1",
        allocation_percent=55.0,
    ))
    task_service.add_dependency(TaskDependencyCreateCommand(
        task_id="task-1",
        linked_task_id="task-2",
        dependency_type="FS",
        lag_days=2,
        relationship_direction="SUCCESSOR",
    ))
    tasks_api = build_project_management_tasks_desktop_api(
        project_service=SimpleNamespace(
            list_for_task_workspace=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_lookup_query=task_service, task_hierarchy_query=task_service, task_deletion_commands=task_service, task_progress_commands=task_service, task_hierarchy_commands=task_service, task_constraint_commands=task_service, task_lifecycle_commands=task_service, task_dependency_commands=task_service, task_dependency_query=task_service, task_assignment_commands=task_service,
        task_workspace_query=task_service,
        task_detail_query=task_service,
        task_time_entries=task_service,
        project_resource_query=SimpleNamespace(
            get=lambda _resource_id: None,
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
        resource_query=SimpleNamespace(
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
    collaboration_api = _collaboration_api(collaboration_service)
    timesheets_api = _FakeTaskTimesheetsDesktopApi()
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            platform_runtime=_FakePmRuntimeApi("org-1"),
            project_management_tasks=tasks_api,
            project_management_collaboration=collaboration_api,
            project_management_timesheets=timesheets_api,
        ),
    )
    return {
        "catalog": catalog,
        "controller": catalog.tasksWorkspace,
        'task_lookup_query': task_service, 'task_hierarchy_query': task_service, 'task_detail_query': task_service, 'task_assignment_commands': task_service, 'task_deletion_commands': task_service, 'task_progress_commands': task_service, 'task_hierarchy_commands': task_service, 'task_constraint_commands': task_service, 'task_lifecycle_commands': task_service, 'task_dependency_commands': task_service, 'task_dependency_query': task_service, 'task_leveling_commands': task_service,
        "collaboration_service": collaboration_service,
        "timesheets_api": timesheets_api,
    }
