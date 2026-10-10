"""Only supported business events stage safe, scoped notification work."""

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentChangeType,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
    TaskAssignmentChangeType,
)
from src.core.modules.project_management.infrastructure.composition.registrations.notifications import (
    register_pm_notification_policy,
)
from src.core.platform.domain.approval.events import ApprovalApproved, ApprovalRequested
from src.core.platform.domain.tenant.tenancy.events import TenantInvitationChanged
from src.core.platform.infrastructure.composition.events.notifications.approval_notifications import (
    register_platform_notification_policy,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.integration import notification_dispatcher

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


def test_shared_notification_runtime_does_not_import_pm_implementation():
    assert "modules.project_management" not in inspect.getsource(notification_dispatcher)


class _ApprovalRepo:
    def get(self, request_id):
        return SimpleNamespace(
            id=request_id, request_type="baseline.create", entity_type="project_baseline",
            requested_by_username="Alice",
        )

    def list_notification_recipient_ids(self, request_id, *, audience, after_user_id, limit):
        if after_user_id:
            return ()
        return ("reviewer-a", "reviewer-a", "reviewer-b") if audience == "reviewers" else ("requester",)


def _platform_dispatch(monkeypatch, event):
    writes = []
    monkeypatch.setattr(
        "src.core.platform.infrastructure.composition.events.notifications.approval_notifications.enqueue_notification_work",
        lambda session, **kwargs: writes.append(kwargs),
    )
    dispatcher = InProcessTransactionalEventDispatcher()
    register_platform_notification_policy(dispatcher)
    uow = SimpleNamespace(approvals=_ApprovalRepo(), _session=object())
    dispatcher.dispatch(event, uow)
    return writes


def test_requested_approval_stages_one_work_row_per_distinct_reviewer(monkeypatch):
    event = ApprovalRequested(
        approval_id="approval-1", tenant_id="tenant-1", organization_id="org-1",
        approval_type="baseline.create", entity_type="project_baseline",
        entity_id="baseline-1", requested_by_user_id="requester", occurred_at=NOW,
    )
    writes = _platform_dispatch(monkeypatch, event)
    assert {row["recipient_user_id"] for row in writes} == {"reviewer-a", "reviewer-b"}
    assert len(writes) == 2
    assert {row["source_event_id"] for row in writes} == {event.event_id}
    assert all(row["organization_id"] == "org-1" for row in writes)


def test_decided_approval_stages_only_requester_without_private_note(monkeypatch):
    event = ApprovalApproved(
        approval_id="approval-1", tenant_id="tenant-1", organization_id="org-1",
        approval_type="baseline.create", entity_type="project_baseline",
        entity_id="baseline-1", decided_by_user_id="reviewer-a", occurred_at=NOW,
    )
    writes = _platform_dispatch(monkeypatch, event)
    assert [row["recipient_user_id"] for row in writes] == ["requester"]
    assert writes[0]["category"] == "approval.approved.v1"


def test_invitation_does_not_stage_in_app_work(monkeypatch):
    event = TenantInvitationChanged(
        membership_id="member-1", tenant_id="tenant-1", recipient_user_id="invitee",
        change_type="issued", occurred_at=NOW,
    )
    writes = _platform_dispatch(monkeypatch, event)
    assert writes == []


def test_assignment_policy_requires_assigned_transition(monkeypatch):
    writes = []
    monkeypatch.setattr(
        "src.core.modules.project_management.infrastructure.composition.registrations.notifications.enqueue_notification_work",
        lambda session, **kwargs: writes.append(kwargs),
    )
    dispatcher = InProcessTransactionalEventDispatcher()
    register_pm_notification_policy(dispatcher)
    session = SimpleNamespace(scalar=lambda query: "assignee")
    for change_type in (TaskAssignmentChangeType.ASSIGNED, TaskAssignmentChangeType.UNASSIGNED):
        dispatcher.dispatch(TaskAssignmentChanged(
            tenant_id="tenant-1", organization_id="org-1", project_id="project-1",
            task_id="task-1", assignment_id="assignment-1", resource_id="resource-1",
            change_type=change_type, occurred_at=NOW,
        ), SimpleNamespace(_session=session))
    assert len(writes) == 1
    assert writes[0]["recipient_user_id"] == "assignee"
    assert writes[0]["metadata"]["task_id"] == "task-1"


def test_mention_policy_deduplicates_and_does_not_archive_comment_body(monkeypatch):
    writes = []
    monkeypatch.setattr(
        "src.core.modules.project_management.infrastructure.composition.registrations.notifications.enqueue_notification_work",
        lambda session, **kwargs: writes.append(kwargs),
    )
    dispatcher = InProcessTransactionalEventDispatcher()
    register_pm_notification_policy(dispatcher)
    comment = SimpleNamespace(
        task_id="task-1", deleted_at=None, author_user_id="author",
        mentioned_user_ids_json='["author", "mentioned", "mentioned"]',
        body="Secret private comment body",
    )
    recipient_queries = []

    def eligible_recipients(query):
        recipient_queries.append(query)
        return ("mentioned",)

    session = SimpleNamespace(get=lambda model, id: comment, scalars=eligible_recipients)
    dispatcher.dispatch(TaskCommentChanged(
        tenant_id="tenant-1", organization_id="org-1", project_id="project-1",
        task_id="task-1", comment_id="comment-1",
        change_type=TaskCommentChangeType.CREATED, occurred_at=NOW,
    ), SimpleNamespace(_session=session))
    assert len(writes) == 1
    assert len(recipient_queries) == 1
    assert writes[0]["recipient_user_id"] == "mentioned"
    assert "Secret private comment body" not in str(writes[0])
