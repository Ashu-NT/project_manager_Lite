import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QSettings

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    ProjectFinancialsWorkspacePresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.api.desktop.runtime import build_desktop_api_registry
from src.api.desktop.platform import ApprovalRequestDto, ApprovalStatus, DesktopApiResult
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.documents import DocumentStorageKind
from src.tests.ui_runtime_helpers import wait_until
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
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


class _FakeEmployeeService:
    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        employees = [
            SimpleNamespace(
                id="emp-1",
                employee_code="EMP-001",
                full_name="Alex Taylor",
                title="Planner",
                department="Operations",
                site_name="Plant North",
                email="alex@example.com",
                phone="555-0100",
                is_active=True,
            ),
            SimpleNamespace(
                id="emp-2",
                employee_code="EMP-002",
                full_name="Jordan Blake",
                title="Supervisor",
                department="Maintenance",
                site_name="Plant South",
                email="jordan@example.com",
                phone="555-0101",
                is_active=False,
            ),
        ]
        if active_only is None:
            return employees
        return [
            employee
            for employee in employees
            if bool(employee.is_active) == bool(active_only)
        ]


class _FakeCollaborationService:
    def __init__(self) -> None:
        self.marked_task_ids: list[str] = []
        self.posted_comments: list[dict[str, object]] = []
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

    def list_workspace_snapshot(self, *, limit: int = 200) -> SimpleNamespace:
        assert limit == 200
        return SimpleNamespace(
            notifications=[
                SimpleNamespace(
                    notification_type="approval",
                    entity_type="approval_request",
                    entity_id="approval-1",
                    headline="Approval requested for Weekly Freeze",
                    body_preview="Baseline comparison needs governance review.",
                    actor_username="alex",
                    created_at=datetime(2026, 5, 1, 9, 30),
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    attention=True,
                )
            ],
            inbox=[
                SimpleNamespace(
                    comment_id="comment-1",
                    task_id="task-1",
                    task_name="Cable Pull",
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    author_username="jamie",
                    body_preview="Please review the updated execution window.",
                    mentions=["planner"],
                    created_at=datetime(2026, 5, 1, 8, 45),
                    unread=True,
                )
            ],
            recent_activity=[
                SimpleNamespace(
                    comment_id="comment-2",
                    task_id="task-2",
                    task_name="Commissioning Pack",
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    author_username="morgan",
                    body_preview="Draft punchlist is now linked for review.",
                    mentions=[],
                    created_at=datetime(2026, 5, 1, 8, 15),
                    unread=False,
                )
            ],
            active_presence=[
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
            ],
        )

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
            SimpleNamespace(
                id="doc-1",
                document_code="PM-LINK-001",
                title="Shared Method Statement",
            ),
            SimpleNamespace(
                id="doc-2",
                document_code="PM-LINK-002",
                title="Commissioning Checklist",
            ),
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

    def post_comment(
        self,
        *,
        task_id: str,
        body: str,
        attachments=(),
        linked_document_ids=(),
        parent_comment_id=None,
    ) -> SimpleNamespace:
        self.posted_comments.append(
            {
                "task_id": task_id,
                "body": body,
                "attachments": tuple(attachments),
                "linked_document_ids": tuple(linked_document_ids),
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


class _FakeResourceService:
    def __init__(self, resources: list[SimpleNamespace] | None = None) -> None:
        self._resources = {
            resource.id: resource
            for resource in (resources or [])
        }

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())


class _FakeRegisterService:
    def __init__(self, entries: list[SimpleNamespace] | None = None) -> None:
        self._entries = {
            entry.id: entry
            for entry in (entries or [])
        }

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[SimpleNamespace]:
        return [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]


def _build_register_record(
    *,
    entry_id: str,
    project_id: str,
    entry_type: RegisterEntryType,
    title: str,
    description: str,
    severity: RegisterEntrySeverity,
    status: RegisterEntryStatus,
    owner_name: str | None,
    due_date: date | None,
    impact_summary: str,
    response_plan: str,
    version: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entry_id,
        project_id=project_id,
        entry_type=entry_type,
        title=title,
        description=description,
        severity=severity,
        status=status,
        owner_name=owner_name,
        due_date=due_date,
        impact_summary=impact_summary,
        response_plan=response_plan,
        version=version,
    )
