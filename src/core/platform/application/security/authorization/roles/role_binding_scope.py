from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformBindingScope:
    """No tenant, no resource. Not reachable through `assign_role`/`revoke_role_binding` today
    (platform-role assignment is explicitly denied there, per the existing "dedicated
    provisioning workflow" business rule) -- represented here for completeness/documentation."""


@dataclass(frozen=True, slots=True)
class TenantBindingScope:
    """Tenant-wide -- no resource, no organization. `tenant_id` is always the caller's own
    authenticated tenant (never ambient/active-organization-derived)."""

    tenant_id: str


@dataclass(frozen=True, slots=True)
class ResourceBindingScope:
    """Exactly one resource (project/site/storeroom/... ) within one tenant.

    `organization_id` is the resource's OWN authoritative organization ownership, resolved via
    the registered `organization_owner_resolver` for `scope_type` -- never the ambient active
    organization. `None` only when the resource type/instance genuinely has no organization
    owner (documented per resource type, not invented)."""

    tenant_id: str
    scope_type: str
    scope_id: str
    organization_id: str | None


ResolvedRoleBindingScope = PlatformBindingScope | TenantBindingScope | ResourceBindingScope


__all__ = [
    "PlatformBindingScope",
    "TenantBindingScope",
    "ResourceBindingScope",
    "ResolvedRoleBindingScope",
]
