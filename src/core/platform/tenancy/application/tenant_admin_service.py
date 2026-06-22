"""Platform-level tenant lifecycle management service (Phase 2B/2C)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.platform_events.contracts import PlatformEventRepository
from src.core.platform.platform_events.domain.platform_event import PlatformEvent
from src.core.platform.tenancy.contracts import TenantRepository, UserTenantMembershipRepository
from src.core.platform.tenancy.domain.tenant import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_ARCHIVED,
    TENANT_STATUS_SUSPENDED,
    Tenant,
)
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership


class TenantAdminService:
    """Lifecycle operations for the Tenant aggregate.

    Permission model:
      tenant.create / platform.admin  → create_tenant()
      tenant.read   / platform.admin  → get_tenant(), list_tenants()
      tenant.manage / platform.admin  → suspend_tenant(), archive_tenant()
      platform.admin only             → restore_tenant()

    Lifecycle transitions:
      active    → suspended  (suspend_tenant)
      active    → archived   (archive_tenant)
      suspended → archived   (archive_tenant)
      archived  → active     (restore_tenant — platform.admin only)
    """

    def __init__(
        self,
        *,
        session: Session,
        tenant_repo: TenantRepository,
        user_tenant_repo: UserTenantMembershipRepository,
        user_session: UserSessionContext,
        platform_event_repo: PlatformEventRepository | None = None,
    ) -> None:
        self._session = session
        self._tenant_repo = tenant_repo
        self._user_tenant_repo = user_tenant_repo
        self._user_session = user_session
        self._platform_event_repo = platform_event_repo

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_tenant(self, tenant_id: str) -> Tenant:
        normalized = str(tenant_id or "").strip()
        tenant = self._tenant_repo.get(normalized) if normalized else None
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        return tenant

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        if principal is None:
            return None
        return str(getattr(principal, "user_id", "") or "").strip() or None

    def _active_tenant_id(self) -> str | None:
        fn = getattr(self._user_session, "active_tenant_id", None)
        return fn() if callable(fn) else None

    def _guard_self_lockout(self, tenant_id: str, operation: str) -> None:
        active_tid = self._active_tenant_id()
        if active_tid and active_tid == tenant_id:
            raise BusinessRuleError(
                f"Cannot {operation} the currently active tenant (self-lockout protection).",
                code="TENANT_SELF_LOCKOUT",
            )

    def _emit_tenant_event(
        self,
        operation: str,
        tenant: Tenant,
        *,
        old_status: str | None = None,
    ) -> None:
        if self._platform_event_repo is None:
            return
        _SEVERITY = {
            "create_tenant": "low",
            "suspend_tenant": "medium",
            "archive_tenant": "high",
            "restore_tenant": "medium",
        }
        if operation == "create_tenant":
            meta: dict = {"tenant_code": tenant.tenant_code, "display_name": tenant.display_name}
        elif operation == "suspend_tenant":
            meta = {"old_status": TENANT_STATUS_ACTIVE, "new_status": TENANT_STATUS_SUSPENDED, "tenant_code": tenant.tenant_code}
        elif operation == "archive_tenant":
            meta = {"old_status": old_status or "", "new_status": TENANT_STATUS_ARCHIVED, "tenant_code": tenant.tenant_code}
        elif operation == "restore_tenant":
            meta = {"old_status": TENANT_STATUS_ARCHIVED, "new_status": TENANT_STATUS_ACTIVE, "tenant_code": tenant.tenant_code}
        else:
            meta = {"tenant_code": tenant.tenant_code}
        event = PlatformEvent.create(
            operation=operation,
            actor_user_id=self._current_user_id(),
            tenant_id=tenant.id,
            resource_type="tenant",
            resource_id=tenant.id,
            outcome="success",
            severity=_SEVERITY.get(operation, "low"),
            metadata=meta,
        )
        self._platform_event_repo.add(event)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_tenant(self, tenant_id: str) -> Tenant:
        require_any_permission(
            self._user_session,
            ["tenant.read", "platform.admin"],
            operation_label="get tenant",
        )
        return self._require_tenant(tenant_id)

    def list_tenants(self, *, active_only: bool | None = None) -> list[Tenant]:
        require_any_permission(
            self._user_session,
            ["tenant.read", "platform.admin"],
            operation_label="list tenants",
        )
        return self._tenant_repo.list_all(active_only=active_only)

    def list_accessible_tenants(self) -> list[Tenant]:
        """Return tenants the current user can switch to.

        No permission guard — listing one's own memberships is always allowed.
        Platform.admin and admin: all tenants (including suspended/archived, so
        the UI can show their status). Regular users: only active (non-suspended,
        non-archived) tenants where an active user_tenants membership exists.
        """
        user_id = self._current_user_id()
        if not user_id:
            return []
        principal = getattr(self._user_session, "principal", None)
        if principal is not None:
            is_admin = "admin" in getattr(principal, "role_names", frozenset())
            is_platform_admin = "platform.admin" in getattr(principal, "permissions", frozenset())
            if is_admin or is_platform_admin:
                return self._tenant_repo.list_all(active_only=None)
        tenant_ids = self._user_tenant_repo.list_tenant_ids_for_user(user_id)
        tenants: list[Tenant] = []
        for tid in tenant_ids:
            tenant = self._tenant_repo.get(tid)
            if tenant is not None and tenant.is_active:
                tenants.append(tenant)
        return tenants

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_tenant(self, tenant_code: str, display_name: str) -> Tenant:
        require_any_permission(
            self._user_session,
            ["tenant.create", "platform.admin"],
            operation_label="create tenant",
        )
        normalized_code = str(tenant_code or "").strip().upper()
        if not normalized_code:
            raise ValidationError("Tenant code is required.", code="TENANT_CODE_REQUIRED")
        normalized_name = str(display_name or "").strip()
        if not normalized_name:
            raise ValidationError("Display name is required.", code="TENANT_DISPLAY_NAME_REQUIRED")
        if self._tenant_repo.get_by_code(normalized_code) is not None:
            raise BusinessRuleError(
                f"Tenant code '{normalized_code}' is already in use.",
                code="TENANT_CODE_CONFLICT",
            )
        tenant = Tenant.create(tenant_code=normalized_code, display_name=normalized_name)
        self._tenant_repo.add(tenant)
        user_id = self._current_user_id()
        if user_id:
            self._user_tenant_repo.add(
                UserTenantMembership.create(
                    user_id=user_id,
                    tenant_id=tenant.id,
                    tenant_role="tenant_admin",
                )
            )
        self._session.flush()
        self._emit_tenant_event("create_tenant", tenant)
        return tenant

    # ------------------------------------------------------------------
    # Lifecycle mutations
    # ------------------------------------------------------------------

    def suspend_tenant(self, tenant_id: str) -> Tenant:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="suspend tenant",
        )
        self._guard_self_lockout(tenant_id, "suspend")
        tenant = self._require_tenant(tenant_id)
        if tenant.tenant_status != TENANT_STATUS_ACTIVE:
            raise BusinessRuleError(
                f"Only active tenants can be suspended. Current status: '{tenant.tenant_status}'.",
                code="TENANT_INVALID_TRANSITION",
            )
        tenant.tenant_status = TENANT_STATUS_SUSPENDED
        self._tenant_repo.update(tenant)
        self._session.flush()
        self._emit_tenant_event("suspend_tenant", tenant)
        return tenant

    def archive_tenant(self, tenant_id: str) -> Tenant:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="archive tenant",
        )
        self._guard_self_lockout(tenant_id, "archive")
        tenant = self._require_tenant(tenant_id)
        if tenant.tenant_status == TENANT_STATUS_ARCHIVED:
            raise BusinessRuleError(
                "Tenant is already archived.",
                code="TENANT_ALREADY_ARCHIVED",
            )
        prior_status = tenant.tenant_status
        tenant.tenant_status = TENANT_STATUS_ARCHIVED
        self._tenant_repo.update(tenant)
        self._session.flush()
        self._emit_tenant_event("archive_tenant", tenant, old_status=prior_status)
        return tenant

    def restore_tenant(self, tenant_id: str) -> Tenant:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="restore tenant",
        )
        tenant = self._require_tenant(tenant_id)
        if tenant.tenant_status != TENANT_STATUS_ARCHIVED:
            raise BusinessRuleError(
                f"Only archived tenants can be restored. Current status: '{tenant.tenant_status}'.",
                code="TENANT_NOT_ARCHIVED",
            )
        tenant.tenant_status = TENANT_STATUS_ACTIVE
        self._tenant_repo.update(tenant)
        self._session.flush()
        self._emit_tenant_event("restore_tenant", tenant)
        return tenant


__all__ = ["TenantAdminService"]
