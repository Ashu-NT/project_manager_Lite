from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.org.domain import Organization
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import (
    DEFAULT_ORGANIZATION_CODE,
    DEFAULT_ORGANIZATION_CURRENCY,
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_TIMEZONE,
    normalize_code,
    normalize_name,
)


class OrganizationService:
    def __init__(
        self,
        session: Session,
        organization_repo: OrganizationRepository,
        *,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

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

    def list_organizations(self, *, active_only: bool | None = None) -> list[Organization]:
        require_permission(self._user_session, "settings.manage", operation_label="list organizations")
        return self._organization_repo.list_all(active_only=active_only)

    def get_active_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view active organization")
        organization = self._organization_repo.get_active()
        if organization is None:
            self.bootstrap_defaults()
            organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

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
        normalized_code = normalize_code(organization_code, label="Organization code")
        normalized_name = normalize_name(display_name, label="Organization name")
        normalized_timezone = normalize_name(timezone_name, label="Timezone")
        normalized_currency = normalize_code(base_currency, label="Base currency")
        if self._organization_repo.get_by_code(normalized_code) is not None:
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS")
        organization = Organization.create(
            organization_code=normalized_code,
            display_name=normalized_name,
            timezone_name=normalized_timezone,
            base_currency=normalized_currency,
            is_active=bool(is_active),
        )
        try:
            if organization.is_active:
                self._deactivate_other_organizations(exclude_id=None)
            self._organization_repo.add(organization)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="organization.create",
            entity_type="organization",
            entity_id=organization.id,
            details={
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
        organization = self._organization_repo.get(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        if expected_version is not None and organization.version != expected_version:
            raise ConcurrencyError(
                "Organization changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if organization_code is not None:
            normalized_code = normalize_code(organization_code, label="Organization code")
            existing = self._organization_repo.get_by_code(normalized_code)
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
            if not is_active and organization.is_active and not self._has_other_active_organizations(organization.id):
                raise ValidationError(
                    "At least one active organization is required.",
                    code="ORGANIZATION_ACTIVE_REQUIRED",
                )
            organization.is_active = bool(is_active)
        try:
            if organization.is_active:
                self._deactivate_other_organizations(exclude_id=organization.id)
            self._organization_repo.update(organization)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Organization code already exists.", code="ORGANIZATION_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="organization.update",
            entity_type="organization",
            entity_id=organization.id,
            details={
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
        organization = self._organization_repo.get(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        try:
            self._deactivate_other_organizations(exclude_id=organization.id)
            organization.is_active = True
            self._organization_repo.update(organization)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="organization.set_active",
            entity_type="organization",
            entity_id=organization.id,
            details={
                "organization_code": organization.organization_code,
                "display_name": organization.display_name,
            },
        )
        domain_events.organizations_changed.emit(organization.id)
        return organization

    def _deactivate_other_organizations(self, *, exclude_id: str | None) -> None:
        for organization in self._organization_repo.list_all(active_only=True):
            if exclude_id and organization.id == exclude_id:
                continue
            if not organization.is_active:
                continue
            organization.is_active = False
            self._organization_repo.update(organization)

    def _has_other_active_organizations(self, organization_id: str) -> bool:
        return any(
            organization.id != organization_id
            for organization in self._organization_repo.list_all(active_only=True)
        )


__all__ = ["OrganizationService"]
