from __future__ import annotations

from src.core.platform.auth.domain import (
    AuthorizationMigrationBatch,
    AuthSession,
    LegacyRoleBindingMigrationRecord,
    Permission,
    Role,
    RoleBinding,
    RoleDelegationPolicy,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
)
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.infrastructure.persistence.orm.auth import (
    AuthorizationMigrationBatchORM,
    AuthSessionORM,
    LegacyRoleBindingMigrationRecordORM,
    PermissionORM,
    RoleBindingORM,
    RoleDelegationPolicyORM,
    RoleORM,
    RolePermissionORM,
    UserORM,
    UserRoleORM,
)


def user_to_orm(user: UserAccount) -> UserORM:
    return UserORM(
        id=user.id,
        username=user.username,
        password_hash=user.password_hash,
        display_name=user.display_name,
        email=user.email,
        identity_provider=getattr(user, "identity_provider", None),
        federated_subject=getattr(user, "federated_subject", None),
        mfa_secret=getattr(user, "mfa_secret", None),
        mfa_enabled=getattr(user, "mfa_enabled", False),
        session_timeout_minutes_override=getattr(user, "session_timeout_minutes_override", None),
        session_revision=getattr(user, "session_revision", 1),
        last_login_auth_method=getattr(user, "last_login_auth_method", None),
        last_login_device_label=getattr(user, "last_login_device_label", None),
        is_active=user.is_active,
        failed_login_attempts=getattr(user, "failed_login_attempts", 0),
        locked_until=getattr(user, "locked_until", None),
        last_login_at=getattr(user, "last_login_at", None),
        session_expires_at=getattr(user, "session_expires_at", None),
        password_changed_at=getattr(user, "password_changed_at", None),
        must_change_password=getattr(user, "must_change_password", False),
        created_at=user.created_at,
        updated_at=user.updated_at,
        version=getattr(user, "version", 1),
    )


def user_from_orm(obj: UserORM) -> UserAccount:
    return UserAccount(
        id=obj.id,
        username=obj.username,
        password_hash=obj.password_hash,
        display_name=obj.display_name,
        email=obj.email,
        identity_provider=getattr(obj, "identity_provider", None),
        federated_subject=getattr(obj, "federated_subject", None),
        mfa_secret=getattr(obj, "mfa_secret", None),
        mfa_enabled=getattr(obj, "mfa_enabled", False),
        session_timeout_minutes_override=getattr(obj, "session_timeout_minutes_override", None),
        session_revision=getattr(obj, "session_revision", 1),
        last_login_auth_method=getattr(obj, "last_login_auth_method", None),
        last_login_device_label=getattr(obj, "last_login_device_label", None),
        is_active=obj.is_active,
        failed_login_attempts=getattr(obj, "failed_login_attempts", 0),
        locked_until=ensure_utc_datetime(getattr(obj, "locked_until", None)),
        last_login_at=ensure_utc_datetime(getattr(obj, "last_login_at", None)),
        session_expires_at=ensure_utc_datetime(getattr(obj, "session_expires_at", None)),
        password_changed_at=ensure_utc_datetime(getattr(obj, "password_changed_at", None)),
        must_change_password=getattr(obj, "must_change_password", False),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
        version=getattr(obj, "version", 1),
    )


def auth_session_to_orm(auth_session: AuthSession) -> AuthSessionORM:
    return AuthSessionORM(
        id=auth_session.id,
        user_id=auth_session.user_id,
        session_revision=auth_session.session_revision,
        auth_method=auth_session.auth_method,
        device_label=auth_session.device_label,
        last_active_tenant_id=getattr(auth_session, "last_active_tenant_id", None),
        last_active_organization_id=getattr(auth_session, "last_active_organization_id", None),
        issued_at=auth_session.issued_at,
        expires_at=auth_session.expires_at,
        last_validated_at=auth_session.last_validated_at,
        revoked_at=auth_session.revoked_at,
        created_at=auth_session.created_at,
        updated_at=auth_session.updated_at,
    )


def auth_session_from_orm(obj: AuthSessionORM) -> AuthSession:
    return AuthSession(
        id=obj.id,
        user_id=obj.user_id,
        session_revision=obj.session_revision,
        auth_method=obj.auth_method,
        device_label=obj.device_label,
        last_active_tenant_id=getattr(obj, "last_active_tenant_id", None),
        last_active_organization_id=getattr(obj, "last_active_organization_id", None),
        issued_at=ensure_utc_datetime(obj.issued_at),
        expires_at=ensure_utc_datetime(obj.expires_at),
        last_validated_at=ensure_utc_datetime(obj.last_validated_at),
        revoked_at=ensure_utc_datetime(obj.revoked_at),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
    )


