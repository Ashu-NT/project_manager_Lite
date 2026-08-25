"""P5C-2: `RoleBindingAssigned`/`RoleBindingRevoked` -- the canonical RoleBinding capability's own
business event vocabulary, their recording lifecycle inside `RoleGovernanceService.assign_role`/
`revoke_role_binding`, and the no-event/exactly-once guarantees this phase decided.

Mirrors `test_module_entitlement_events.py`/`test_organization_created_event.py`'s own patterns
(`_spy_recorded_events`, `_FixedClock`, post-commit-bus subscription for observability/rollback
proofs). Complements `test_role_governance_unit_of_work_cutover.py` (P5C-1's transaction/scope
mechanics, unchanged here).

This phase adds ONLY `RoleBindingAssigned`/`RoleBindingRevoked` -- no ViewInvalidation, no Qt
migration, no `access_changed`/`auth_changed` removal, no delegation-policy or custom-role
events. `test_no_p5c3_production_code_exists_for_role_binding_events` and the "facade does not
record" tests enforce that phase boundary.
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass, replace
from datetime import datetime, timezone

import pytest

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.domain.security.authorization.roles.role_binding_scope import (
    RoleBindingPlatformScope,
    RoleBindingResourceScope,
    RoleBindingTenantScope,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyRoleBindingRepository,
)
from src.core.platform.infrastructure.persistence.role_governance_unit_of_work import (
    SqlAlchemyRoleGovernanceUnitOfWork,
)
from src.core.shared.events.domain_event import DomainEvent

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _tenant_id(services) -> str:
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    assert tenant_id is not None
    return tenant_id


class _FixedClock:
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


def _switch_session_to_actor(services, actor, *, tenant_id, organization_id=None, extra_permissions=()):
    auth = services["auth_service"]
    if organization_id is None:
        organization_id = services["tenant_context_service"].get_active_organization_id()
    principal = auth.build_principal_for_context(
        actor, tenant_id=tenant_id, organization_id=organization_id
    )
    services["user_session"].set_principal(
        replace(
            principal,
            session_id=None,
            permissions=frozenset({*principal.permissions, *extra_permissions}),
        )
    )


def _tenant_scoped_binding_setup(services, *, suffix: str, role_name: str = "viewer"):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"p5c2-actor-{suffix}", "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        f"p5c2-target-{suffix}", "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(role_name)
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=target_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    return target, target_role


def _resource_scoped_binding_setup(services, *, suffix, scope_type, role_name, organization_id=None):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        f"p5c2-actor-{suffix}", "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        f"p5c2-target-{suffix}", "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(role_name)
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=target_role.id,
        target_scope_type=scope_type,
        tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services,
        actor,
        tenant_id=tenant_id,
        organization_id=organization_id,
        extra_permissions=("auth.role.assign",),
    )
    return target, target_role


def _spy_recorded_events(role_governance_service, monkeypatch) -> list:
    recorded = []
    original_create = type(role_governance_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event

        def _spy_record_event(event):
            assert uow._committed is False, "event must be recorded before commit, not after"
            recorded.append(event)
            return original_record_event(event)

        uow.record_event = _spy_record_event
        return uow

    monkeypatch.setattr(type(role_governance_service._uow_factory), "create", _spy_create)
    return recorded


# ---------------------------------------------------------------------------
# Event contract / architecture guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event_cls", [RoleBindingAssigned, RoleBindingRevoked])
def test_role_binding_event_conforms_to_domain_event_and_has_only_approved_fields(event_cls):
    event = event_cls(
        binding_id="b1",
        principal_id="p1",
        role_id="r1",
        scope=RoleBindingTenantScope(tenant_id="t1"),
        occurred_at=datetime.now(timezone.utc),
    )
    assert isinstance(event, DomainEvent)
    assert is_dataclass(event)
    assert {f.name for f in fields(event)} == {"binding_id", "principal_id", "role_id", "scope", "occurred_at"}
    with pytest.raises(AttributeError):
        event.role_id = "changed"  # type: ignore[misc]
    for forbidden in (
        "correlation_id", "causation_id", "command_id", "schema_version", "actor_id",
        "audit_message", "permission_snapshot", "effective_permissions",
    ):
        assert not hasattr(event, forbidden)


def _imported_module_names(module) -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_role_binding_events_module_has_no_ui_or_infrastructure_vocabulary():
    from src.core.platform.domain.security.authorization.roles import events as events_module

    imports = _imported_module_names(events_module)
    for forbidden in (
        "view_invalidation", "domain_events", "PySide6", "QtCore", "ui_qml",
        "infrastructure", "sqlalchemy",
    ):
        assert not any(forbidden in name.lower() for name in imports), imports


def test_role_binding_scope_module_has_no_ui_or_infrastructure_vocabulary():
    from src.core.platform.domain.security.authorization.roles import role_binding_scope as scope_module

    imports = _imported_module_names(scope_module)
    for forbidden in (
        "view_invalidation", "domain_events", "PySide6", "QtCore", "ui_qml",
        "infrastructure", "sqlalchemy",
    ):
        assert not any(forbidden in name.lower() for name in imports), imports


def test_shared_events_package_does_not_import_role_binding_events():
    import src.core.shared.events.domain_event as shared_domain_event_module

    source = inspect.getsource(shared_domain_event_module)
    for forbidden in ("RoleBindingAssigned", "RoleBindingRevoked", "RoleBindingScope"):
        assert forbidden not in source


def test_access_facade_does_not_record_role_binding_events():
    """The facade's own comments legitimately MENTION `RoleBindingAssigned` (documenting why
    `access_changed` was retired, per P5C-3) -- what must never exist is an actual construction
    of the event or a call to `record_event`/`uow.record_event`."""
    import src.core.platform.access.application.access_control_service as access_module

    source = inspect.getsource(access_module)
    for forbidden in ("RoleBindingAssigned(", "RoleBindingRevoked(", "record_event", "uow.record_event"):
        assert forbidden not in source


def test_tenant_role_facade_does_not_record_role_binding_events():
    import src.core.platform.application.security.authorization.roles.role_assignment_service as facade_module

    source = inspect.getsource(facade_module)
    for forbidden in ("RoleBindingAssigned", "RoleBindingRevoked", "record_event"):
        assert forbidden not in source


def test_no_p5c3_production_code_exists_for_role_binding_events():
    import src.core.platform.application.security.authorization.roles.role_governance_service as service_module

    source = inspect.getsource(service_module)
    for forbidden in ("ViewInvalidation", "PySide6", "ui_qml", "QtCore"):
        assert forbidden not in source


def test_role_governance_service_introduces_no_new_arbitrary_session_usage():
    """The `session: Session` parameter threaded through `_validate_target_scope`/
    `_resolve_domain_scope_for_binding` exists ONLY to pass the calling UoW's own Session into
    the registered (session-bound) resource resolvers -- P5C-2 must not have introduced a new,
    separate, direct SQLAlchemy query inside `RoleGovernanceService` itself."""
    import src.core.platform.application.security.authorization.roles.role_governance_service as service_module

    source = inspect.getsource(service_module)
    for forbidden in ("session.execute(", "session.query(", "select(", "session.add(", "session.get("):
        assert forbidden not in source


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------


def test_assign_role_uses_the_injected_clock_deterministically(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="clock")
    role_governance_service = services["role_governance_service"]
    fixed_when = datetime(2031, 3, 4, 9, 30, 0, tzinfo=timezone.utc)
    original_clock = role_governance_service._clock
    role_governance_service._clock = _FixedClock(fixed_when)
    try:
        recorded = _spy_recorded_events(role_governance_service, monkeypatch)
        role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
        assert recorded[0].occurred_at == fixed_when
    finally:
        role_governance_service._clock = original_clock


# ---------------------------------------------------------------------------
# Assign / revoke recording point
# ---------------------------------------------------------------------------


def test_assign_role_records_exactly_one_role_binding_assigned_with_tenant_scope(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="assign-tenant")
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    binding = role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, RoleBindingAssigned)
    assert event.binding_id == binding.id
    assert event.principal_id == target.id
    assert event.role_id == target_role.id
    assert event.scope == RoleBindingTenantScope(tenant_id=_tenant_id(services))


def test_assign_role_on_identical_active_binding_records_zero_events(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="assign-noop")
    role_governance_service = services["role_governance_service"]
    role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert recorded == []


def test_revoke_role_binding_records_exactly_one_role_binding_revoked(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="revoke")
    role_governance_service = services["role_governance_service"]
    binding = role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.revoke_role_binding(binding.id)

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, RoleBindingRevoked)
    assert event.binding_id == binding.id
    assert event.principal_id == target.id
    assert event.role_id == target_role.id
    assert event.scope == RoleBindingTenantScope(tenant_id=_tenant_id(services))


def test_revoke_already_revoked_binding_records_zero_events(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="revoke-noop")
    role_governance_service = services["role_governance_service"]
    binding = role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    role_governance_service.revoke_role_binding(binding.id)
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.revoke_role_binding(binding.id)

    assert recorded == []


def test_revoke_unknown_binding_records_zero_events(services, monkeypatch):
    _tenant_scoped_binding_setup(services, suffix="revoke-unknown")
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    with pytest.raises(NotFoundError):
        role_governance_service.revoke_role_binding(_unique_code("nonexistent-binding"))

    assert recorded == []


# ---------------------------------------------------------------------------
# Scope variants
# ---------------------------------------------------------------------------


def test_platform_scope_assignment_is_denied_by_the_legitimate_canonical_path_and_emits_nothing(
    services, monkeypatch
):
    """Platform-role assignment is denied by an existing business rule
    (`PLATFORM_ROLE_ASSIGNMENT_DENIED`) before scope resolution is even reached -- proven through
    the real canonical service, not weakened to manufacture a platform-scoped event."""
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c2-platform-actor"), "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c2-platform-target"), "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    platform_role = auth._role_repo.get_by_name("admin")
    assert platform_role is not None and platform_role.allowed_scope_type == "platform"
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    with pytest.raises(BusinessRuleError) as exc_info:
        role_governance_service.assign_role(target_user_id=target.id, role_id=platform_role.id)

    assert exc_info.value.code == "PLATFORM_ROLE_ASSIGNMENT_DENIED"
    assert recorded == []


def test_resource_scope_assignment_in_a_non_active_organization_carries_the_authoritative_organization(
    services, monkeypatch
):
    tenant_context_service = services["tenant_context_service"]
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C2-A1-SITE"), name="A1 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a1 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C2-A1-ROOM"), name="A1 Storeroom", site_id=site_a1.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    org_a1_id = storeroom_a1.organization_id
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C2-A2"), display_name="P5C-2 Org A2", is_active=True
    )
    tenant_context_service.set_active_organization(org_a2.id)

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="resource-nonactive", scope_type="storeroom", role_name="storeroom_viewer",
        organization_id=org_a2.id,
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    binding = role_governance_service.assign_role(
        target_user_id=target.id, role_id=target_role.id, actual_scope_id=storeroom_a1.id
    )

    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, RoleBindingAssigned)
    assert event.binding_id == binding.id
    assert event.scope == RoleBindingResourceScope(
        tenant_id=_tenant_id(services), organization_id=org_a1_id, scope_type="storeroom", scope_id=storeroom_a1.id,
    )
    assert event.scope.organization_id == org_a1_id
    assert event.scope.organization_id != org_a2.id


def test_resource_scope_revocation_preserves_the_same_authoritative_binding_scope_identity(
    services, monkeypatch
):
    tenant_context_service = services["tenant_context_service"]
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C2-REV-A1-SITE"), name="A1 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a1 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C2-REV-A1-ROOM"), name="A1 Storeroom", site_id=site_a1.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    org_a1_id = storeroom_a1.organization_id
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C2-REV-A2"), display_name="P5C-2 Revoke Org A2", is_active=True
    )
    tenant_context_service.set_active_organization(org_a2.id)

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="resource-revoke-nonactive", scope_type="storeroom", role_name="storeroom_viewer",
        organization_id=org_a2.id,
    )
    role_governance_service = services["role_governance_service"]
    binding = role_governance_service.assign_role(
        target_user_id=target.id, role_id=target_role.id, actual_scope_id=storeroom_a1.id
    )
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.revoke_role_binding(binding.id)

    assert tenant_context_service.get_active_organization_id() == org_a2.id  # never switched
    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, RoleBindingRevoked)
    assert event.binding_id == binding.id
    assert event.scope == RoleBindingResourceScope(
        tenant_id=_tenant_id(services), organization_id=org_a1_id, scope_type="storeroom", scope_id=storeroom_a1.id,
    )


def test_project_scope_event_carries_the_authoritative_organization_from_the_corrected_repository(
    services, monkeypatch
):
    tenant_context_service = services["tenant_context_service"]
    project_a1 = services["project_service"].create_project("P5C-2 Non-Active Org Project")
    org_a1_id = project_a1.organization_id
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C2-PROJ-A2"), display_name="P5C-2 Project Org A2"
    )
    tenant_context_service.set_active_organization(org_a2.id)

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="project-scope", scope_type="project", role_name="project_viewer",
        organization_id=org_a2.id,
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.assign_role(
        target_user_id=target.id, role_id=target_role.id, actual_scope_id=project_a1.id
    )

    assert len(recorded) == 1
    assert recorded[0].scope.organization_id == org_a1_id
    assert recorded[0].scope.scope_type == "project"
    assert recorded[0].scope.scope_id == project_a1.id


def test_site_scope_event_carries_the_authoritative_organization_from_the_corrected_repository(
    services, monkeypatch
):
    tenant_context_service = services["tenant_context_service"]
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C2-SITE-A1"), name="A1 Site", city="Berlin", currency_code="EUR"
    )
    org_a1_id = site_a1.organization_id
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C2-SITE-A2"), display_name="P5C-2 Site Org A2"
    )
    tenant_context_service.set_active_organization(org_a2.id)

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="site-scope", scope_type="site", role_name="site_viewer",
        organization_id=org_a2.id,
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.assign_role(
        target_user_id=target.id, role_id=target_role.id, actual_scope_id=site_a1.id
    )

    assert len(recorded) == 1
    assert recorded[0].scope.organization_id == org_a1_id
    assert recorded[0].scope.scope_type == "site"
    assert recorded[0].scope.scope_id == site_a1.id


def test_storeroom_scope_event_carries_the_authoritative_organization_from_the_corrected_repository(
    services, monkeypatch
):
    tenant_context_service = services["tenant_context_service"]
    site_a1 = services["site_service"].create_site(
        site_code=_unique_code("P5C2-STOREROOM-A1-SITE"), name="A1 Site", city="Berlin", currency_code="EUR"
    )
    storeroom_a1 = services["inventory_service"].create_storeroom(
        storeroom_code=_unique_code("P5C2-STOREROOM-A1-ROOM"), name="A1 Storeroom", site_id=site_a1.id,
        status="ACTIVE", storeroom_type="MAIN",
    )
    org_a1_id = storeroom_a1.organization_id
    org_a2 = services["organization_service"].create_organization(
        organization_code=_unique_code("P5C2-STOREROOM-A2"), display_name="P5C-2 Storeroom Org A2", is_active=True
    )
    tenant_context_service.set_active_organization(org_a2.id)

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="storeroom-scope", scope_type="storeroom", role_name="storeroom_viewer",
        organization_id=org_a2.id,
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    role_governance_service.assign_role(
        target_user_id=target.id, role_id=target_role.id, actual_scope_id=storeroom_a1.id
    )

    assert len(recorded) == 1
    assert recorded[0].scope.organization_id == org_a1_id
    assert recorded[0].scope.scope_type == "storeroom"
    assert recorded[0].scope.scope_id == storeroom_a1.id


# ---------------------------------------------------------------------------
# Cross-tenant
# ---------------------------------------------------------------------------


def test_cross_tenant_storeroom_assignment_attempt_emits_zero_events(services, monkeypatch):
    from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import StoreroomORM
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM

    session = services["session"]
    now = datetime.now(timezone.utc)
    foreign_tenant_id = _unique_code("p5c2-foreign-tenant")
    session.add(TenantORM(
        id=foreign_tenant_id, tenant_code=_unique_code("P5C2FT"), display_name="Foreign Tenant",
        is_active=True, version=1,
    ))
    session.commit()
    foreign_org_id = _unique_code("p5c2-foreign-org")
    session.add(OrganizationORM(
        id=foreign_org_id, tenant_id=foreign_tenant_id, organization_code=_unique_code("P5C2FORG"),
        display_name="Foreign Org", is_active=True, version=1,
    ))
    session.commit()
    foreign_site_id = _unique_code("p5c2-foreign-site")
    session.add(SiteORM(
        id=foreign_site_id, tenant_id=foreign_tenant_id, organization_id=foreign_org_id,
        site_code=_unique_code("P5C2FSITE"), name="Foreign Site", is_active=True,
        created_at=now, updated_at=now, version=1,
    ))
    session.commit()
    foreign_storeroom_id = _unique_code("p5c2-foreign-storeroom")
    session.add(StoreroomORM(
        id=foreign_storeroom_id, tenant_id=foreign_tenant_id, organization_id=foreign_org_id,
        site_id=foreign_site_id, storeroom_code=_unique_code("P5C2FROOM"), name="Foreign Storeroom",
        status="ACTIVE", created_at=now, updated_at=now, version=1,
    ))
    session.commit()

    target, target_role = _resource_scoped_binding_setup(
        services, suffix="cross-tenant", scope_type="storeroom", role_name="storeroom_viewer",
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    with pytest.raises(NotFoundError) as exc_info:
        role_governance_service.assign_role(
            target_user_id=target.id, role_id=target_role.id, actual_scope_id=foreign_storeroom_id
        )

    assert exc_info.value.code == "STOREROOM_NOT_FOUND"
    assert recorded == []


# ---------------------------------------------------------------------------
# Authorization / SoD failure produces zero mutation, zero audit, zero event
# ---------------------------------------------------------------------------


def test_delegation_denied_produces_zero_mutation_zero_audit_zero_event(services, monkeypatch):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c2-nodeleg-actor"), "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code("p5c2-nodeleg-target"), "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    viewer_role = auth._role_repo.get_by_name("viewer")
    # No delegation policy created -- the actor has no authority to grant "viewer".
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    with pytest.raises(BusinessRuleError) as exc_info:
        role_governance_service.assign_role(target_user_id=target.id, role_id=viewer_role.id)

    assert exc_info.value.code == "ROLE_DELEGATION_DENIED"
    assert recorded == []
    assert SqlAlchemyRoleBindingRepository(services["session"]).get_active_for_assignment(
        principal_id=target.id, role_id=viewer_role.id, tenant_id=tenant_id,
        actual_scope_type="tenant", actual_scope_id=None,
    ) is None


def test_separation_of_duties_conflict_produces_zero_mutation_zero_audit_zero_event(services, monkeypatch):
    from src.core.platform.domain.security.authorization.enforcement.sod import (
        SeparationOfDutiesPolicy,
        SeparationOfDutiesRule,
    )

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c2-sod-actor"), "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    grantor_role = auth._role_repo.get_by_name("access_admin")
    security_role = auth._role_repo.get_by_name("security_admin")
    assert grantor_role is not None and security_role is not None
    target = auth.register_user(
        _unique_code("p5c2-sod-target"), "P5C2Target123!", role_names=[grantor_role.name], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id, assignable_role_id=security_role.id,
        target_scope_type="tenant", tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    role_governance_service = services["role_governance_service"]
    original_policy = role_governance_service._sod_policy
    role_governance_service._sod_policy = SeparationOfDutiesPolicy(rules=(
        SeparationOfDutiesRule(
            required_permissions=frozenset({"access.manage", "security.manage"}),
            message="Users cannot both manage scoped access and manage login security controls.",
        ),
    ))
    try:
        recorded = _spy_recorded_events(role_governance_service, monkeypatch)
        with pytest.raises(ValidationError) as exc_info:
            role_governance_service.assign_role(target_user_id=target.id, role_id=security_role.id)
        assert exc_info.value.code == "ROLE_CONFLICT"
        assert recorded == []
    finally:
        role_governance_service._sod_policy = original_policy


# ---------------------------------------------------------------------------
# Audit failure / commit failure / post-commit handler failure
# ---------------------------------------------------------------------------


def test_audit_staging_failure_rolls_back_binding_and_records_zero_observable_event(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="audit-fail")
    role_governance_service = services["role_governance_service"]
    bus = role_governance_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen.append(e))

    def _fail_audit(self, entry, tenant_id):
        raise RuntimeError("simulated audit staging failure")

    monkeypatch.setattr(SqlAlchemyAuditRepository, "add_for_tenant", _fail_audit)

    with pytest.raises(RuntimeError, match="simulated audit staging failure"):
        role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert seen == []
    assert SqlAlchemyRoleBindingRepository(services["session"]).get_active_for_assignment(
        principal_id=target.id, role_id=target_role.id, tenant_id=_tenant_id(services),
        actual_scope_type="tenant", actual_scope_id=None,
    ) is None


def test_no_event_observable_on_commit_failure(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="commit-fail")
    role_governance_service = services["role_governance_service"]
    bus = role_governance_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen.append(e))

    def _fail_commit(self):
        raise RuntimeError("simulated role governance commit failure")

    monkeypatch.setattr(SqlAlchemyRoleGovernanceUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated role governance commit failure"):
        role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert seen == []


def test_one_post_commit_handler_failing_does_not_block_the_other_or_the_commit(services):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="handler-fail")
    role_governance_service = services["role_governance_service"]
    bus = role_governance_service._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    healthy_seen = []
    bus.subscribe(RoleBindingAssigned, _failing_handler)
    bus.subscribe(RoleBindingAssigned, lambda e, c: healthy_seen.append(e))

    # Must not raise -- ISOLATE_AND_CONTINUE swallows the failing handler's exception.
    binding = role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert len(healthy_seen) == 1
    assert SqlAlchemyRoleBindingRepository(services["session"]).get(binding.id) is not None


def test_post_commit_subscriber_receives_the_commands_own_domain_event_context(services):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="context")
    role_governance_service = services["role_governance_service"]
    bus = role_governance_service._uow_factory._post_commit_bus
    seen = {}

    def _capture(event, context):
        seen["event"] = event
        seen["context"] = context

    bus.subscribe(RoleBindingAssigned, _capture)
    role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)

    assert isinstance(seen["event"], RoleBindingAssigned)
    assert not hasattr(seen["event"], "correlation_id")
    assert not hasattr(seen["event"], "causation_id")
    assert seen["context"].correlation_id is not None


# ---------------------------------------------------------------------------
# Current-principal refresh / fail-closed semantics are independent of event subscribers
# ---------------------------------------------------------------------------


def test_current_principal_self_refresh_unaffected_by_a_broken_role_binding_event_subscriber(services):
    """P5C-2 must not make security-state consistency depend on a best-effort event handler --
    the existing explicit post-commit refresh flow (established in P5C-1) must keep working
    even when a RoleBindingRevoked subscriber raises."""
    from src.tests.ui_runtime_helpers import login_as

    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    username = _unique_code("p5c2-self-actor")
    self_actor = auth.register_user(
        username, "P5C2SelfActor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    tenant_admin_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=tenant_admin_role.id, assignable_role_id=viewer_role.id,
        target_scope_type="tenant", tenant_id=tenant_id,
    )
    login_as(services, username, "P5C2SelfActor123!")
    auth.assign_role(self_actor.id, "viewer")
    assert "viewer" in services["user_session"].principal.role_names

    role_governance_service = services["role_governance_service"]
    bus = role_governance_service._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    bus.subscribe(RoleBindingRevoked, _failing_handler)

    auth.revoke_role(self_actor.id, "viewer")

    assert "viewer" not in services["user_session"].principal.role_names


# ---------------------------------------------------------------------------
# Legacy signals unchanged; delegation-policy remains eventless
# ---------------------------------------------------------------------------


def test_legacy_auth_changed_still_fires_alongside_the_new_typed_event(services, monkeypatch):
    target, target_role = _tenant_scoped_binding_setup(services, suffix="legacy-signal")
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    from src.core.shared.events.domain_events import domain_events

    seen_signals = []
    domain_events.auth_changed.connect(seen_signals.append)
    try:
        role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    finally:
        domain_events.auth_changed.disconnect(seen_signals.append)

    assert len(recorded) == 1
    assert seen_signals == [target.id]


def test_delegation_policy_lifecycle_emits_no_role_binding_events(services, monkeypatch):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    policy = role_governance_service.create_delegation_policy(
        actor_role_id=actor_role.id, assignable_role_id=viewer_role.id,
        target_scope_type="tenant", tenant_id=tenant_id,
    )
    role_governance_service.revoke_delegation_policy(policy.id)

    assert recorded == []


# ---------------------------------------------------------------------------
# Sequence / committed order
# ---------------------------------------------------------------------------


def test_sequence_of_assign_assign_revoke_produces_events_in_committed_order(services, monkeypatch):
    auth = services["auth_service"]
    tenant_id = _tenant_id(services)
    actor = auth.register_user(
        _unique_code("p5c2-seq-actor"), "P5C2Actor123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target_a = auth.register_user(
        _unique_code("p5c2-seq-target-a"), "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    target_b = auth.register_user(
        _unique_code("p5c2-seq-target-b"), "P5C2Target123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id, assignable_role_id=viewer_role.id,
        target_scope_type="tenant", tenant_id=tenant_id,
    )
    _switch_session_to_actor(
        services, actor, tenant_id=tenant_id, extra_permissions=("auth.role.assign",)
    )
    role_governance_service = services["role_governance_service"]
    recorded = _spy_recorded_events(role_governance_service, monkeypatch)

    binding_a = role_governance_service.assign_role(target_user_id=target_a.id, role_id=viewer_role.id)
    role_governance_service.assign_role(target_user_id=target_b.id, role_id=viewer_role.id)
    role_governance_service.revoke_role_binding(binding_a.id)

    assert len(recorded) == 3
    assert [type(e) for e in recorded] == [RoleBindingAssigned, RoleBindingAssigned, RoleBindingRevoked]
    assert recorded[0].principal_id == target_a.id
    assert recorded[1].principal_id == target_b.id
    assert recorded[2].binding_id == binding_a.id
