from __future__ import annotations

from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass(frozen=True)
class RolePermissionChange:
    role_name: str
    permission_code: str


@validated_dataclass(frozen=True)
class RolePolicyReconciliationPlan:
    policy_name: str
    current_version: int
    target_version: int
    additions: tuple[RolePermissionChange, ...]
    removals: tuple[RolePermissionChange, ...]
    affected_user_ids: tuple[str, ...]
    active_session_ids: tuple[str, ...]
    missing_role_names: tuple[str, ...]
    missing_permission_codes: tuple[str, ...]
    change_set_hash: str
    rollback_json: str

    @property
    def has_changes(self) -> bool:
        return bool(self.additions or self.removals)


@validated_dataclass(frozen=True)
class RolePolicyReconciliationResult:
    plan: RolePolicyReconciliationPlan
    applied: bool
    revoked_session_count: int
