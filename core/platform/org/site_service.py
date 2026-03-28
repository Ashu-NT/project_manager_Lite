from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_any_permission, require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.org.domain import Organization, Site
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import normalize_code, normalize_name


def _normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def _resolve_name(*, name: str | None, display_name: str | None, label: str) -> str:
    return normalize_name(display_name if display_name is not None else name, label=label)


def _normalize_status(value: str | None, *, is_active: bool) -> str:
    normalized = _normalize_optional_text(value).upper()
    if normalized:
        return normalized
    return "ACTIVE" if is_active else "INACTIVE"


class SiteService:
    def __init__(
        self,
        session: Session,
        site_repo: SiteRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._site_repo = site_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_sites(self, *, active_only: bool | None = None) -> list[Site]:
        self._require_site_read_access("list sites")
        organization = self._active_organization()
        return self._site_repo.list_for_organization(organization.id, active_only=active_only)

    def search_sites(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Site]:
        self._require_site_read_access("search sites")
        normalized_search = _normalize_optional_text(search_text).lower()
        rows = self._site_repo.list_for_organization(self._active_organization().id, active_only=active_only)
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
        normalized_code = normalize_code(site_code, label="Site code")
        normalized_name = _resolve_name(name=name, display_name=display_name, label="Site name")
        if self._site_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
        now = datetime.now(timezone.utc)
        site = Site.create(
            organization_id=organization.id,
            site_code=normalized_code,
            name=normalized_name,
            description=_normalize_optional_text(description),
            country=_normalize_optional_text(country),
            region=_normalize_optional_text(region),
            city=_normalize_optional_text(city),
            address_line_1=_normalize_optional_text(address_line_1),
            address_line_2=_normalize_optional_text(address_line_2),
            postal_code=_normalize_optional_text(postal_code),
            timezone=_normalize_optional_text(timezone_name) or organization.timezone_name,
            currency_code=_normalize_optional_text(currency_code).upper() or organization.base_currency,
            site_type=_normalize_optional_text(site_type),
            status=_normalize_status(status, is_active=bool(is_active)),
            default_calendar_id=_normalize_optional_text(default_calendar_id) or "default",
            default_language=_normalize_optional_text(default_language),
            is_active=bool(is_active),
            opened_at=opened_at or (now if is_active else None),
            closed_at=closed_at,
            notes=_normalize_optional_text(notes),
        )
        try:
            self._site_repo.add(site)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="site.create",
            entity_type="site",
            entity_id=site.id,
            details={
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
        if site_code is not None:
            normalized_code = normalize_code(site_code, label="Site code")
            existing = self._site_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != site.id:
                raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
            site.site_code = normalized_code
        if name is not None or display_name is not None:
            site.name = _resolve_name(name=name, display_name=display_name, label="Site name")
        if description is not None:
            site.description = _normalize_optional_text(description)
        if country is not None:
            site.country = _normalize_optional_text(country)
        if region is not None:
            site.region = _normalize_optional_text(region)
        if city is not None:
            site.city = _normalize_optional_text(city)
        if address_line_1 is not None:
            site.address_line_1 = _normalize_optional_text(address_line_1)
        if address_line_2 is not None:
            site.address_line_2 = _normalize_optional_text(address_line_2)
        if postal_code is not None:
            site.postal_code = _normalize_optional_text(postal_code)
        if timezone_name is not None:
            site.timezone = _normalize_optional_text(timezone_name)
        if currency_code is not None:
            site.currency_code = _normalize_optional_text(currency_code).upper()
        if site_type is not None:
            site.site_type = _normalize_optional_text(site_type)
        if status is not None:
            site.status = _normalize_status(status, is_active=site.is_active if is_active is None else bool(is_active))
        if default_calendar_id is not None:
            site.default_calendar_id = _normalize_optional_text(default_calendar_id)
        if default_language is not None:
            site.default_language = _normalize_optional_text(default_language)
        previous_is_active = site.is_active
        if is_active is not None:
            site.is_active = bool(is_active)
        if opened_at is not None:
            site.opened_at = opened_at
        if closed_at is not None:
            site.closed_at = closed_at
        if notes is not None:
            site.notes = _normalize_optional_text(notes)
        if is_active is not None and previous_is_active != site.is_active:
            now = datetime.now(timezone.utc)
            if site.is_active:
                if status is None:
                    site.status = "ACTIVE"
                site.closed_at = None if closed_at is None else site.closed_at
                site.opened_at = site.opened_at or now
            else:
                if status is None:
                    site.status = "INACTIVE"
                site.closed_at = site.closed_at or now
        site.updated_at = datetime.now(timezone.utc)
        try:
            self._site_repo.update(site)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="site.update",
            entity_type="site",
            entity_id=site.id,
            details={
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

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_site_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "site.read"),
            operation_label=operation_label,
        )


__all__ = ["SiteService"]
