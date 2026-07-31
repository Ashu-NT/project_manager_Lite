from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.core.platform.access.application.access_control_service import AccessControlService
from src.core.platform.access.domain import (
    ProjectMembership,
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
    is_active: bool = True


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


class _FakeMembershipRepo:
    def add(self, membership: ProjectMembership) -> None:
        return None

    def update(self, membership: ProjectMembership) -> None:
        return None

    def get(self, membership_id: str) -> ProjectMembership | None:
        return None

    def get_for_project_user(self, project_id: str, user_id: str) -> ProjectMembership | None:
        return None

    def list_by_project(self, project_id: str) -> list[ProjectMembership]:
        return []

    def list_by_user(self, user_id: str) -> list[ProjectMembership]:
        return []

    def delete(self, membership_id: str) -> None:
        return None


class _FakeScopedAccessRepo:
    def __init__(self) -> None:
        self._rows: dict[str, ScopedAccessGrant] = {}

    def add(self, grant: ScopedAccessGrant) -> None:
        self._rows[grant.id] = grant

    def update(self, grant: ScopedAccessGrant) -> None:
        self._rows[grant.id] = grant

    def get(self, grant_id: str) -> ScopedAccessGrant | None:
        return self._rows.get(grant_id)

    def get_for_scope_user(
        self,
        scope_type: str,
        scope_id: str,
        user_id: str,
    ) -> ScopedAccessGrant | None:
        for row in self._rows.values():
            if row.scope_type == scope_type and row.scope_id == scope_id and row.user_id == user_id:
                return row
        return None

    def list_by_scope(self, scope_type: str, scope_id: str) -> list[ScopedAccessGrant]:
        return [
            row
            for row in self._rows.values()
            if row.scope_type == scope_type and row.scope_id == scope_id
        ]

    def list_by_user(
        self,
        user_id: str,
        *,
        scope_type: str | None = None,
    ) -> list[ScopedAccessGrant]:
        rows = [row for row in self._rows.values() if row.user_id == user_id]
        if scope_type is not None:
            rows = [row for row in rows if row.scope_type == scope_type]
        return rows

    def delete(self, grant_id: str) -> None:
        self._rows.pop(grant_id, None)


def _make_policy_registry() -> ScopedRolePolicyRegistry:
    def _normalize_role(value: str) -> str:
        return str(value or "").strip().lower() or "viewer"

    def _project_permissions(role: str) -> tuple[str, ...]:
        if role == "lead":
            return ("project.read", "project.manage")
        return ("project.read",)

    def _site_permissions(role: str) -> tuple[str, ...]:
        if role == "editor":
            return ("site.read", "site.write")
        return ("site.read",)

    def _storeroom_permissions(role: str) -> tuple[str, ...]:
        if role == "editor":
            return ("inventory.read", "inventory.manage")
        return ("inventory.read",)

    def _maintenance_permissions(role: str) -> tuple[str, ...]:
        if role == "editor":
            return ("maintenance.read", "maintenance.manage")
        return ("maintenance.read",)

    # "department" is a registered RESOURCE_ROLE_SCOPE_TYPES member with no
    # ScopedRolePolicy ever wired in production composition, so it is a
    # permanent, never-cut-over legacy example scope for this fake harness
    # once organization/project/site/storeroom/maintenance are all canonical.
    def _department_permissions(role: str) -> tuple[str, ...]:
        if role == "editor":
            return ("department.read", "department.manage")
        return ("department.read",)

    return ScopedRolePolicyRegistry(
        (
            ScopedRolePolicy(
                scope_type="project",
                role_choices=("viewer", "lead"),
                normalize_role=_normalize_role,
                resolve_permissions=_project_permissions,
            ),
            ScopedRolePolicy(
                scope_type="site",
                role_choices=("viewer", "editor"),
                normalize_role=_normalize_role,
                resolve_permissions=_site_permissions,
            ),
            ScopedRolePolicy(
                scope_type="storeroom",
                role_choices=("viewer", "editor"),
                normalize_role=_normalize_role,
                resolve_permissions=_storeroom_permissions,
            ),
            ScopedRolePolicy(
                scope_type="maintenance",
                role_choices=("viewer", "editor"),
                normalize_role=_normalize_role,
                resolve_permissions=_maintenance_permissions,
            ),
            ScopedRolePolicy(
                scope_type="department",
                role_choices=("viewer", "editor"),
                normalize_role=_normalize_role,
                resolve_permissions=_department_permissions,
            ),
        )
    )


def _make_service(monkeypatch: pytest.MonkeyPatch) -> AccessControlService:
    monkeypatch.setattr(
        "src.core.platform.access.application.access_control_service.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.access.application.access_control_service.record_audit_entry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.access.application.access_control_service.domain_events.access_changed.emit",
        lambda *args, **kwargs: None,
    )
    return AccessControlService(
        session=_FakeSession(),
        membership_repo=_FakeMembershipRepo(),
        user_repo=_FakeUserRepo(),
        auth_service=object(),
        policy_registry=_make_policy_registry(),
        scoped_access_repo=_FakeScopedAccessRepo(),
        scope_exists_resolvers={
            "project": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "project-1"
            ),
            "site": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "site-1"
            ),
            "storeroom": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "storeroom-1"
            ),
            "maintenance": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "maintenance-1"
            ),
            "department": lambda tenant_id, scope_id: (
                tenant_id == "tenant-1" and scope_id == "department-1"
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


def test_project_membership_dto_normalizes_and_round_trips_to_grant():
    membership = ProjectMembership.create(
        project_id="  project-1  ",
        user_id="  user-1  ",
        scope_role="  LEAD  ",
        permission_codes=("project.manage", " project.read ", "project.read"),
    )

    assert membership.project_id == "project-1"
    assert membership.user_id == "user-1"
    assert membership.scope_role == "lead"
    assert membership.permission_codes == ["project.manage", "project.read"]

    grant = membership.as_scoped_access_grant()
    assert grant.scope_type == "project"
    assert grant.scope_id == "project-1"
    assert grant.permission_codes == ["project.manage", "project.read"]

    restored = ProjectMembership.from_scoped_access_grant(grant)
    assert restored.project_id == membership.project_id
    assert restored.user_id == membership.user_id
    assert restored.scope_role == membership.scope_role


def test_access_service_uses_entity_validation_for_memberships_and_grants(
    monkeypatch: pytest.MonkeyPatch,
):
    service = _make_service(monkeypatch)

    # Project, site, storeroom, and maintenance scope now all route through
    # canonical role_bindings and are covered end-to-end (with real
    # role_repo/role_binding_repo) in test_platform_access_scopes.py; this
    # fake service has no canonical dependencies wired, so entity-validation
    # coverage here uses the synthetic "department" scope, which is never
    # registered with a live ScopedRolePolicy in production and so never
    # gets cut over.
    grant = service.assign_scope_grant(
        scope_type="  department  ",
        scope_id="  department-1  ",
        user_id="  user-1  ",
        scope_role="  editor  ",
    )

    assert grant.scope_type == "department"
    assert grant.scope_id == "department-1"
    assert grant.user_id == "user-1"
    assert grant.scope_role == "editor"
    assert grant.permission_codes == ["department.manage", "department.read"]

    updated = service.assign_scope_grant(
        scope_type="department",
        scope_id="department-1",
        user_id="user-1",
        scope_role="viewer",
    )
    assert updated.id == grant.id
    assert updated.permission_codes == ["department.read"]

    with pytest.raises(ValidationError) as exc_scope:
        service.assign_scope_grant(
            scope_type="department",
            scope_id=" ",
            user_id="user-1",
            scope_role="viewer",
        )
    assert exc_scope.value.code == "SCOPE_ID_REQUIRED"


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
    service._user_tenant_repo.membership.is_active = False

    with pytest.raises(BusinessRuleError) as exc_info:
        service.assign_scope_grant(
            scope_type="site",
            scope_id="site-1",
            user_id="user-1",
            scope_role="viewer",
        )

    assert exc_info.value.code == "ACCESS_TARGET_TENANT_DENIED"
