from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.domain.master_data.site import Site
from src.core.platform.domain.master_data.site.events import (
    SiteCreated,
    SiteDisabled,
    SiteEnabled,
    SiteProfileUpdated,
)
from src.core.shared.audit import record_audit_entry

from .site_context import active_organization
from .site_utils import normalize_optional_text, resolve_name

if TYPE_CHECKING:
    from .site_service import SiteService


def create_site(
    service: SiteService,
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
    require_permission(service._user_session, "settings.manage", operation_label="create site")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    now = datetime.now(timezone.utc)
    site = Site.create(
        organization_id=organization.id,
        site_code=site_code,
        name=resolve_name(name=name, display_name=display_name),
        description=description,
        country=country,
        region=region,
        city=city,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        postal_code=postal_code,
        timezone=normalize_optional_text(timezone_name) or organization.timezone_name,
        currency_code=normalize_optional_text(currency_code) or organization.base_currency,
        site_type=site_type,
        status=status,
        # Legacy field: references working_calendars.id. Not read by the enterprise
        # CalendarResolver -- which uses site_calendar_assignments instead and falls
        # back to the GLOBAL platform_calendar. Kept for backward-compat data export.
        default_calendar_id=normalize_optional_text(default_calendar_id) or "default",
        default_language=default_language,
        is_active=is_active,
        opened_at=opened_at or (now if is_active else None),
        closed_at=closed_at,
        notes=notes,
    )
    with service._uow_factory.create(context=service._new_context()) as uow:
        if uow.sites.get_by_code(organization.id, site.site_code) is not None:
            raise ValidationError(
                "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
            )
        try:
            uow.sites.add(site)
            record_audit_entry(
                uow,
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
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                SiteCreated(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    site_id=site.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
            ) from exc
    return site


def update_site(
    service: SiteService,
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
    require_permission(service._user_session, "settings.manage", operation_label="update site")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    with service._uow_factory.create(context=service._new_context()) as uow:
        site = uow.sites.get(site_id)
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
            name=site.name if name is None and display_name is None else resolve_name(name=name, display_name=display_name),
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
        )
        availability_changed = is_active is not None and previous_is_active != bool(next_is_active)
        profile_changed = (
            candidate.site_code != site.site_code
            or candidate.name != site.name
            or candidate.description != site.description
            or candidate.country != site.country
            or candidate.region != site.region
            or candidate.city != site.city
            or candidate.address_line_1 != site.address_line_1
            or candidate.address_line_2 != site.address_line_2
            or candidate.postal_code != site.postal_code
            or candidate.timezone != site.timezone
            or candidate.currency_code != site.currency_code
            or candidate.site_type != site.site_type
            or candidate.default_calendar_id != site.default_calendar_id
            or candidate.default_language != site.default_language
            or candidate.notes != site.notes
        )
        if not availability_changed:
            profile_changed = (
                profile_changed
                or candidate.status != site.status
                or candidate.opened_at != site.opened_at
                or candidate.closed_at != site.closed_at
            )
        if not profile_changed and not availability_changed:
            return site
        candidate = replace(candidate, updated_at=now)
        existing = uow.sites.get_by_code(organization.id, candidate.site_code)
        if existing is not None and existing.id != site.id:
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
        try:
            uow.sites.update(candidate)
            record_audit_entry(
                uow,
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
                commit=False,
                fail_closed=True,
            )
            occurred_at = service._clock.now()
            if profile_changed:
                uow.record_event(
                    SiteProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        site_id=candidate.id,
                        occurred_at=occurred_at,
                    )
                )
            if availability_changed:
                availability_event_cls = SiteEnabled if candidate.is_active else SiteDisabled
                uow.record_event(
                    availability_event_cls(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        site_id=candidate.id,
                        occurred_at=occurred_at,
                    )
                )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Site code already exists in the active organization.", code="SITE_CODE_EXISTS"
            ) from exc
    return candidate


__all__ = ["create_site", "update_site"]
