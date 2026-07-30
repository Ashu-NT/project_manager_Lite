from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.audit.contracts import AuditRepository
from src.core.platform.audit.domain import AuditEntry
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.contracts import (
    AuthSessionRepository,
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
)
from src.core.platform.auth.domain import (
    ROLE_SCOPE_TENANT,
    Permission,
    Role,
    RolePermissionBinding,
    UserSessionContext,
)
from src.core.platform.auth.policy import DEFAULT_ROLE_PERMISSIONS
from src.core.platform.auth.sod import SeparationOfDutiesPolicy
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.core.shared.events.domain_events import domain_events

from .role_scope_policy import is_platform_role


ROLE_MANAGE_PERMISSION = "auth.manage"
ROLE_ASSIGN_PERMISSION = "auth.role.assign"
RESERVED_CUSTOM_ROLE_NAMES = frozenset(DEFAULT_ROLE_PERMISSIONS)
CUSTOMER_CUSTOM_ROLE_PERMISSION_CODES = frozenset(
    permission_code
    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items()
    if not is_platform_role(role_name)
    for permission_code in permission_codes
)


class TenantRoleAdministrationService:
    """Tenant-scoped custom-role lifecycle with fail-closed policy controls."""

    def __init__(
        self,
        *,
        session: Session,
        role_repo: RoleRepository,
        role_binding_repo: RoleBindingRepository,
        role_permission_repo: RolePermissionRepository,
        permission_repo: PermissionRepository,
        auth_session_repo: AuthSessionRepository,
        tenant_repo: TenantRepository,
        membership_repo: UserTenantMembershipRepository,
        audit_repo: AuditRepository,
        user_session: UserSessionContext,
        tenant_context_service: TenantContextService,
        sod_policy: SeparationOfDutiesPolicy | None = None,
    ) -> None:
        self._session = session
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._role_permission_repo = role_permission_repo
        self._permission_repo = permission_repo
        self._auth_session_repo = auth_session_repo
        self._tenant_repo = tenant_repo
        self._membership_repo = membership_repo
        self._audit_repo = audit_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._sod_policy = sod_policy or SeparationOfDutiesPolicy()

    def list_custom_roles(self) -> list[Role]:
        _, tenant_id = self._require_role_administrator(
            operation_label="list tenant custom roles"
        )
        return [
            role
            for role in self._role_repo.list_for_tenant(
                tenant_id,
                include_system=False,
            )
            if role.status != "retired"
        ]

    def create_custom_role(
        self,
        *,
        name: str,
        display_name: str,
        description: str = "",
        permission_codes: Iterable[str] = (),
        is_assignable: bool = True,
    ) -> Role:
        actor, tenant_id = self._require_role_administrator(
            operation_label="create a tenant custom role"
        )
        role = Role.create(
            name=name,
            display_name=display_name,
            description=description,
            is_system=False,
            tenant_id=tenant_id,
            allowed_scope_type=ROLE_SCOPE_TENANT,
            is_assignable=is_assignable,
        )
        self._require_available_name(role.name, tenant_id=tenant_id)
        permissions = self._validate_permissions(permission_codes)

        try:
            self._role_repo.add(role)
            for permission in permissions.values():
                self._role_permission_repo.add(
                    RolePermissionBinding.create(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )
            self._record_audit(
                actor=actor,
                tenant_id=tenant_id,
                role=role,
                operation="create",
                action="auth.custom_role.created",
                metadata={
                    "permission_codes": sorted(permissions),
                    "policy_version": role.policy_version,
                    "is_assignable": role.is_assignable,
                },
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise BusinessRuleError(
                "A custom role with this name already exists in the tenant.",
                code="CUSTOM_ROLE_NAME_CONFLICT",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        return role

    def update_custom_role(
        self,
        role_id: str,
        *,
        expected_policy_version: int,
        display_name: str,
        description: str = "",
        permission_codes: Iterable[str] = (),
        is_assignable: bool = True,
    ) -> Role:
        actor, tenant_id = self._require_role_administrator(
            operation_label="update a tenant custom role"
        )
        current = self._require_custom_role(role_id, tenant_id=tenant_id)
        expected_version = self._normalize_expected_version(
            expected_policy_version
        )
        if current.policy_version != expected_version:
            raise ConcurrencyError(
                "The custom role was updated by another administrator.",
                code="CUSTOM_ROLE_STALE",
            )
        if current.status == "retired":
            raise BusinessRuleError(
                "Retired custom roles cannot be changed.",
                code="CUSTOM_ROLE_RETIRED",
            )

        permissions = self._validate_permissions(permission_codes)
        previous_codes = self._permission_codes(current.id)
        updated_codes = set(permissions)
        candidate = replace(
            current,
            display_name=display_name,
            description=description,
            is_assignable=bool(is_assignable),
            policy_version=current.policy_version + 1,
            updated_at=datetime.now(timezone.utc),
        )
        if (
            candidate.display_name == current.display_name
            and candidate.description == current.description
            and candidate.is_assignable == current.is_assignable
            and updated_codes == previous_codes
        ):
            return current

        affected_user_ids = (
            self._active_holder_ids(current.id, tenant_id=tenant_id)
            if updated_codes != previous_codes
            else set()
        )
        try:
            if not self._role_repo.update_custom(
                candidate,
                expected_policy_version=expected_version,
            ):
                raise ConcurrencyError(
                    "The custom role was updated by another administrator.",
                    code="CUSTOM_ROLE_STALE",
                )
            self._replace_permissions(
                current.id,
                current_codes=previous_codes,
                permissions=permissions,
            )
            revoked_session_count = self._revoke_tenant_sessions(
                affected_user_ids,
                tenant_id=tenant_id,
                revoked_at=candidate.updated_at,
            )
            self._record_audit(
                actor=actor,
                tenant_id=tenant_id,
                role=candidate,
                operation="permission_change",
                action="auth.custom_role.updated",
                metadata={
                    "previous_policy_version": current.policy_version,
                    "policy_version": candidate.policy_version,
                    "added_permission_codes": sorted(
                        updated_codes - previous_codes
                    ),
                    "removed_permission_codes": sorted(
                        previous_codes - updated_codes
                    ),
                    "is_assignable": candidate.is_assignable,
                    "revoked_session_count": revoked_session_count,
                },
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        for user_id in affected_user_ids:
            domain_events.auth_changed.emit(user_id)
        return candidate

    def retire_custom_role(
        self,
        role_id: str,
        *,
        expected_policy_version: int,
    ) -> Role:
        actor, tenant_id = self._require_role_administrator(
            operation_label="retire a tenant custom role"
        )
        current = self._require_custom_role(role_id, tenant_id=tenant_id)
        expected_version = self._normalize_expected_version(
            expected_policy_version
        )
        if current.policy_version != expected_version:
            raise ConcurrencyError(
                "The custom role was updated by another administrator.",
                code="CUSTOM_ROLE_STALE",
            )
        if current.status == "retired":
            return current

        retired_at = datetime.now(timezone.utc)
        retired = replace(
            current,
            status="retired",
            is_assignable=False,
            policy_version=current.policy_version + 1,
            updated_at=retired_at,
        )
        affected_user_ids = self._active_holder_ids(
            current.id,
            tenant_id=tenant_id,
        )
        try:
            if not self._role_repo.update_custom(
                retired,
                expected_policy_version=expected_version,
            ):
                raise ConcurrencyError(
                    "The custom role was updated by another administrator.",
                    code="CUSTOM_ROLE_STALE",
                )
            revoked_binding_count = (
                self._role_binding_repo.revoke_active_for_role(
                    current.id,
                    tenant_id,
                    revoked_at=retired_at,
                )
            )
            revoked_session_count = self._revoke_tenant_sessions(
                affected_user_ids,
                tenant_id=tenant_id,
                revoked_at=retired_at,
            )
            self._record_audit(
                actor=actor,
                tenant_id=tenant_id,
                role=retired,
                operation="delete",
                action="auth.custom_role.retired",
                metadata={
                    "previous_policy_version": current.policy_version,
                    "policy_version": retired.policy_version,
                    "revoked_binding_count": revoked_binding_count,
                    "revoked_session_count": revoked_session_count,
                },
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        for user_id in affected_user_ids:
            domain_events.auth_changed.emit(user_id)
        return retired

    def _require_role_administrator(self, *, operation_label: str):
        require_permission(
            self._user_session,
            ROLE_MANAGE_PERMISSION,
            operation_label=operation_label,
        )
        require_permission(
            self._user_session,
            ROLE_ASSIGN_PERMISSION,
            operation_label=operation_label,
        )
        actor = self._user_session.principal
        if actor is None:
            raise BusinessRuleError(
                "Authentication is required for custom-role administration.",
                code="AUTHENTICATION_REQUIRED",
            )
        if "platform.admin" in actor.permissions:
            raise BusinessRuleError(
                "Platform operators cannot administer customer roles without "
                "a governed support context.",
                code="PLATFORM_CUSTOMER_OPERATION_DENIED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label
        )
        tenant = self._tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Custom roles require an active tenant.",
                code="TENANT_INACTIVE",
            )
        if not self._membership_repo.is_active_member(
            actor.user_id,
            tenant_id,
        ):
            raise BusinessRuleError(
                "Active tenant membership is required for custom-role "
                "administration.",
                code="TENANT_ACCESS_DENIED",
            )
        self._require_tenant_administration_scope(
            actor.user_id,
            tenant_id=tenant_id,
        )
        return actor, tenant_id

    def _require_tenant_administration_scope(
        self,
        actor_user_id: str,
        *,
        tenant_id: str,
    ) -> None:
        required_permissions = {
            ROLE_MANAGE_PERMISSION,
            ROLE_ASSIGN_PERMISSION,
        }
        for binding in self._role_binding_repo.list_active_for_principal(
            actor_user_id,
            tenant_id=tenant_id,
        ):
            if (
                binding.actual_scope_type == ROLE_SCOPE_TENANT
                and binding.actual_scope_id is None
                and required_permissions.issubset(
                    self._permission_codes(binding.role_id)
                )
            ):
                return
        raise BusinessRuleError(
            "A canonical tenant-scope administrative role is required for "
            "custom-role administration.",
            code="CUSTOM_ROLE_TENANT_SCOPE_REQUIRED",
        )

    def _require_available_name(self, role_name: str, *, tenant_id: str) -> None:
        if role_name in RESERVED_CUSTOM_ROLE_NAMES:
            raise BusinessRuleError(
                "Custom role names cannot impersonate managed system roles.",
                code="CUSTOM_ROLE_NAME_RESERVED",
            )
        if (
            self._role_repo.get_for_tenant_by_name(
                tenant_id,
                role_name,
                include_system=False,
            )
            is not None
        ):
            raise BusinessRuleError(
                "A custom role with this name already exists in the tenant.",
                code="CUSTOM_ROLE_NAME_CONFLICT",
            )

    def _require_custom_role(self, role_id: str, *, tenant_id: str) -> Role:
        role = self._role_repo.get(str(role_id or "").strip())
        if (
            role is None
            or role.is_system
            or role.tenant_id != tenant_id
            or role.allowed_scope_type != ROLE_SCOPE_TENANT
        ):
            raise NotFoundError(
                "Custom role not found.",
                code="CUSTOM_ROLE_NOT_FOUND",
            )
        return role

    def _validate_permissions(
        self,
        permission_codes: Iterable[str],
    ) -> dict[str, Permission]:
        normalized_codes = {
            str(permission_code or "").strip().lower()
            for permission_code in (permission_codes or ())
            if str(permission_code or "").strip()
        }
        permission_map = {
            permission.code: permission
            for permission in self._permission_repo.list_all()
        }
        unknown_codes = normalized_codes.difference(permission_map)
        if unknown_codes:
            raise ValidationError(
                "Unknown custom-role permission codes: "
                + ", ".join(sorted(unknown_codes)),
                code="CUSTOM_ROLE_PERMISSION_UNKNOWN",
            )
        denied_codes = normalized_codes.difference(
            CUSTOMER_CUSTOM_ROLE_PERMISSION_CODES
        )
        if denied_codes:
            raise BusinessRuleError(
                "Custom roles cannot receive platform permission codes: "
                + ", ".join(sorted(denied_codes)),
                code="CUSTOM_ROLE_PERMISSION_DENIED",
            )
        conflicts = self._sod_policy.find_conflicts(normalized_codes)
        if conflicts:
            raise ValidationError(
                f"Custom role violates separation of duties. {conflicts[0]}",
                code="CUSTOM_ROLE_PERMISSION_CONFLICT",
            )
        return {
            code: permission_map[code]
            for code in sorted(normalized_codes)
        }

    def _permission_codes(self, role_id: str) -> set[str]:
        codes_by_id = {
            permission.id: permission.code
            for permission in self._permission_repo.list_all()
        }
        return {
            codes_by_id[permission_id]
            for permission_id in self._role_permission_repo.list_permission_ids(
                role_id
            )
            if permission_id in codes_by_id
        }

    def _replace_permissions(
        self,
        role_id: str,
        *,
        current_codes: set[str],
        permissions: dict[str, Permission],
    ) -> None:
        permission_by_code = {
            permission.code: permission
            for permission in self._permission_repo.list_all()
        }
        updated_codes = set(permissions)
        for code in current_codes - updated_codes:
            self._role_permission_repo.delete(
                role_id,
                permission_by_code[code].id,
            )
        for code in updated_codes - current_codes:
            self._role_permission_repo.add(
                RolePermissionBinding.create(
                    role_id=role_id,
                    permission_id=permissions[code].id,
                )
            )

    def _active_holder_ids(self, role_id: str, *, tenant_id: str) -> set[str]:
        return {
            binding.principal_id
            for binding in self._role_binding_repo.list_active_for_role(
                role_id,
                tenant_id=tenant_id,
            )
        }

    def _revoke_tenant_sessions(
        self,
        user_ids: set[str],
        *,
        tenant_id: str,
        revoked_at: datetime,
    ) -> int:
        revoked_count = 0
        for user_id in user_ids:
            for auth_session in self._auth_session_repo.list_by_user(user_id):
                if (
                    auth_session.revoked_at is not None
                    or auth_session.last_active_tenant_id != tenant_id
                ):
                    continue
                auth_session.revoked_at = revoked_at
                auth_session.updated_at = revoked_at
                self._auth_session_repo.update(auth_session)
                revoked_count += 1
        return revoked_count

    @staticmethod
    def _normalize_expected_version(value: int) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Expected role policy version must be a positive integer.",
                code="CUSTOM_ROLE_POLICY_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Expected role policy version must be a positive integer.",
                code="CUSTOM_ROLE_POLICY_VERSION_INVALID",
            )
        return normalized

    def _record_audit(
        self,
        *,
        actor,
        tenant_id: str,
        role: Role,
        operation: str,
        action: str,
        metadata: dict[str, object],
    ) -> None:
        self._audit_repo.add_for_tenant(
            AuditEntry.create(
                operation=operation,
                entity_type="custom_role",
                entity_id=role.id,
                entity_parent_id=tenant_id,
                module="platform",
                actor_id=actor.user_id,
                actor_username=actor.username,
                tenant_id=tenant_id,
                severity="high",
                compliance_tag="SOC2",
                metadata={
                    "action": action,
                    "role_name": role.name,
                    "display_name": role.display_name,
                    **metadata,
                },
            ),
            tenant_id,
        )


__all__ = [
    "CUSTOMER_CUSTOM_ROLE_PERMISSION_CODES",
    "RESERVED_CUSTOM_ROLE_NAMES",
    "ROLE_ASSIGN_PERMISSION",
    "ROLE_MANAGE_PERMISSION",
    "TenantRoleAdministrationService",
]
