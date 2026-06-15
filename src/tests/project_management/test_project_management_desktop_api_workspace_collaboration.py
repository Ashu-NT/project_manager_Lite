from datetime import datetime
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_workspace_desktop_api,
)
from src.core.platform.documents import DocumentStorageKind


EXPECTED_PM_WORKSPACE_KEYS = [
    "projects",
    "tasks",
    "scheduling",
    "resources",
    "financials",
    "portfolio",
    "register",
    "collaboration",
    "timesheets",
    "dashboard",
]


def test_project_management_desktop_api_lists_workspace_descriptors() -> None:
    api = build_project_management_workspace_desktop_api()
    descriptors = api.list_workspaces()

    assert [descriptor.key for descriptor in descriptors] == EXPECTED_PM_WORKSPACE_KEYS
    assert descriptors[0].title == "Projects"
    assert descriptors[0].summary == (
        "Project lifecycle, ownership, status, and project list workflows."
    )


def test_project_management_desktop_api_gets_workspace_by_route_id() -> None:
    api = build_project_management_workspace_desktop_api()

    descriptor = api.get_workspace("project_management.dashboard")

    assert descriptor is not None
    assert descriptor.key == "dashboard"
    assert descriptor.title == "Dashboard"
    assert api.get_workspace("project_management.unknown") is None


def test_project_management_collaboration_desktop_api_builds_snapshot_and_marks_mentions_read() -> None:
    service = _FakeCollaborationService()
    api = build_project_management_collaboration_desktop_api(
        collaboration_service=service
    )

    snapshot = api.build_snapshot(limit=50)

    assert snapshot.notifications[0].notification_type_label == "Approval"
    assert snapshot.notifications[0].created_at_label == "2026-05-01 09:30"
    assert snapshot.inbox[0].mentions_label == "@planner"
    assert snapshot.recent_activity[0].unread is False
    assert snapshot.active_presence[0].who_label == "Alex Taylor (@planner)"
    assert snapshot.active_presence[0].activity_label == "Reviewing"

    api.mark_task_mentions_read("task-1")

    assert service.marked_task_ids == ["task-1"]

    task_snapshot = api.build_task_snapshot("task-1")

    assert task_snapshot.comments[0].author_username == "jamie"
    assert task_snapshot.comments[0].linked_documents_label == (
        "procedure.pdf [General | File], ticket-123 [General | Reference]"
    )
    assert task_snapshot.mention_options[0].value == "planner"
    assert task_snapshot.document_options[0].label == "PM-LINK-001 - Shared Method Statement"

    posted = api.post_task_comment(
        SimpleNamespace(
            task_id="task-1",
            body="Please review the linked checklist with @planner.",
            attachments=("handover.txt",),
            linked_document_ids=("doc-2",),
        )
    )

    assert posted.author_username == "alex"
    assert posted.attachments == ("handover.txt",)
    assert posted.linked_documents == ("Commissioning Checklist [General | Reference]",)
    assert service.posted_comments[-1]["task_id"] == "task-1"

    api.touch_task_presence("task-1", activity="editing")
    api.clear_task_presence("task-1")

    assert service.touched_presence == [("task-1", "editing")]
    assert service.cleared_presence == ["task-1"]


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
        assert limit == 50
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
