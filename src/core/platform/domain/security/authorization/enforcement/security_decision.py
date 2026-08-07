from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityDenialEvent:
    operation: str
    reason_code: str
    operation_label: str
    actor_user_id: str | None
    actor_username: str | None
    session_id: str | None
    tenant_id: str | None
    organization_id: str | None
    required_permissions: tuple[str, ...] = ()
    target_scope_type: str | None = None
    target_scope_id: str | None = None


__all__ = ["SecurityDenialEvent"]
