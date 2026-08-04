from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.master_data.org.support import normalize_code
from src.core.platform.contract.master_data.site.contracts import SiteRepository
from src.core.platform.domain.master_data.site import Site
from src.core.platform.application.tenant.tenancy import TenantContextService

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.auth.domain.session import UserSessionContext


def _normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def _resolve_name(*, name: str | None, display_name: str | None) -> str | None:
    return display_name if display_name is not None else name


class SiteService:
    def __init__(
        self,
        session: Session,
        site_repo: SiteRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        tenant_context_service: TenantContextService | None = None,
    ):
        self._session = session
        self._site_repo = site_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service

    def list_sites(self, *, active_only: bool | None = None) -> list[Site]:
        self._require_site_read_access("list sites")
        organization = self._active_organization()
        rows = self._site_repo.list_for_organization(organization.id, active_only=active_only)
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="site",
            permission_code="site.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )

    def search_sites(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Site]:
        self._require_site_read_access("search sites")
        normalized_search = _normalize_optional_text(search_text).lower()
        rows = self.list_sites(active_only=active_only)
        if not normalized_search:
            return rows
        return [
            site
            for site in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        site.site_code,
                        site.name,
                        site.city,
                        site.country,
                        site.site_type,
                        site.status,
                    ],
                )
            ).lower()
        ]

    def get_site(self, site_id: str) -> Site:
        self._require_site_read_access("view site")
        organization = self._active_organization()
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        require_scope_permission(
            self._user_session,
            "site",
            site.id,
            "site.read",
            operation_label="view site",
        )
        return site

    def find_site_by_code(self, site_code: str) -> Site | None:
        self._require_site_read_access("resolve site")
        normalized_code = normalize_code(site_code, label="Site code")
        return self._site_repo.get_by_code(self._active_organization().id, normalized_code)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view site context")
        return self._active_organization()

    def create_site(
        self,
        *,
        site_code: str,
        name: str | None = None,
        display_name: str | None = None,
        description: str = "",
        country: str = "",
        region: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        timezone_name: str | None = None,
        currency_code: str | None = None,
        site_type: str = "",
        status: str | None = None,
        default_calendar_id: str = "",
        default_language: str = "",
        is_active: bool = True,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        notes: str = "",
    ) -> Site:
        require_permission(self._user_session, "settings.manage", operation_label="create site")
        organization = self._active_organization()
        now = datetime.now(timezone.utc)
        site = Site.create(
            organization_id=organization.id,
            site_code=site_code,
            name=_resolve_name(name=name, display_name=display_name),
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone=_normalize_optional_text(timezone_name) or organization.timezone_name,
            currency_code=_normalize_optional_text(currency_code) or organization.base_currency,
            site_type=site_type,
            status=status,
            # Legacy field: references working_calendars.id. Not read by the enterprise
            # CalendarResolver — which uses site_calendar_assignments instead and falls
            # back to the GLOBAL platform_calendar. Kept for backward-compat data export.
            default_calendar_id=_normalize_optional_text(default_calendar_id) or "default",
            default_language=default_language,
            is_active=is_active,
            opened_at=opened_at or (now if is_active else None),
            closed_at=closed_at,
            notes=notes,
        )
        if self._site_repo.get_by_code(organization.id, site.site_code) is not None:
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
        try:
            self._site_repo.add(site)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="create",
            entity_type="site",
            entity_id=site.id,
            module="platform",
            severity="low",
            metadata={
                "action": "site.create",
                "organization_id": organization.id,
                "site_code": site.site_code,
                "name": site.name,
                "status": site.status,
                "city": site.city,
                "country": site.country,
                "is_active": str(site.is_active),
            },
        )
        domain_events.sites_changed.emit(site.id)
        return site

    def update_site(
        self,
        site_id: str,
        *,
        site_code: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        country: str | None = None,
        region: str | None = None,
        city: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        postal_code: str | None = None,
        timezone_name: str | None = None,
        currency_code: str | None = None,
        site_type: str | None = None,
        status: str | None = None,
        default_calendar_id: str | None = None,
        default_language: str | None = None,
        is_active: bool | None = None,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Site:
        require_permission(self._user_session, "settings.manage", operation_label="update site")
        organization = self._active_organization()
        site = self._site_repo.get(site_id)
        if site is None or site.organization_id != organization.id:
            raise NotFoundError("Site not found in the active organization.", code="SITE_NOT_FOUND")
        if expected_version is not None and site.version != expected_version:
            raise ConcurrencyError(
                "Site changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        previous_is_active = site.is_active
        now = datetime.now(timezone.utc)
        next_is_active = site.is_active if is_active is None else is_active
        next_status = site.status
        if status is not None:
            next_status = status
        elif is_active is not None and previous_is_active != bool(next_is_active):
            next_status = ""
        next_opened_at = site.opened_at if opened_at is None else opened_at
        next_closed_at = site.closed_at if closed_at is None else closed_at
        if is_active is not None and previous_is_active != bool(next_is_active):
            if bool(next_is_active):
                if closed_at is None:
                    next_closed_at = None
                if next_opened_at is None:
                    next_opened_at = now
            elif next_closed_at is None:
                next_closed_at = now
        candidate = replace(
            site,
            site_code=site.site_code if site_code is None else site_code,
            name=site.name if name is None and display_name is None else _resolve_name(name=name, display_name=display_name),
            description=site.description if description is None else description,
            country=site.country if country is None else country,
            region=site.region if region is None else region,
            city=site.city if city is None else city,
            address_line_1=site.address_line_1 if address_line_1 is None else address_line_1,
            address_line_2=site.address_line_2 if address_line_2 is None else address_line_2,
            postal_code=site.postal_code if postal_code is None else postal_code,
            timezone=site.timezone if timezone_name is None else timezone_name,
            currency_code=site.currency_code if currency_code is None else currency_code,
            site_type=site.site_type if site_type is None else site_type,
            status=next_status,
            default_calendar_id=site.default_calendar_id if default_calendar_id is None else default_calendar_id,
            default_language=site.default_language if default_language is None else default_language,
            is_active=next_is_active,
            opened_at=next_opened_at,
            closed_at=next_closed_at,
            notes=site.notes if notes is None else notes,
            updated_at=now,
        )
        existing = self._site_repo.get_by_code(organization.id, candidate.site_code)
        if existing is not None and existing.id != site.id:
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
        try:
            self._site_repo.update(candidate)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit_entry(
            self,
            operation="update",
            entity_type="site",
            entity_id=candidate.id,
            module="platform",
            severity="low",
            metadata={
                "action": "site.update",
                "organization_id": organization.id,
                "site_code": candidate.site_code,
                "name": candidate.name,
                "status": candidate.status,
                "city": candidate.city,
                "country": candidate.country,
                "is_active": str(candidate.is_active),
            },
        )
        domain_events.sites_changed.emit(candidate.id)
        return candidate

    def _active_organization(self) -> Organization:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization = self._tenant_context_service.get_active_organization()
        if organization is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return organization

    def _require_site_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "site.read"),
            operation_label=operation_label,
        )


__all__ = ["SiteService"]
