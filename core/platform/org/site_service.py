from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.common.models import Organization, Site
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import normalize_code, normalize_name


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
        require_permission(self._user_session, "settings.manage", operation_label="list sites")
        organization = self._active_organization()
        return self._site_repo.list_for_organization(organization.id, active_only=active_only)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view site context")
        return self._active_organization()

    def create_site(
        self,
        *,
        site_code: str,
        display_name: str,
        is_active: bool = True,
    ) -> Site:
        require_permission(self._user_session, "settings.manage", operation_label="create site")
        organization = self._active_organization()
        normalized_code = normalize_code(site_code, label="Site code")
        normalized_name = normalize_name(display_name, label="Site name")
        if self._site_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Site code already exists in the active organization.", code="SITE_CODE_EXISTS")
        site = Site.create(
            organization_id=organization.id,
            site_code=normalized_code,
            display_name=normalized_name,
            is_active=bool(is_active),
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
                "display_name": site.display_name,
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
        display_name: str | None = None,
        is_active: bool | None = None,
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
        if display_name is not None:
            site.display_name = normalize_name(display_name, label="Site name")
        if is_active is not None:
            site.is_active = bool(is_active)
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
                "display_name": site.display_name,
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


__all__ = ["SiteService"]
