from datetime import datetime
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
)
from src.core.platform.api.desktop.approval.models.approval import ApprovalRequestDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.approval import ApprovalStatus
from src.core.platform.domain.master_data.documents import DocumentStorageKind
from src.ui_qml.modules.project_management.presenters.collaboration import (
    ProjectCollaborationWorkspacePresenter,
)


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

    @staticmethod
    def _inbox_rows() -> list[SimpleNamespace]:
        return [
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
        ]

    def query_mentions_page(
        self,
        *,
        project_id=None,
        author_username=None,
        search_text="",
        created_since=None,
        unread_only=False,
        page=1,
        page_size=25,
    ) -> SimpleNamespace:
        rows = self._inbox_rows()
        rows = [
            row
            for row in rows
            if (project_id is None or row.project_id == project_id)
            and (author_username is None or row.author_username == author_username)
            and (created_since is None or row.created_at >= created_since)
            and (not unread_only or row.unread)
            and (
                not search_text
                or search_text.casefold()
                in " ".join(
                    (row.task_name, row.project_name, row.author_username, row.body_preview)
                ).casefold()
            )
        ]
        offset = (page - 1) * page_size
        return SimpleNamespace(
            items=tuple(rows[offset : offset + page_size]),
            total=len(rows),
            page=page,
            page_size=page_size,
        )

    def query_inbox_page(self, **kwargs) -> SimpleNamespace:
        return self.query_mentions_page(**kwargs)

    def list_recent_activity(self, **kwargs) -> list[SimpleNamespace]:
        return [
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
        ]

    def list_active_presence(self) -> list[SimpleNamespace]:
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

    def list_workspace_context(self) -> SimpleNamespace:
        return SimpleNamespace(
            projects=(("proj-1", "Plant Upgrade"),),
            people=("jamie", "morgan"),
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

    def post_comment(self, *, task_id, body, attachments=(), linked_document_ids=(), parent_comment_id=None) -> SimpleNamespace:
        self.posted_comments.append(
            {"task_id": task_id, "body": body, "attachments": tuple(attachments), "linked_document_ids": tuple(linked_document_ids)}
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


def test_project_management_workspace_catalog_exposes_typed_collaboration_controller() -> None:
    collaboration_api = build_project_management_collaboration_desktop_api(
        collaboration_service=_FakeCollaborationService()
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_collaboration=collaboration_api
        )
    )

    controller = catalog.collaborationWorkspace

    assert controller.workspace["routeId"] == "project_management.collaboration"
    assert controller.overview["title"] == "Collaboration"
    assert controller.inbox["items"][0]["title"] == "Cable Pull"
    assert controller.mentions["totalCount"] == 1
    assert controller.overview["metrics"][3]["value"] == "1"

    result = controller.markTaskRead("task-1")

    assert result == {
        "ok": True,
        "message": "Task mentions marked as read.",
    }

    controller.setMentionsPageSize(1)
    controller.setMentionsSearchText("Cable")

    assert controller.mentions["page"] == 1
    assert controller.mentions["pageSize"] == 1
    assert controller.mentions["totalCount"] == 1


def test_collaboration_presenter_skips_null_approval_rows() -> None:
    class _FakeApprovalApi:
        def list_requests(self, *, status=None, project_id=None, limit: int = 200) -> DesktopApiResult[tuple[ApprovalRequestDto | None, ...]]:
            return DesktopApiResult(
                ok=True,
                data=(
                    ApprovalRequestDto(
                        id="approval-1",
                        request_type="purchase_order.submit",
                        entity_type="purchase_order",
                        entity_id="po-1",
                        project_id=None,
                        status=ApprovalStatus.PENDING,
                        requested_by_username="ashu",
                        requested_at=datetime(2026, 5, 1, 9, 0),
                        module_label="Inventory & Procurement",
                        context_label="PO INV-PO-001 | 1 line",
                        display_label="Submit purchase order INV-PO-001",
                    ),
                    None,
                ),
            )

    presenter = ProjectCollaborationWorkspacePresenter(
        desktop_api=build_project_management_collaboration_desktop_api(
            collaboration_service=_FakeCollaborationService()
        ),
        approval_api=_FakeApprovalApi(),
    )

    workspace = presenter.build_workspace_state()

    assert len(workspace.approvals.items) == 1
    assert workspace.approvals.items[0].id == "approval-1"
