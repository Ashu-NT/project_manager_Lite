from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.roles.role_binding_scope import (
    ResolvedRoleBindingScope,
    ResourceBindingScope,
    TenantBindingScope,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    RoleBinding,
    RoleBindingAssigned,
    RoleBindingPlatformScope,
    RoleBindingResourceScope,
    RoleBindingRevoked,
    RoleBindingScope,
    RoleBindingTenantScope,
)
from src.core.shared.time.clock import Clock

OrganizationOwnerResolver = Callable[[Session, str, str], "str | None"]


def resolved_scope_to_domain_scope(resolved: ResolvedRoleBindingScope) -> RoleBindingScope:
    """Converts `RoleGovernanceService`'s own application-layer `ResolvedRoleBindingScope`
    (resolved mid-transaction via `_validate_target_scope`, which ALSO does existence checking)
    into the domain-facing, event-safe `RoleBindingScope`."""
    if isinstance(resolved, ResourceBindingScope):
        return RoleBindingResourceScope(
            tenant_id=resolved.tenant_id,
            organization_id=resolved.organization_id,
            scope_type=resolved.scope_type,
            scope_id=resolved.scope_id,
        )
    if isinstance(resolved, TenantBindingScope):
        return RoleBindingTenantScope(tenant_id=resolved.tenant_id)
    return RoleBindingPlatformScope()


