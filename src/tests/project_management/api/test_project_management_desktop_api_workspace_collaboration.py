from datetime import datetime
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_workspace_desktop_api,
)
from src.core.platform.domain.master_data.documents import DocumentStorageKind

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
    "review_queue",
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
    assert descriptor.title == "Overview"
    assert api.get_workspace("project_management.unknown") is None


def test_project_management_collaboration_desktop_api_exposes_purpose_queries() -> None:
    service = _FakeCollaborationService()
    api = build_project_management_collaboration_desktop_api(
        collaboration_service=service
    )

    inbox = api.query_inbox_page(page=1, page_size=25)
    activity = api.list_recent_activity(limit=50)
    presence = api.list_active_presence()
    context = api.list_context_options()

    assert inbox.total == 1
    assert inbox.items[0].mentions_label == "@planner"
    assert activity[0].unread is False
    assert presence[0].who_label == "Alex Taylor (@planner)"
    assert presence[0].activity_label == "Reviewing"
    assert context.projects == (("proj-1", "Plant Upgrade"),)

    api.mark_task_mentions_read("task-1")

    assert service.marked_task_ids == ["task-1"]

    task_snapshot = api.build_task_snapshot("task-1")

    assert task_snapshot.comments[1].author_username == "jamie"
    assert task_snapshot.comments[1].linked_documents_label == (
        "procedure.pdf [General | File], ticket-123 [General | Reference]"
    )
    assert [comment.comment_id for comment in task_snapshot.comments] == [
        "comment-reply-1",
        "comment-1",
    ]
    assert task_snapshot.comments[1].reply_count == 1
    assert task_snapshot.comments[1].can_edit is True
    assert task_snapshot.comments[1].reactions[0].reacted_by_current_user is True
    assert task_snapshot.comments[0].thread_depth == 1
    assert task_snapshot.comments[0].parent_author_username == "jamie"
    assert task_snapshot.comments[0].can_edit is False
    assert task_snapshot.comment_total == 2
    assert task_snapshot.mention_options[0].value == "everyone"
    assert task_snapshot.mention_options[1].value == "planner"
    assert [option.value for option in api.search_task_mention_options("task-1", "plan")] == [
        "everyone", "planner"
    ]
    assert task_snapshot.document_options[0].label == "PM-LINK-001 - Shared Method Statement"
    assert [option.value for option in api.search_task_document_options("task-1", "check")] == [
        "doc-2"
    ]

    posted = api.post_task_comment(
        SimpleNamespace(
            task_id="task-1",
            body="Please review the linked checklist with @planner.",
            attachments=("handover.txt",),
            linked_document_ids=("doc-2",),
            submission_id="desktop-post-1",
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
                author_user_id="user-alex",
                author_username="jamie",
                body="Please review the updated execution window.",
                mentions=["planner"],
                attachments=["handover.txt"],
                created_at=datetime(2026, 5, 1, 8, 45),
                parent_comment_id=None,
                reactions={"\N{THUMBS UP SIGN}": ["user-alex"]},
                parent_author_username="",
                reply_count=1,
            ),
            SimpleNamespace(
                id="comment-reply-1",
                task_id="task-1",
                author_user_id="user-jordan",
                author_username="jordan",
                body="The revised window works for operations.",
                mentions=[],
                attachments=[],
                created_at=datetime(2026, 5, 1, 9, 15),
                parent_comment_id="comment-1",
                reactions={},
                parent_author_username="jamie",
                reply_count=0,
            ),
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

    def query_inbox_page(self, **kwargs) -> SimpleNamespace:
        item = SimpleNamespace(
            comment_id="comment-1",
            task_id="task-1",
            task_name="Cable Pull",
            project_id="proj-1",
            project_name="Plant Upgrade",
            author_username="jamie",
            body_preview="Please review the updated execution window.",
            is_deleted=False,
            deleted_at=None,
            mentions=["planner"],
            created_at=datetime(2026, 5, 1, 8, 45),
            unread=True,
        )
        return SimpleNamespace(items=(item,), total=1, page=1, page_size=25)

    def query_mentions_page(self, **kwargs) -> SimpleNamespace:
        return self.query_inbox_page(**kwargs)

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
                is_deleted=False,
                deleted_at=None,
                mentions=[],
                created_at=datetime(2026, 5, 1, 8, 15),
                unread=False,
            )
        ]

    def list_active_presence(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                task_id="task-1",
                user_id="user-alex",
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
            people=("jamie", "planner"),
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        self.marked_task_ids.append(task_id)

    def query_task_comments_page(
        self, task_id: str, *, page: int = 1, page_size: int = 25
    ) -> SimpleNamespace:
        comments = sorted(
            (comment for comment in self._comments if comment.task_id == task_id),
            key=lambda comment: (comment.created_at, comment.id),
            reverse=True,
        )
        start = (page - 1) * page_size
        return SimpleNamespace(
            items=tuple(comments[start : start + page_size]),
            total=len(comments),
            page=page,
            page_size=page_size,
        )

    def list_comment_documents_for_ids(
        self, task_id: str, comment_ids: tuple[str, ...]
    ) -> dict[str, list[SimpleNamespace]]:
        valid_ids = {comment.id for comment in self._comments if comment.task_id == task_id}
        return {
            comment_id: list(documents)
            for comment_id, documents in self._comment_documents.items()
            if comment_id in comment_ids and comment_id in valid_ids
        }

    def list_mention_candidates(
        self, task_id: str, *, query: str = "", limit: int = 50
    ) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        candidates = [
            SimpleNamespace(handle="planner", label="@planner  Alex Taylor  Planner"),
            SimpleNamespace(handle="supervisor", label="@supervisor  Jordan Blake  Supervisor"),
        ]
        return [item for item in candidates if query.lower() in item.handle][:limit]

    def search_available_documents(
        self, task_id: str, *, query: str = "", limit: int = 50
    ) -> tuple[SimpleNamespace, ...]:
        assert task_id == "task-1"
        documents = [
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
        return tuple(
            item for item in documents
            if query.lower() in item.title.lower() or query.lower() in item.document_code.lower()
        )[:limit]

    def list_task_presence(self, task_id: str) -> list[SimpleNamespace]:
        if task_id != "task-1":
            return []
        return [
            SimpleNamespace(
                task_id="task-1",
                user_id="user-alex",
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
        self,
        *,
        task_id: str,
        body: str,
        attachments=(),
        linked_document_ids=(),
        parent_comment_id=None,
        submission_id=None,
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
            parent_comment_id=parent_comment_id,
            parent_author_username="",
            reply_count=0,
            reactions={},
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
