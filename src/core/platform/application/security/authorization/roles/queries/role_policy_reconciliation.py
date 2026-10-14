from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.security.authorization.roles.dto import (
    RolePermissionChange,
    RolePolicyReconciliationPlan,
)
from src.core.platform.contract.repositories.security.auth import (
    AuthPolicyReconciliationRepository,
    AuthSessionRepository,
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
)
from src.core.platform.domain.security.auth import (
    UserSessionContext,
)
from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
    SYSTEM_ROLE_POLICY_NAME,
    SYSTEM_ROLE_POLICY_VERSION,
)


class RolePolicyReconciliationQueryHandler:
    """Authorized policy previews and transaction-neutral plan construction."""

    def __init__(
        self,
        *,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        auth_session_repo: AuthSessionRepository,
        reconciliation_repo: AuthPolicyReconciliationRepository,
        user_session: UserSessionContext,
        role_binding_repo: RoleBindingRepository,
    ) -> None:
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo
        self._auth_session_repo = auth_session_repo
        self._reconciliation_repo = reconciliation_repo
        self._user_session = user_session
        self._role_binding_repo = role_binding_repo

    def preview(self) -> RolePolicyReconciliationPlan:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="preview system role policy reconciliation",
        )
        return self.build_plan(lock_policy_state=False)

    def build_plan(
        self,
        *,
        lock_policy_state: bool,
    ) -> RolePolicyReconciliationPlan:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="build system role policy reconciliation plan",
        )
        latest = self._reconciliation_repo.get_latest(
            SYSTEM_ROLE_POLICY_NAME,
            for_update=lock_policy_state,
        )
        current_version = latest.to_version if latest is not None else 0
        roles = {
            role.name: role for role in self._role_repo.list_all() if role.is_system
        }
        permissions = {
            permission.code: permission
            for permission in self._permission_repo.list_all()
        }
        permission_codes_by_id = {
            permission.id: permission.code for permission in permissions.values()
        }
        missing_roles = tuple(sorted(set(DEFAULT_ROLE_PERMISSIONS).difference(roles)))
        expected_permission_codes = set().union(*DEFAULT_ROLE_PERMISSIONS.values())
        missing_permissions = tuple(
            sorted(expected_permission_codes.difference(permissions))
        )

        additions: list[RolePermissionChange] = []
        removals: list[RolePermissionChange] = []
        changed_role_ids: set[str] = set()
        for role_name, expected_codes in sorted(DEFAULT_ROLE_PERMISSIONS.items()):
            role = roles.get(role_name)
            if role is None:
                continue
            actual_codes = {
                permission_codes_by_id[permission_id]
                for permission_id in self._role_permission_repo.list_permission_ids(
                    role.id
                )
                if permission_id in permission_codes_by_id
            }
            for code in sorted(expected_codes.difference(actual_codes)):
                additions.append(RolePermissionChange(role_name, code))
                changed_role_ids.add(role.id)
            for code in sorted(actual_codes.difference(expected_codes)):
                removals.append(RolePermissionChange(role_name, code))
                changed_role_ids.add(role.id)

        affected_users: set[str] = set()
        for role_id in changed_role_ids:
            role = self._role_repo.get(role_id)
            if role is not None and role.allowed_scope_type == "platform":
                affected_users.update(
                    binding.principal_id
                    for binding in self._role_binding_repo.list_active_for_role(
                        role_id,
                        tenant_id=None,
                    )
                )
            elif role is not None:
                affected_users.update(
                    binding.principal_id
                    for binding in (
                        self._role_binding_repo.list_active_for_role_across_tenants(
                            role_id
                        )
                    )
                )
        affected_user_ids = tuple(sorted(affected_users))
        active_session_ids = tuple(sorted(self._active_session_ids(affected_user_ids)))
        change_payload = {
            "policy_name": SYSTEM_ROLE_POLICY_NAME,
            "from_version": current_version,
            "to_version": SYSTEM_ROLE_POLICY_VERSION,
            "additions": [
                [change.role_name, change.permission_code] for change in additions
            ],
            "removals": [
                [change.role_name, change.permission_code] for change in removals
            ],
            "missing_roles": list(missing_roles),
            "missing_permissions": list(missing_permissions),
        }
        canonical_change_set = json.dumps(
            change_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        change_set_hash = hashlib.sha256(
            canonical_change_set.encode("utf-8")
        ).hexdigest()
        rollback_json = json.dumps(
            {
                "policy_name": SYSTEM_ROLE_POLICY_NAME,
                "from_version": SYSTEM_ROLE_POLICY_VERSION,
                "to_version": current_version,
                "additions": change_payload["removals"],
                "removals": change_payload["additions"],
                "forward_change_set_hash": change_set_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return RolePolicyReconciliationPlan(
            policy_name=SYSTEM_ROLE_POLICY_NAME,
            current_version=current_version,
            target_version=SYSTEM_ROLE_POLICY_VERSION,
            additions=tuple(additions),
            removals=tuple(removals),
            affected_user_ids=affected_user_ids,
            active_session_ids=active_session_ids,
            missing_role_names=missing_roles,
            missing_permission_codes=missing_permissions,
            change_set_hash=change_set_hash,
            rollback_json=rollback_json,
        )

    def _active_session_ids(self, user_ids: tuple[str, ...]) -> set[str]:
        now = datetime.now(UTC)
        active_ids: set[str] = set()
        for user_id in user_ids:
            for auth_session in self._auth_session_repo.list_by_user(user_id):
                expires_at = ensure_utc_datetime(auth_session.expires_at)
                if (
                    auth_session.revoked_at is None
                    and expires_at is not None
                    and expires_at > now
                ):
                    active_ids.add(auth_session.id)
        return active_ids