def resolve_domain_scope_for_binding(
    *,
    session: Session,
    tenant_id: str,
    scope_type: str,
    scope_id: str | None,
    organization_owner_resolvers: dict[str, OrganizationOwnerResolver],
) -> RoleBindingScope:
    """For a binding that already exists (revocation, or a membership-removal cascade) --
    resolves the authoritative domain scope from the binding's own recorded
    `actual_scope_type`/`actual_scope_id`, without re-running existence validation (the binding
    already exists and was validated at assignment time). Shared by `RoleGovernanceService
    .revoke_role_binding` and `TenantMembershipService`'s own cascade revocation, so both use the
    SAME session-bound `organization_owner_resolvers` -- never the ambient active organization."""
    if scope_type == ROLE_SCOPE_TENANT:
        return RoleBindingTenantScope(tenant_id=tenant_id)
    if scope_type == ROLE_SCOPE_PLATFORM or scope_id is None:
        return RoleBindingPlatformScope()
    resolver = organization_owner_resolvers.get(scope_type)
    organization_id = resolver(session, tenant_id, scope_id) if resolver is not None else None
    return RoleBindingResourceScope(
        tenant_id=tenant_id,
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


def record_role_binding_audit_entry(
    audit_repo,
    *,
    actor,
    tenant_id: str | None,
    operation: str,
    entity_id: str,
    action: str,
    metadata: dict[str, object],
) -> None:
    entry = AuditEntry.create(
        operation=operation,
        entity_type="role_binding",
        entity_id=entity_id,
        entity_parent_id=tenant_id,
        module="platform",
        actor_id=actor.user_id,
        actor_username=actor.username,
        tenant_id=tenant_id,
        severity="high",
        compliance_tag="SOC2",
        metadata={"action": action, **metadata},
    )
    if tenant_id is None:
        audit_repo.add_platform(entry)
    else:
        audit_repo.add_for_tenant(entry, tenant_id)


def create_role_binding_using(
    *,
    role_bindings_repo,
    audit_repo,
    clock: Clock,
    record_event: Callable[[object], None],
    principal_id: str,
    role_id: str,
    tenant_id: str,
    scope_type: str,
    scope_id: str | None,
    domain_scope: RoleBindingScope,
    actor,
    expires_at: datetime | None = None,
    audit_action: str = "auth.role.binding.assigned",
    audit_metadata_extra: dict[str, object] | None = None,
) -> tuple[RoleBinding, bool]:
    """The exact mechanics `RoleGovernanceService.assign_role` used to inline: no-op check
    (revoke-expired-then-look-for-an-identical-active-binding), create, audit, record
    `RoleBindingAssigned`. Never opens a transaction, never commits -- the caller's own UoW owns
    that (the caller must still call `uow.commit()` itself when `is_noop` is `False`; on a
    genuine no-op it should return immediately WITHOUT committing, exactly like the original
    inline implementation did, so the outer UoW's own safety net discards the empty transaction).

    Returns `(binding, is_noop)`. `is_noop=True` means the existing binding was returned
    unchanged -- no write, no audit, no event, matching the established P5C-1/P5C-2 rule. A
    genuine `ROLE_BINDING_CONCURRENT_ASSIGNMENT` race is NOT handled here -- it can only
    surface from the caller's own subsequent `uow.commit()` (a real unique-constraint violation
    at the database level, never from `add()` alone); see `recover_from_concurrent_assignment`,
    which the caller should use to wrap that commit."""
    now = clock.now()
    role_bindings_repo.revoke_expired_for_assignment(
        principal_id=principal_id,
        role_id=role_id,
        tenant_id=tenant_id,
        actual_scope_type=scope_type,
        actual_scope_id=scope_id,
        as_of=now,
    )
    existing = role_bindings_repo.get_active_for_assignment(
        principal_id=principal_id,
        role_id=role_id,
        tenant_id=tenant_id,
        actual_scope_type=scope_type,
        actual_scope_id=scope_id,
    )
    if existing is not None:
        return existing, True

    binding = RoleBinding.create(
        principal_id=principal_id,
        role_id=role_id,
        tenant_id=tenant_id,
        actual_scope_type=scope_type,
        actual_scope_id=scope_id,
        assigned_by=actor.user_id,
        expires_at=expires_at,
    )
    role_bindings_repo.add(binding)
    record_role_binding_audit_entry(
        audit_repo,
        actor=actor,
        tenant_id=tenant_id,
        operation="permission_change",
        entity_id=binding.id,
        action=audit_action,
        metadata={
            "target_user_id": principal_id,
            "role_id": role_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "organization_id": getattr(domain_scope, "organization_id", None),
            "expires_at": binding.expires_at.isoformat() if binding.expires_at is not None else None,
            **(audit_metadata_extra or {}),
        },
    )
    record_event(
        RoleBindingAssigned(
            binding_id=binding.id,
            principal_id=principal_id,
            role_id=role_id,
            scope=domain_scope,
            occurred_at=now,
        )
    )
    return binding, False


def recover_from_concurrent_assignment(
    role_bindings_repo,
    *,
    principal_id: str,
    role_id: str,
    tenant_id: str,
    scope_type: str,
    scope_id: str | None,
) -> RoleBinding:
    """Call from an `except IntegrityError:` wrapping the caller's own `uow.commit()`, after a
    `create_role_binding_using(...)` call that returned `is_noop=False` -- a concurrent,
    identical assignment committed first. Re-queries on the SAME (already-rolled-back-by-the-
    failed-commit) Session; raises `ROLE_BINDING_CONCURRENT_ASSIGNMENT` only if that turns out
    not to explain the failure."""
    existing = role_bindings_repo.get_active_for_assignment(
        principal_id=principal_id,
        role_id=role_id,
        tenant_id=tenant_id,
        actual_scope_type=scope_type,
        actual_scope_id=scope_id,
    )
    if existing is not None:
        return existing
    raise BusinessRuleError(
        "The canonical role was assigned concurrently.",
        code="ROLE_BINDING_CONCURRENT_ASSIGNMENT",
    )


def revoke_role_binding_using(
    *,
    role_bindings_repo,
    audit_repo,
    clock: Clock,
    record_event: Callable[[object], None],
    binding: RoleBinding,
    domain_scope: RoleBindingScope,
    actor,
    audit_action: str = "auth.role.binding.revoked",
    audit_metadata_extra: dict[str, object] | None = None,
) -> RoleBinding:
    """Mirrors `create_role_binding_using`'s own shape for revocation. The caller is responsible
    for the no-op check (already-revoked) BEFORE calling this -- `RoleGovernanceService
    .revoke_role_binding` and `TenantMembershipService`'s cascade both only ever call this for a
    binding already confirmed active, so it is not re-checked here."""
    now = clock.now()
    role_bindings_repo.revoke(binding.id, revoked_at=now)
    record_role_binding_audit_entry(
        audit_repo,
        actor=actor,
        tenant_id=binding.tenant_id,
        operation="delete",
        entity_id=binding.id,
        action=audit_action,
        metadata={
            "target_user_id": binding.principal_id,
            "role_id": binding.role_id,
            "scope_type": binding.actual_scope_type,
            "scope_id": binding.actual_scope_id,
            **(audit_metadata_extra or {}),
        },
    )
    record_event(
        RoleBindingRevoked(
            binding_id=binding.id,
            principal_id=binding.principal_id,
            role_id=binding.role_id,
            scope=domain_scope,
            occurred_at=now,
        )
    )
    return replace(binding, revoked_at=now, version=binding.version + 1)


__all__ = [
    "OrganizationOwnerResolver",
    "resolved_scope_to_domain_scope",
    "resolve_domain_scope_for_binding",
    "record_role_binding_audit_entry",
    "create_role_binding_using",
    "revoke_role_binding_using",
]
