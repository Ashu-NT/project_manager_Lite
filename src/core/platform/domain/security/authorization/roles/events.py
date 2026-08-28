from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.platform.domain.security.authorization.roles.role_binding_scope import (
    RoleBindingScope,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleBindingAssigned:
    binding_id: str
    principal_id: str
    role_id: str
    scope: RoleBindingScope
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleBindingRevoked:
    binding_id: str
    principal_id: str
    role_id: str
    scope: RoleBindingScope
    occurred_at: datetime


__all__ = ["RoleBindingAssigned", "RoleBindingRevoked"]
