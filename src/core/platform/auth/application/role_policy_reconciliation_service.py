from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.contracts import (
    AuthPolicyReconciliationRepository,
    AuthSessionRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain import (
    AuthPolicyReconciliation,
    RolePermissionBinding,
    UserSessionContext,
)
from src.core.platform.auth.policy import (
    DEFAULT_ROLE_PERMISSIONS,
    SYSTEM_ROLE_POLICY_NAME,
    SYSTEM_ROLE_POLICY_VERSION,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass

from .session_utils import rotate_session_revision


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


class RolePolicyReconciliationService:
    def __init__(
        self,
        *,
        session: Session,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        user_role_repo: UserRoleRepository,
        user_repo: UserRepository,
        auth_session_repo: AuthSessionRepository,
        reconciliation_repo: AuthPolicyReconciliationRepository,
        user_session: UserSessionContext,
    ) -> None:
        self._session = session
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo
        self._user_role_repo = user_role_repo
        self._user_repo = user_repo
        self._auth_session_repo = auth_session_repo
        self._reconciliation_repo = reconciliation_repo
        self._user_session = user_session

    def preview(self) -> RolePolicyReconciliationPlan:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="preview system role policy reconciliation",
        )
        return self._build_plan(lock_policy_state=False)

    def apply(
        self,
        *,
        expected_version: int,
        expected_change_set_hash: str,
    ) -> RolePolicyReconciliationResult:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="apply system role policy reconciliation",
        )
        expected_hash = str(expected_change_set_hash or "").strip().lower()
        try:
            with self._session.begin_nested():
                plan = self._build_plan(lock_policy_state=True)
                if int(expected_version) != plan.current_version:
                    raise BusinessRuleError(
                        "Authorization policy version changed after review.",
                        code="ROLE_POLICY_VERSION_MISMATCH",
                    )
                if expected_hash != plan.change_set_hash:
                    raise BusinessRuleError(
                        "Authorization policy drift changed after review.",
                        code="ROLE_POLICY_CHANGE_SET_MISMATCH",
                    )
                if plan.missing_role_names or plan.missing_permission_codes:
                    raise BusinessRuleError(
                        "Managed role or permission definitions are missing.",
                        code="ROLE_POLICY_DEFINITION_MISSING",
                    )
                if plan.current_version > plan.target_version:
                    raise BusinessRuleError(
                        "Persisted authorization policy is newer than this application.",
                        code="ROLE_POLICY_VERSION_AHEAD",
                    )
                if plan.current_version == plan.target_version:
                    if plan.has_changes:
                        raise BusinessRuleError(
                            "Managed system-role bindings drifted after policy application.",
                            code="ROLE_POLICY_UNEXPECTED_DRIFT",
                        )
                    return RolePolicyReconciliationResult(
                        plan=plan,
                        applied=False,
                        revoked_session_count=0,
                    )

                role_map = {
                    role.name: role
                    for role in self._role_repo.list_all()
                    if (
                        role.is_system
                        and role.name in DEFAULT_ROLE_PERMISSIONS
                    )
                }
                permission_map = {
                    permission.code: permission
                    for permission in self._permission_repo.list_all()
                }
                for change in plan.removals:
                    self._role_permission_repo.delete(
                        role_map[change.role_name].id,
                        permission_map[change.permission_code].id,
                    )
                for change in plan.additions:
                    role = role_map[change.role_name]
                    permission = permission_map[change.permission_code]
                    self._role_permission_repo.add(
                        RolePermissionBinding.create(
                            role_id=role.id,
                            permission_id=permission.id,
                        )
                    )

                applied_at = datetime.now(timezone.utc)
                for role in role_map.values():
                    if not self._role_repo.set_policy_version(
                        role.id,
                        policy_version=plan.target_version,
                        updated_at=applied_at,
                    ):
                        raise BusinessRuleError(
                            "Managed system role changed during policy "
                            "reconciliation.",
                            code="ROLE_POLICY_CONCURRENT_ROLE_CHANGE",
                        )
                revoked_session_count = self._invalidate_affected_users(
                    plan.affected_user_ids,
                    revoked_at=applied_at,
                )
                self._reconciliation_repo.add(
                    AuthPolicyReconciliation(
                        id=generate_id(),
                        policy_name=plan.policy_name,
                        from_version=plan.current_version,
                        to_version=plan.target_version,
                        change_set_hash=plan.change_set_hash,
                        applied_at=applied_at,
                        applied_by_user_id=self._actor_user_id(),
                        rollback_json=plan.rollback_json,
                    )
                )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise BusinessRuleError(
                "Authorization policy was reconciled concurrently.",
                code="ROLE_POLICY_CONCURRENT_APPLY",
            ) from exc
        except Exception:
            self._session.rollback()
            raise

        for user_id in plan.affected_user_ids:
            domain_events.auth_changed.emit(user_id)
        return RolePolicyReconciliationResult(
            plan=plan,
            applied=True,
            revoked_session_count=revoked_session_count,
        )

    def _build_plan(
        self,
        *,
        lock_policy_state: bool,
    ) -> RolePolicyReconciliationPlan:
        latest = self._reconciliation_repo.get_latest(
            SYSTEM_ROLE_POLICY_NAME,
            for_update=lock_policy_state,
        )
        current_version = latest.to_version if latest is not None else 0
        roles = {
            role.name: role
            for role in self._role_repo.list_all()
            if role.is_system
        }
        permissions = {
            permission.code: permission
            for permission in self._permission_repo.list_all()
        }
        permission_codes_by_id = {
            permission.id: permission.code for permission in permissions.values()
        }
        missing_roles = tuple(
            sorted(set(DEFAULT_ROLE_PERMISSIONS).difference(roles))
        )
        expected_permission_codes = set().union(
            *DEFAULT_ROLE_PERMISSIONS.values()
        )
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

        affected_user_ids = tuple(
            sorted(
                {
                    user_id
                    for role_id in changed_role_ids
                    for user_id in self._user_role_repo.list_user_ids_for_role(
                        role_id
                    )
                }
            )
        )
        active_session_ids = tuple(
            sorted(self._active_session_ids(affected_user_ids))
        )
        change_payload = {
            "policy_name": SYSTEM_ROLE_POLICY_NAME,
            "from_version": current_version,
            "to_version": SYSTEM_ROLE_POLICY_VERSION,
            "additions": [
                [change.role_name, change.permission_code]
                for change in additions
            ],
            "removals": [
                [change.role_name, change.permission_code]
                for change in removals
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
        now = datetime.now(timezone.utc)
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

    def _invalidate_affected_users(
        self,
        user_ids: tuple[str, ...],
        *,
        revoked_at: datetime,
    ) -> int:
        revoked_session_count = 0
        for user_id in user_ids:
            user = self._user_repo.get(user_id)
            if user is None:
                continue
            rotate_session_revision(user)
            user.session_expires_at = revoked_at
            user.updated_at = revoked_at
            for auth_session in self._auth_session_repo.list_by_user(user.id):
                if auth_session.revoked_at is not None:
                    continue
                auth_session.revoked_at = revoked_at
                auth_session.updated_at = revoked_at
                self._auth_session_repo.update(auth_session)
                revoked_session_count += 1
            self._user_repo.update(user)
        return revoked_session_count

    def _actor_user_id(self) -> str:
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required for policy reconciliation.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal.user_id


__all__ = [
    "RolePermissionChange",
    "RolePolicyReconciliationPlan",
    "RolePolicyReconciliationResult",
    "RolePolicyReconciliationService",
]
