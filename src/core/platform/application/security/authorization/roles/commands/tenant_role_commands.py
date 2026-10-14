from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.roles.role_binding_mutation_participant import (
    revoke_role_binding_using,
)
from src.core.platform.application.security.authorization.roles.tenant_role_authorization import (
    RESERVED_CUSTOM_ROLE_NAMES,
    TenantRoleAuthorization,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.contract.repositories.security.auth import (
    AuthSessionRepository,
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    RoleRepository,
)
from src.core.platform.contract.uow.security.auth_unit_of_work import (
    AuthUnitOfWorkFactory,
)
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.auth import (
    Permission,
    Role,
    RolePermissionBinding,
)
from src.core.platform.domain.security.auth.events import (
    CustomRoleCreated,
    CustomRoleRetired,
    CustomRoleUpdated,
)
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_TENANT,
    RoleBindingTenantScope,
)
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.core.shared.time.clock import Clock


class TenantRoleCommandHandler:
    """Tenant-scoped custom-role lifecycle with fail-closed policy controls."""

    def __init__(
        self,
        *,
        session: Session,
        authorization: TenantRoleAuthorization,
        role_repo: RoleRepository,
        role_binding_repo: RoleBindingRepository,
        role_permission_repo: RolePermissionRepository,
        permission_repo: PermissionRepository,
        auth_session_repo: AuthSessionRepository,
        audit_repo: AuditRepository,
        transactional_dispatcher: TransactionalEventDispatcher | None,
        post_commit_bus: PostCommitEventPublisher | None,
        clock: Clock,
        uow_factory: AuthUnitOfWorkFactory,
    ) -> None:
        self._session = session
        self._authorization = authorization
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._role_permission_repo = role_permission_repo
        self._permission_repo = permission_repo
        self._auth_session_repo = auth_session_repo
        self._audit_repo = audit_repo
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self._clock = clock
        self._uow_factory = uow_factory

    def _uow(self):
        return self._uow_factory.create(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
        )

    def create_custom_role(
        self,
        *,
        name: str,
        display_name: str,
        description: str = "",
        permission_codes: Iterable[str] = (),
        is_assignable: bool = True,
    ) -> Role:
        actor, tenant_id = self._authorization.require_role_administrator(
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
        permissions = self._authorization.validate_permissions(permission_codes)

        try:
            with self._uow() as uow:
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
                uow.record_event(
                    CustomRoleCreated(
                        role_id=role.id,
                        tenant_id=tenant_id,
                        policy_version=role.policy_version,
                        occurred_at=datetime.now(UTC),
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "A custom role with this name already exists in the tenant.",
                code="CUSTOM_ROLE_NAME_CONFLICT",
            ) from exc
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
        actor, tenant_id = self._authorization.require_role_administrator(
            operation_label="update a tenant custom role"
        )
        current = self._require_custom_role(role_id, tenant_id=tenant_id)
        expected_version = self._normalize_expected_version(expected_policy_version)
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

        permissions = self._authorization.validate_permissions(permission_codes)
        previous_codes = self._authorization.permission_codes(current.id)
        updated_codes = set(permissions)
        updated_at = datetime.now(UTC)
        candidate = replace(
            current,
            display_name=display_name,
            description=description,
            is_assignable=bool(is_assignable),
            policy_version=current.policy_version + 1,
            updated_at=updated_at,
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
        with self._uow() as uow:
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
                revoked_at=updated_at,
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
                    "added_permission_codes": sorted(updated_codes - previous_codes),
                    "removed_permission_codes": sorted(previous_codes - updated_codes),
                    "is_assignable": candidate.is_assignable,
                    "revoked_session_count": revoked_session_count,
                },
            )
            uow.record_event(
                CustomRoleUpdated(
                    role_id=candidate.id,
                    tenant_id=tenant_id,
                    policy_version=candidate.policy_version,
                    occurred_at=updated_at,
                )
            )
            uow.commit()
        return candidate

    def retire_custom_role(
        self,
        role_id: str,
        *,
        expected_policy_version: int,
    ) -> Role:
        actor, tenant_id = self._authorization.require_role_administrator(
            operation_label="retire a tenant custom role"
        )
        current = self._require_custom_role(role_id, tenant_id=tenant_id)
        expected_version = self._normalize_expected_version(expected_policy_version)
        if current.policy_version != expected_version:
            raise ConcurrencyError(
                "The custom role was updated by another administrator.",
                code="CUSTOM_ROLE_STALE",
            )
        if current.status == "retired":
            return current

        retired_at = datetime.now(UTC)
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
        with self._uow() as uow:
            if not self._role_repo.update_custom(
                retired,
                expected_policy_version=expected_version,
            ):
                raise ConcurrencyError(
                    "The custom role was updated by another administrator.",
                    code="CUSTOM_ROLE_STALE",
                )
            # Replaces the prior direct bulk-SQL `revoke_active_for_role` bypass (which updated
            # rows with only a bulk count in the audit metadata, no per-binding audit/event
            # evidence at all) with the same canonical, transaction-neutral per-binding function
            # `RoleGovernanceCommandHandler.revoke_role_binding` and `TenantMembershipLifecycleCommandHandler`'s own
            # cascade already use -- one real `RoleBindingRevoked` fact per binding actually
            # revoked, not a fabricated bulk event.
            active_bindings = self._role_binding_repo.list_active_for_role(
                current.id,
                tenant_id=tenant_id,
            )
            for binding in active_bindings:
                revoke_role_binding_using(
                    role_bindings_repo=self._role_binding_repo,
                    audit_repo=self._audit_repo,
                    clock=self._clock,
                    record_event=uow.record_event,
                    binding=binding,
                    domain_scope=RoleBindingTenantScope(tenant_id=tenant_id),
                    actor=actor,
                    audit_action="auth.custom_role.binding_revoked",
                    audit_metadata_extra={"role_retirement": True},
                )
            revoked_binding_count = len(active_bindings)
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
            uow.record_event(
                CustomRoleRetired(
                    role_id=retired.id,
                    tenant_id=tenant_id,
                    policy_version=retired.policy_version,
                    occurred_at=retired_at,
                )
            )
            uow.commit()
        return retired

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
                category="SECURITY",
                metadata={
                    "action": action,
                    "role_name": role.name,
                    "display_name": role.display_name,
                    **metadata,
                },
            ),
            tenant_id,
        )
