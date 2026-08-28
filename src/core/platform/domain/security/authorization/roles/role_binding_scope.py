from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoleBindingPlatformScope:
    """No tenant, no organization, no resource. (Not reachable through
    `RoleGovernanceService.assign_role`/`revoke_role_binding` today -- platform-role assignment
    is denied there by an existing business rule -- represented here for completeness, matching
    `PlatformBindingScope`'s own documented non-reachability.)"""


@dataclass(frozen=True, slots=True)
class RoleBindingTenantScope:
    """Tenant-wide -- no organization, no resource."""

    tenant_id: str


@dataclass(frozen=True, slots=True)
class RoleBindingResourceScope:
    """Exactly one resource (project/site/storeroom/organization/...) within one tenant.

    `organization_id` is the resource's OWN authoritative organization ownership (resolved
    inside the RoleGovernance transaction, never the desktop's ambient active organization) --
    `None` only when the resource type/instance genuinely has no organization owner."""

    tenant_id: str
    organization_id: str | None
    scope_type: str
    scope_id: str


RoleBindingScope = RoleBindingPlatformScope | RoleBindingTenantScope | RoleBindingResourceScope


__all__ = [
    "RoleBindingPlatformScope",
    "RoleBindingTenantScope",
    "RoleBindingResourceScope",
    "RoleBindingScope",
]
