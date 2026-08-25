from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.core.platform.access.application.access_control_service import AccessControlService
from src.core.platform.access.domain import (
    ScopedAccessGrant,
    ScopedRolePolicy,
    ScopedRolePolicyRegistry,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1


@dataclass
class _FakeUser:
    id: str
    username: str


class _FakeUserRepo:
    def __init__(self) -> None:
        self._rows = {"user-1": _FakeUser(id="user-1", username="ada")}

    def get(self, user_id: str) -> _FakeUser | None:
        return self._rows.get(user_id)


@dataclass
class _FakeTenantMembership:
    user_id: str
    tenant_id: str
    status: str = "active"


class _FakeUserTenantRepo:
    def __init__(self) -> None:
        self.membership = _FakeTenantMembership("user-1", "tenant-1")

    def get(self, user_id: str, tenant_id: str) -> _FakeTenantMembership | None:
        if (
            self.membership.user_id == user_id
            and self.membership.tenant_id == tenant_id
        ):
            return self.membership
        return None


class _FakeTenantContextService:
    def require_active_tenant_id(self, *, operation_label: str) -> str:
        del operation_label
        return "tenant-1"


def _make_policy_registry() -> ScopedRolePolicyRegistry:
    def _normalize_role(value: str) -> str:
        return str(value or "").strip().lower() or "viewer"

    def _site_permissions(role: str) -> tuple[str, ...]:
        if role == "editor":
            return ("site.read", "site.write")
        return ("site.read",)

    return ScopedRolePolicyRegistry(
        (
            ScopedRolePolicy(
                scope_type="site",
                role_choices=("viewer", "editor"),
                normalize_role=_normalize_role,
                resolve_permissions=_site_permissions,
            ),
        )
    )


def _make_service(monkeypatch: pytest.MonkeyPatch) -> AccessControlService:
    monkeypatch.setattr(
        "src.core.platform.access.application.access_control_service.require_permission",
        lambda *args, **kwargs: None,
    )
    return AccessControlService(
        session=_FakeSession(),
        user_repo=_FakeUserRepo(),
        auth_service=object(),
        policy_registry=_make_policy_registry(),
        scope_exists_resolvers={
            "site": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "site-1"
            ),
        },
        user_session=None,
        user_tenant_repo=_FakeUserTenantRepo(),
        tenant_context_service=_FakeTenantContextService(),
    )


def test_scoped_access_grant_dto_normalizes_and_validates_fields():
    grant = ScopedAccessGrant.create(
        scope_type="  SITE  ",
        scope_id="  site-1  ",
        user_id="  user-1  ",
        scope_role="  EDITOR  ",
        permission_codes=[" site.write ", "site.read", "site.write", ""],
    )

    assert grant.scope_type == "site"
    assert grant.scope_id == "site-1"
    assert grant.user_id == "user-1"
    assert grant.scope_role == "editor"
    assert grant.permission_codes == ["site.read", "site.write"]

    with pytest.raises(ValidationError) as exc_scope:
        ScopedAccessGrant.create(
            scope_type="site",
            scope_id=" ",
            user_id="user-1",
            scope_role="viewer",
        )
    assert exc_scope.value.code == "SCOPE_ID_REQUIRED"

    with pytest.raises(ValidationError) as exc_user:
        ScopedAccessGrant.create(
            scope_type="site",
            scope_id="site-1",
            user_id=" ",
            scope_role="viewer",
        )
    assert exc_user.value.code == "USER_ID_REQUIRED"


def test_access_service_denies_missing_scope_ownership_resolver(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch)
    service._scope_exists_resolvers.pop("site")

    with pytest.raises(BusinessRuleError) as exc_info:
        service.assign_scope_grant(
            scope_type="site",
            scope_id="site-1",
            user_id="user-1",
            scope_role="viewer",
        )

    assert exc_info.value.code == "AUTHORIZATION_SCOPE_RESOLVER_REQUIRED"


def test_access_service_denies_target_without_active_tenant_membership(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch)
    service._user_tenant_repo.membership.status = "suspended"

    with pytest.raises(BusinessRuleError) as exc_info:
        service.assign_scope_grant(
            scope_type="site",
            scope_id="site-1",
            user_id="user-1",
            scope_role="viewer",
        )

    assert exc_info.value.code == "ACCESS_TARGET_TENANT_DENIED"
