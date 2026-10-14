from __future__ import annotations

from src.core.platform.application.tenant.tenancy.membership_support import (
    TenantMembershipSupport,
)
from src.core.platform.contract.uow.tenancy.tenant_membership_unit_of_work import (
    TenantMembershipUnitOfWorkFactory,
)
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_SUSPENDED,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
    UserTenantMembership,
)
from src.core.shared.time.clock import Clock


class TenantMembershipLifecycleCommandHandler:
    """Suspend, reactivate and remove members without changing user/employee identity."""

    def __init__(
        self,
        *,
        uow_factory: TenantMembershipUnitOfWorkFactory,
        support: TenantMembershipSupport,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._support = support
        self._clock = clock

    def suspend_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            actor, tenant_id = self._support.require_tenant_administrator(
                uow, operation_label="suspend a tenant member"
            )
            target = self._support.require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="suspend",
            )
            membership = self._support.require_membership(
                uow.memberships, target.id, tenant_id
            )
            self._support.guard_last_tenant_administrator(
                uow.memberships, uow.role_bindings, uow.roles, target.id, tenant_id
            )
            now = self._clock.now()
            suspended = membership.suspend(suspended_at=now)
            invalidated_sessions = self._support.revoke_affected_sessions(
                uow.auth_sessions,
                target.id,
                tenant_id,
                revoked_at=now,
            )
            uow.memberships.update(suspended)
            self._support.record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=suspended,
                action="tenant.membership.suspended",
                operation="update",
                old_status=MEMBERSHIP_STATUS_ACTIVE,
                new_status=suspended.status,
                metadata={
                    "target_user_id": target.id,
                    "invalidated_session_count": invalidated_sessions,
                },
            )
            # AuthSession invalidation is a side effect, not a separate event; suspension
            # never touches RoleBinding rows either.
            uow.record_event(
                TenantMembershipSuspended(
                    membership_id=suspended.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return suspended

    def reactivate_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            actor, tenant_id = self._support.require_tenant_administrator(
                uow, operation_label="reactivate a tenant member"
            )
            target = self._support.require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="reactivate",
                require_active=True,
            )
            membership = self._support.require_membership(
                uow.memberships, target.id, tenant_id
            )
            now = self._clock.now()
            reactivated = membership.reactivate(reactivated_at=now)
            uow.memberships.update(reactivated)
            self._support.record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=reactivated,
                action="tenant.membership.reactivated",
                operation="update",
                old_status=MEMBERSHIP_STATUS_SUSPENDED,
                new_status=reactivated.status,
                metadata={"target_user_id": target.id},
            )
            # Reactivation never touches RoleBinding rows, so no RoleBinding event is emitted.
            uow.record_event(
                TenantMembershipReactivated(
                    membership_id=reactivated.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            uow.commit()
        return reactivated

    def remove_member(self, target_user_id: str) -> UserTenantMembership:
        with self._uow_factory.create(context=self._support.new_context()) as uow:
            actor, tenant_id = self._support.require_tenant_administrator(
                uow, operation_label="remove a tenant member"
            )
            target = self._support.require_manageable_target(
                uow,
                target_user_id,
                actor=actor,
                operation_label="remove",
            )
            membership = self._support.require_membership(
                uow.memberships, target.id, tenant_id
            )
            self._support.guard_last_tenant_administrator(
                uow.memberships, uow.role_bindings, uow.roles, target.id, tenant_id
            )
            now = self._clock.now()
            removed = membership.remove(removed_at=now)
            uow.memberships.update(removed)
            # Recorded before the RoleBinding revocation cascade below so committed event
            # order matches the real transition order.
            uow.record_event(
                TenantMembershipRemoved(
                    membership_id=removed.id,
                    tenant_id=tenant_id,
                    user_id=target.id,
                    occurred_at=now,
                )
            )
            invalidated_sessions = self._support.revoke_affected_sessions(
                uow.auth_sessions,
                target.id,
                tenant_id,
                revoked_at=now,
            )
            revoked_binding_count = (
                self._support.revoke_active_role_bindings_for_membership_removal(
                    uow,
                    target.id,
                    tenant_id,
                    actor=actor,
                )
            )
            self._support.record_membership_audit(
                uow.audit,
                actor=actor,
                tenant_id=tenant_id,
                membership=removed,
                action="tenant.membership.removed",
                operation="update",
                old_status=membership.status,
                new_status=removed.status,
                metadata={
                    "target_user_id": target.id,
                    "invalidated_session_count": invalidated_sessions,
                    "revoked_binding_count": revoked_binding_count,
                },
            )
            uow.commit()
        return removed
