"""Phase 1 team-collaboration notifications: approval requested/decided dispatch."""

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


class _FakePermissionRepo:
    def __init__(self, permissions: dict[str, str]) -> None:
        # code -> permission_id
        self._by_code = permissions

    def get_by_code(self, code: str):
        permission_id = self._by_code.get(code)
        if permission_id is None:
            return None
        return SimpleNamespace(id=permission_id, code=code)


class _FakeRoleRepo:
    def __init__(self, roles: list[object]) -> None:
        self._roles = roles

    def list_all(self):
        return list(self._roles)


class _FakeRolePermissionRepo:
    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self._mapping = mapping  # role_id -> [permission_id, ...]

    def list_permission_ids(self, role_id: str) -> list[str]:
        return list(self._mapping.get(role_id, []))


class _FakeRoleBindingRepo:
    def __init__(
        self,
        *,
        across_tenants: dict[str, list[object]] | None = None,
        for_tenant: dict[tuple[str, str], list[object]] | None = None,
    ) -> None:
        self._across_tenants = across_tenants or {}
        self._for_tenant = for_tenant or {}

    def list_active_for_role_across_tenants(self, role_id: str):
        return list(self._across_tenants.get(role_id, []))

    def list_active_for_role(self, role_id: str, *, tenant_id: str):
        return list(self._for_tenant.get((role_id, tenant_id), []))


class _FakeTenantContextService:
    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    def get_active_tenant_id(self) -> str:
        return self._tenant_id


def _binding(principal_id: str, principal_type: str = "user"):
    return SimpleNamespace(principal_id=principal_id, principal_type=principal_type)


def _build_service(*, notification_service, tenant_id="tenant-1"):
    role_approver = SimpleNamespace(id="role-approver", name="approver")
    role_viewer = SimpleNamespace(id="role-viewer", name="viewer")
    return ApprovalService(
        session=SimpleNamespace(),
        approval_repo=SimpleNamespace(),
        tenant_context_service=_FakeTenantContextService(tenant_id),
        notification_service=notification_service,
        role_repo=_FakeRoleRepo([role_approver, role_viewer]),
        role_permission_repo=_FakeRolePermissionRepo(
            {"role-approver": ["perm-approval-decide"], "role-viewer": ["perm-project-read"]}
        ),
        permission_repo=_FakePermissionRepo(
            {"approval.decide": "perm-approval-decide", "project.read": "perm-project-read"}
        ),
        role_binding_repo=_FakeRoleBindingRepo(
            for_tenant={
                ("role-approver", tenant_id): [
                    _binding("user-approver-1"),
                    _binding("user-requester"),  # requester also happens to hold the role
                ],
            },
            across_tenants={"role-approver": [_binding("user-platform-admin")]},
        ),
    )


def _make_request(**overrides) -> ApprovalRequest:
    defaults = dict(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id="baseline-1",
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
    assert recipients == {"user-approver-1", "user-platform-admin"}
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
