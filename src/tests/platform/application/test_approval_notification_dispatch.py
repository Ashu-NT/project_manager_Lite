"""Team-collaboration notifications: approval requested/decided dispatch."""

from __future__ import annotations

from types import SimpleNamespace

from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.domain.approval import ApprovalRequest


class _FakeNotificationService:
    def __init__(self) -> None:
        self.dispatched: list[dict] = []

    def dispatch(self, **kwargs):
        self.dispatched.append(kwargs)
        return SimpleNamespace(id=f"notif-{len(self.dispatched)}")


class _FakeApprovalRepo:
    def list_notification_recipient_ids(self, request_id, *, audience, after_user_id, limit):
        if after_user_id:
            return ()
        return ("user-approver-1",) if audience == "reviewers" else ("user-requester",)


class _FakeTenantContextService:
    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    def get_active_tenant_id(self) -> str:
        return self._tenant_id


def _build_service(*, notification_service, tenant_id="tenant-1"):
    return ApprovalService(
        session=SimpleNamespace(),
        approval_repo=_FakeApprovalRepo(),
        # Notification methods don't touch the UnitOfWork factory; a never-called placeholder
        # is sufficient here.
        uow_factory=SimpleNamespace(),
        tenant_context_service=_FakeTenantContextService(tenant_id),
        notification_service=notification_service,
    )


def _make_request(**overrides) -> ApprovalRequest:
    defaults = dict(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id="baseline-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        organization_id="org-1",
        requested_by_user_id="user-requester",
        requested_by_username="alice",
    )
    defaults.update(overrides)
    return ApprovalRequest.create(**defaults)


def test_notify_approval_requested_fans_out_to_permission_holders_excluding_requester():
    notification_service = _FakeNotificationService()
    service = _build_service(notification_service=notification_service)
    request = _make_request()

    service._notify_approval_requested(request)

    recipients = {call["recipient_user_id"] for call in notification_service.dispatched}
    assert recipients == {"user-approver-1"}
    assert "user-requester" not in recipients
    assert all(
        call["category"] == "approval.requested.v1" for call in notification_service.dispatched
    )


def test_notify_approval_decided_notifies_requester_on_approval():
    notification_service = _FakeNotificationService()
    service = _build_service(notification_service=notification_service)
    request = _make_request()

    service._notify_approval_decided(request, decided="approved")

    assert len(notification_service.dispatched) == 1
    call = notification_service.dispatched[0]
    assert call["recipient_user_id"] == "user-requester"
    assert call["category"] == "approval.approved.v1"


def test_notify_approval_decided_notifies_requester_on_rejection_with_note():
    notification_service = _FakeNotificationService()
    service = _build_service(notification_service=notification_service)
    request = _make_request(payload={"foo": "bar"})
    request.decision_note = "Budget not available this quarter."

    service._notify_approval_decided(request, decided="rejected")

    assert len(notification_service.dispatched) == 1
    call = notification_service.dispatched[0]
    assert call["recipient_user_id"] == "user-requester"
    assert call["category"] == "approval.rejected.v1"
    assert "Budget not available this quarter." in call["body"]


def test_notify_approval_decided_noop_when_no_requester():
    notification_service = _FakeNotificationService()
    service = _build_service(notification_service=notification_service)
    request = _make_request(requested_by_user_id=None, requested_by_username=None)

    service._notify_approval_decided(request, decided="approved")

    assert notification_service.dispatched == []