def role_to_orm(role: Role) -> RoleORM:
    return RoleORM(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        tenant_id=role.tenant_id,
        display_name=role.display_name,
        allowed_scope_type=role.allowed_scope_type,
        is_assignable=role.is_assignable,
        status=role.status,
        policy_version=role.policy_version,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def role_from_orm(obj: RoleORM) -> Role:
    return Role(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        is_system=obj.is_system,
        tenant_id=obj.tenant_id,
        display_name=obj.display_name,
        allowed_scope_type=obj.allowed_scope_type,
        is_assignable=obj.is_assignable,
        status=obj.status,
        policy_version=obj.policy_version,
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
    )


def role_binding_to_orm(binding: RoleBinding) -> RoleBindingORM:
    return RoleBindingORM(
        id=binding.id,
        principal_type=binding.principal_type,
        principal_id=binding.principal_id,
        role_id=binding.role_id,
        tenant_id=binding.tenant_id,
        actual_scope_type=binding.actual_scope_type,
        actual_scope_id=binding.actual_scope_id,
        assigned_by=binding.assigned_by,
        assigned_at=binding.assigned_at,
        expires_at=binding.expires_at,
        revoked_at=binding.revoked_at,
        version=binding.version,
    )


def role_binding_from_orm(obj: RoleBindingORM) -> RoleBinding:
    return RoleBinding(
        id=obj.id,
        principal_type=obj.principal_type,
        principal_id=obj.principal_id,
        role_id=obj.role_id,
        tenant_id=obj.tenant_id,
        actual_scope_type=obj.actual_scope_type,
        actual_scope_id=obj.actual_scope_id,
        assigned_by=obj.assigned_by,
        assigned_at=ensure_utc_datetime(obj.assigned_at),
        expires_at=ensure_utc_datetime(obj.expires_at),
        revoked_at=ensure_utc_datetime(obj.revoked_at),
        version=obj.version,
    )


# RBAC-TRANSITION-ONLY: Remove these migration-state mappers at decommission.
def authorization_migration_batch_to_orm(
    batch: AuthorizationMigrationBatch,
) -> AuthorizationMigrationBatchORM:
    return AuthorizationMigrationBatchORM(
        id=batch.id,
        source_inventory_sha256=batch.source_inventory_sha256,
        source_record_count=batch.source_record_count,
        reviewed_plan_sha256=batch.reviewed_plan_sha256,
        reviewer_id=batch.reviewer_id,
        reviewed_at=batch.reviewed_at,
        status=batch.status,
        created_by=batch.created_by,
        created_at=batch.created_at,
        applied_at=batch.applied_at,
        rolled_back_at=batch.rolled_back_at,
        version=batch.version,
    )


def authorization_migration_batch_from_orm(
    obj: AuthorizationMigrationBatchORM,
) -> AuthorizationMigrationBatch:
    return AuthorizationMigrationBatch(
        id=obj.id,
        source_inventory_sha256=obj.source_inventory_sha256,
        source_record_count=obj.source_record_count,
        reviewed_plan_sha256=obj.reviewed_plan_sha256,
        reviewer_id=obj.reviewer_id,
        reviewed_at=ensure_utc_datetime(obj.reviewed_at),
        status=obj.status,
        created_by=obj.created_by,
        created_at=ensure_utc_datetime(obj.created_at),
        applied_at=ensure_utc_datetime(obj.applied_at),
        rolled_back_at=ensure_utc_datetime(obj.rolled_back_at),
        version=obj.version,
    )


def legacy_role_binding_migration_record_to_orm(
    record: LegacyRoleBindingMigrationRecord,
) -> LegacyRoleBindingMigrationRecordORM:
    return LegacyRoleBindingMigrationRecordORM(
        id=record.id,
        batch_id=record.batch_id,
        legacy_binding_id=record.legacy_binding_id,
        source_user_id=record.source_user_id,
        source_role_id=record.source_role_id,
        source_organization_id=record.source_organization_id,
        source_snapshot_sha256=record.source_snapshot_sha256,
        status=record.status,
        quarantine_reason_code=record.quarantine_reason_code,
        resolved_tenant_id=record.resolved_tenant_id,
        resolved_scope_type=record.resolved_scope_type,
        resolved_scope_id=record.resolved_scope_id,
        canonical_binding_id=record.canonical_binding_id,
        reviewed_by=record.reviewed_by,
        reviewed_at=record.reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        version=record.version,
    )


def legacy_role_binding_migration_record_from_orm(
    obj: LegacyRoleBindingMigrationRecordORM,
) -> LegacyRoleBindingMigrationRecord:
    return LegacyRoleBindingMigrationRecord(
        id=obj.id,
        batch_id=obj.batch_id,
        legacy_binding_id=obj.legacy_binding_id,
        source_user_id=obj.source_user_id,
        source_role_id=obj.source_role_id,
        source_organization_id=obj.source_organization_id,
        source_snapshot_sha256=obj.source_snapshot_sha256,
        status=obj.status,
        quarantine_reason_code=obj.quarantine_reason_code,
        resolved_tenant_id=obj.resolved_tenant_id,
        resolved_scope_type=obj.resolved_scope_type,
        resolved_scope_id=obj.resolved_scope_id,
        canonical_binding_id=obj.canonical_binding_id,
        reviewed_by=obj.reviewed_by,
        reviewed_at=ensure_utc_datetime(obj.reviewed_at),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
        version=obj.version,
    )


def role_delegation_policy_to_orm(
    policy: RoleDelegationPolicy,
) -> RoleDelegationPolicyORM:
    return RoleDelegationPolicyORM(
        id=policy.id,
        tenant_id=policy.tenant_id,
        actor_role_id=policy.actor_role_id,
        assignable_role_id=policy.assignable_role_id,
        target_scope_type=policy.target_scope_type,
        assignable_role_policy_version=policy.assignable_role_policy_version,
        assignable_permission_set_hash=policy.assignable_permission_set_hash,
        created_by=policy.created_by,
        created_at=policy.created_at,
        revoked_at=policy.revoked_at,
    )


def role_delegation_policy_from_orm(
    obj: RoleDelegationPolicyORM,
) -> RoleDelegationPolicy:
    return RoleDelegationPolicy(
        id=obj.id,
        tenant_id=obj.tenant_id,
        actor_role_id=obj.actor_role_id,
        assignable_role_id=obj.assignable_role_id,
        target_scope_type=obj.target_scope_type,
        assignable_role_policy_version=obj.assignable_role_policy_version,
        assignable_permission_set_hash=obj.assignable_permission_set_hash,
        created_by=obj.created_by,
        created_at=ensure_utc_datetime(obj.created_at),
        revoked_at=ensure_utc_datetime(obj.revoked_at),
    )


def permission_to_orm(permission: Permission) -> PermissionORM:
    return PermissionORM(
        id=permission.id,
        code=permission.code,
        description=permission.description,
    )


def permission_from_orm(obj: PermissionORM) -> Permission:
    return Permission(
        id=obj.id,
        code=obj.code,
        description=obj.description,
    )


def user_role_to_orm(binding: UserRoleBinding) -> UserRoleORM:
    # RBAC-TRANSITION-ONLY: Remove with the legacy user_roles adapter.
    return UserRoleORM(
        id=binding.id,
        user_id=binding.user_id,
        role_id=binding.role_id,
        organization_id=binding.organization_id,
    )


def user_role_from_orm(obj: UserRoleORM) -> UserRoleBinding:
    return UserRoleBinding(
        id=obj.id,
        user_id=obj.user_id,
        role_id=obj.role_id,
        organization_id=getattr(obj, "organization_id", None),
    )


def role_permission_to_orm(binding: RolePermissionBinding) -> RolePermissionORM:
    return RolePermissionORM(
        id=binding.id,
        role_id=binding.role_id,
        permission_id=binding.permission_id,
    )


def role_permission_from_orm(obj: RolePermissionORM) -> RolePermissionBinding:
    return RolePermissionBinding(
        id=obj.id,
        role_id=obj.role_id,
        permission_id=obj.permission_id,
    )


__all__ = [
    "authorization_migration_batch_from_orm",
    "authorization_migration_batch_to_orm",
    "auth_session_from_orm",
    "auth_session_to_orm",
    "legacy_role_binding_migration_record_from_orm",
    "legacy_role_binding_migration_record_to_orm",
    "user_to_orm",
    "user_from_orm",
    "role_to_orm",
    "role_from_orm",
    "role_binding_to_orm",
    "role_binding_from_orm",
    "role_delegation_policy_to_orm",
    "role_delegation_policy_from_orm",
    "permission_to_orm",
    "permission_from_orm",
    "user_role_to_orm",
    "user_role_from_orm",
    "role_permission_to_orm",
    "role_permission_from_orm",
]
