from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.core.platform.org.support import (
    DEFAULT_ORGANIZATION_CODE,
    DEFAULT_ORGANIZATION_CURRENCY,
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_TIMEZONE,
    normalize_code,
    normalize_name,
)

if TYPE_CHECKING:
    from src.core.platform.audit.application.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.auth.domain.session import UserSessionContext


class OrganizationService:
    def __init__(
        self,
        session: Session,
        organization_repo: OrganizationRepository,
        *,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
    ):
        self._session = session
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service

    # ------------------------------------------------------------------
    # Bootstrap — allowed to use unscoped repo methods (no tenant yet).
    # ------------------------------------------------------------------

    def bootstrap_defaults(self) -> None:
        if self._organization_repo.list_all():
            return
        organization = Organization.create(
            organization_code=DEFAULT_ORGANIZATION_CODE,
            display_name=DEFAULT_ORGANIZATION_NAME,
            timezone_name=DEFAULT_ORGANIZATION_TIMEZONE,
            base_currency=DEFAULT_ORGANIZATION_CURRENCY,
            is_active=True,
        )
        self._organization_repo.add(organization)
        self._session.commit()

    # ------------------------------------------------------------------
    # Tenant context helper — used by every runtime method.
    # Raises TENANT_CONTEXT_REQUIRED immediately if no active tenant.
    # ------------------------------------------------------------------

    def _require_current_tenant_id(self, *, operation_label: str) -> str:
        if self._user_session is None:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = str(self._user_session.active_tenant_id() or "").strip()
        if not tenant_id:
            raise BusinessRuleError(
                f"Tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_id

    # ------------------------------------------------------------------
    # Runtime read operations — all tenant-scoped.
    # ------------------------------------------------------------------

    def list_organizations(self, *, active_only: bool | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        tenant_id = self._require_current_tenant_id(operation_label="list organizations")
        return self._organization_repo.list_for_tenant(tenant_id, active_only=active_only)

    def get_active_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view active organization")
        tenant_id = self._require_current_tenant_id(operation_label="view active organization")
        organization = self._organization_repo.get_active_for_tenant(tenant_id)
        if organization is None:
            self.bootstrap_defaults()
            organization = self._organization_repo.get_active_for_tenant(tenant_id)
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    # ------------------------------------------------------------------
    # Runtime write operations — all tenant-scoped.
    # ------------------------------------------------------------------

    def create_organization(
        self,
        *,
        organization_code: str,
        display_name: str,
        timezone_name: str = DEFAULT_ORGANIZATION_TIMEZONE,
        base_currency: str = DEFAULT_ORGANIZATION_CURRENCY,
        is_active: bool = True,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="create organization")
        tenant_id = self._require_current_tenant_id(operation_label="create organization")
        normalized_code = normalize_code(organization_code, label="Organization code")
        normalized_name = normalize_name(display_name, label="Organization name")
        normalized_timezone = normalize_name(timezone_name, label="Timezone")
        normalized_currency = normalize_code(base_currency, label="Base currency")
        if self._organization_repo.get_by_code_for_tenant(normalized_code, tenant_id) is not None:
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
        organization = Organization.create(
            organization_code=normalized_code,
            display_name=normalized_name,
            timezone_name=normalized_timezone,
            base_currency=normalized_currency,
            is_active=bool(is_active),
            tenant_id=tenant_id,
        )
        try:
            if organization.is_active:
                self._deactivate_other_organizations(tenant_id=tenant_id, exclude_id=None)
            self._organization_repo.add(organization)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="create",
            entity_type="organization",
            entity_id=organization.id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.create",
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "is_active": str(organization.is_active),
            },
        )
        domain_events.organizations_changed.emit(organization.id)
        return organization

    def update_organization(
        self,
        organization_id: str,
        *,
        organization_code: str | None = None,
        display_name: str | None = None,
        timezone_name: str | None = None,
        base_currency: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="update organization")
        tenant_id = self._require_current_tenant_id(operation_label="update organization")
        organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        if expected_version is not None and organization.version != expected_version:
            raise ConcurrencyError(
                "Organization changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if organization_code is not None:
            normalized_code = normalize_code(organization_code, label="Organization code")
            existing = self._organization_repo.get_by_code_for_tenant(normalized_code, tenant_id)
            if existing is not None and existing.id != organization.id:
                raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
            organization.organization_code = normalized_code
        if display_name is not None:
            organization.display_name = normalize_name(display_name, label="Organization name")
        if timezone_name is not None:
            organization.timezone_name = normalize_name(timezone_name, label="Timezone")
        if base_currency is not None:
            organization.base_currency = normalize_code(base_currency, label="Base currency")
        if is_active is not None:
            if not is_active and organization.is_active and not self._has_other_active_organizations(
                organization.id, tenant_id=tenant_id
            ):
                raise ValidationError(
                    "At least one active organization is required.",
                    code="ORGANIZATION_ACTIVE_REQUIRED",
                )
            organization.is_active = bool(is_active)
        try:
            if organization.is_active:
                self._deactivate_other_organizations(tenant_id=tenant_id, exclude_id=organization.id)
            self._organization_repo.update(organization)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="update",
            entity_type="organization",
            entity_id=organization.id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.update",
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
                "timezone_name": organization.timezone_name,
                "base_currency": organization.base_currency,
                "is_active": str(organization.is_active),
            },
        )
        domain_events.organizations_changed.emit(organization.id)
        return organization

    def set_active_organization(self, organization_id: str) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="set active organization")
        tenant_id = self._require_current_tenant_id(operation_label="set active organization")
        organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        try:
            self._deactivate_other_organizations(tenant_id=tenant_id, exclude_id=organization.id)
            organization.is_active = True
            self._organization_repo.update(organization)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="update",
            entity_type="organization",
            entity_id=organization.id,
            module="platform",
            severity="low",
            metadata={
                "action": "organization.set_active",
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
            },
        )
        if self._user_session is not None:
            self._user_session.set_active_organization_id(organization.id)
        domain_events.organizations_changed.emit(organization.id)
        return organization

    # ------------------------------------------------------------------
    # Private helpers — tenant_id always passed by caller.
    # ------------------------------------------------------------------

    def _deactivate_other_organizations(self, *, tenant_id: str, exclude_id: str | None) -> None:
        for organization in self._organization_repo.list_for_tenant(tenant_id, active_only=True):
            if exclude_id and organization.id == exclude_id:
                continue
            organization.is_active = False
            self._organization_repo.update(organization)

    def _has_other_active_organizations(self, organization_id: str, *, tenant_id: str) -> bool:
        return any(
            org.id != organization_id
            for org in self._organization_repo.list_for_tenant(tenant_id, active_only=True)
        )


__all__ = ["OrganizationService"]
