from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.domain.master_data.site import Site


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def flush(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _FakeEnterpriseAuditService:
    def record(self, **kwargs) -> None:
        return None


class _FakeUserSession:
    def __init__(self, tenant_id: str = "tenant-1") -> None:
        self._tenant_id = tenant_id
        self.active_organization_id = ""

    def active_tenant_id(self) -> str:
        return self._tenant_id

    def set_active_organization_id(self, organization_id: str) -> None:
        self.active_organization_id = organization_id


class _FakeOrganizationRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Organization] = {}

    def add(self, organization: Organization) -> None:
        self._rows[organization.id] = organization

    def update(self, organization: Organization) -> None:
        if organization.id not in self._rows:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        organization.version += 1
        self._rows[organization.id] = organization

    def get(self, organization_id: str) -> Organization | None:
        return self._rows.get(organization_id)

    def get_by_code(self, organization_code: str) -> Organization | None:
        for row in self._rows.values():
            if row.organization_code == organization_code:
                return row
        return None

    def list_all(self, *, enabled_only: bool | None = None) -> list[Organization]:
        rows = list(self._rows.values())
        if enabled_only is not None:
            rows = [row for row in rows if row.is_enabled is bool(enabled_only)]
        return sorted(rows, key=lambda row: row.display_name)

    def get_for_tenant(self, organization_id: str, tenant_id: str) -> Organization | None:
        organization = self._rows.get(organization_id)
        if organization is None or organization.tenant_id != tenant_id:
            return None
        return organization

    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str) -> Organization | None:
        for row in self._rows.values():
            if row.organization_code == organization_code and row.tenant_id == tenant_id:
                return row
        return None

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        enabled_only: bool | None = None,
    ) -> list[Organization]:
        rows = [
            row
            for row in self._rows.values()
            if row.tenant_id == tenant_id
        ]
        if enabled_only is not None:
            rows = [row for row in rows if row.is_enabled is bool(enabled_only)]
        return sorted(rows, key=lambda row: row.display_name)


class _FakeOrganizationUnitOfWork:
    """P4B: a minimal stand-in for `SqlAlchemyOrganizationUnitOfWork` -- this file tests
    `OrganizationService`'s domain-validation/final-state logic against fully in-memory fakes
    with no real SQLAlchemy Session, so it cannot construct a real
    `SqlAlchemyOrganizationUnitOfWork`. Wraps the SAME `organization_repo`/
    `enterprise_audit_service` instances passed to `OrganizationService`'s constructor (not a
    fresh repo per call) since this fake world has no session-per-call concept -- callers assert
    against `service._organization_repo` directly across sequential calls."""

    def __init__(self, organization_repo: "_FakeOrganizationRepo", enterprise_audit_service) -> None:
        self.organizations = organization_repo
        self._enterprise_audit_service = enterprise_audit_service

    def __enter__(self) -> "_FakeOrganizationUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def commit(self) -> None:
        return None

    def record_event(self, event) -> None:
        return None


class _FakeOrganizationUnitOfWorkFactory:
    def __init__(self, organization_repo: "_FakeOrganizationRepo", enterprise_audit_service) -> None:
        self._organization_repo = organization_repo
        self._enterprise_audit_service = enterprise_audit_service

    def create(self, *, context) -> _FakeOrganizationUnitOfWork:
        return _FakeOrganizationUnitOfWork(self._organization_repo, self._enterprise_audit_service)


class _FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeTenantContext:
    def __init__(self, organization_repo: _FakeOrganizationRepo, organization_id: str) -> None:
        self._organization_repo = organization_repo
        self._organization_id = organization_id

    def get_active_organization(self) -> Organization | None:
        return self._organization_repo.get(self._organization_id)


class _FakeSiteUnitOfWork:
    def __init__(self, site_repo: "_FakeSiteRepo", enterprise_audit_service) -> None:
        self.sites = site_repo
        self._enterprise_audit_service = enterprise_audit_service

    def __enter__(self) -> "_FakeSiteUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def commit(self) -> None:
        return None

    def record_event(self, event) -> None:
        return None


class _FakeSiteUnitOfWorkFactory:
    def __init__(self, site_repo: "_FakeSiteRepo", enterprise_audit_service) -> None:
        self._site_repo = site_repo
        self._enterprise_audit_service = enterprise_audit_service

    def create(self, *, context) -> _FakeSiteUnitOfWork:
        return _FakeSiteUnitOfWork(self._site_repo, self._enterprise_audit_service)


class _FakeSiteRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Site] = {}

    def add(self, site: Site) -> None:
        self._rows[site.id] = site

    def update(self, site: Site) -> None:
        if site.id not in self._rows:
            raise NotFoundError("Site not found.", code="SITE_NOT_FOUND")
        site.version += 1
        self._rows[site.id] = site

    def get(self, site_id: str) -> Site | None:
        return self._rows.get(site_id)

    def get_by_code(self, organization_id: str, site_code: str) -> Site | None:
        for row in self._rows.values():
            if row.organization_id == organization_id and row.site_code == site_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Site]:
        rows = [
            row
            for row in self._rows.values()
            if row.organization_id == organization_id
        ]
        if active_only is not None:
            rows = [row for row in rows if row.is_active is bool(active_only)]
        return sorted(rows, key=lambda row: row.name)


def _make_organization_service(monkeypatch: pytest.MonkeyPatch) -> OrganizationService:
    monkeypatch.setattr(
        "src.core.platform.application.master_data.org.organization_service.require_permission",
        lambda *args, **kwargs: None,
    )
    organization_repo = _FakeOrganizationRepo()
    enterprise_audit_service = _FakeEnterpriseAuditService()
    return OrganizationService(
        session=_FakeSession(),
        organization_repo=organization_repo,
        uow_factory=_FakeOrganizationUnitOfWorkFactory(organization_repo, enterprise_audit_service),
        clock=_FakeClock(),
        user_session=_FakeUserSession(),
        enterprise_audit_service=enterprise_audit_service,
    )


def _make_site_service(monkeypatch: pytest.MonkeyPatch) -> tuple[SiteService, Organization]:
    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.site_service.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.site_service.require_any_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.site_service.require_scope_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.site_service.filter_scope_rows",
        lambda rows, *_args, **_kwargs: list(rows),
    )

    organization_repo = _FakeOrganizationRepo()
    organization = Organization.create(
        organization_code="default",
        display_name="  Default Organization  ",
        timezone_name="  UTC  ",
        base_currency=" eur ",
        tenant_id="tenant-1",
    )
    organization_repo.add(organization)

    site_repo = _FakeSiteRepo()
    enterprise_audit_service = _FakeEnterpriseAuditService()
    service = SiteService(
        session=_FakeSession(),
        site_repo=site_repo,
        organization_repo=organization_repo,
        user_session=object(),
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=_FakeTenantContext(organization_repo, organization.id),
        uow_factory=_FakeSiteUnitOfWorkFactory(site_repo, enterprise_audit_service),
        clock=_FakeClock(),
    )
    return service, organization


def test_organization_dto_normalizes_and_validates_fields():
    organization = Organization.create(
        organization_code="  ops  ",
        display_name="  Operations Hub  ",
        timezone_name="  Europe/Berlin  ",
        base_currency=" usd ",
        tenant_id="  tenant-1  ",
    )

    assert organization.organization_code == "OPS"
    assert organization.display_name == "Operations Hub"
    assert organization.timezone_name == "Europe/Berlin"
    assert organization.base_currency == "USD"
    assert organization.tenant_id == "tenant-1"

    with pytest.raises(ValidationError) as exc_code:
        Organization.create(
            organization_code=" ",
            display_name="Valid",
            timezone_name="UTC",
            base_currency="EUR",
        )
    assert exc_code.value.code == "ORGANIZATION_CODE_REQUIRED"

    with pytest.raises(ValidationError) as exc_currency:
        Organization.create(
            organization_code="OPS",
            display_name="Valid",
            timezone_name="UTC",
            base_currency=" ",
        )
    assert exc_currency.value.code == "BASE_CURRENCY_REQUIRED"

    with pytest.raises(ValidationError) as exc_historical_currency:
        Organization.create(
            organization_code="OPS",
            display_name="Valid",
            timezone_name="UTC",
            base_currency="BGN",
        )
    assert exc_historical_currency.value.code == "BASE_CURRENCY_INVALID"


def test_organization_service_uses_entity_validation_and_final_state(monkeypatch: pytest.MonkeyPatch):
    service = _make_organization_service(monkeypatch)

    created = service.create_organization(
        organization_code="  default  ",
        display_name="  Default Organization  ",
        timezone_name="  UTC  ",
        base_currency=" eur ",
        is_enabled=True,
    )
    second = service.create_organization(
        organization_code=" north ",
        display_name="  North Division  ",
        timezone_name=" Europe/Berlin ",
        base_currency=" usd ",
        is_enabled=False,
    )

    assert created.organization_code == "DEFAULT"
    assert second.organization_code == "NORTH"
    assert second.display_name == "North Division"
    assert second.base_currency == "USD"

    activated = service.update_organization(
        second.id,
        expected_version=second.version,
        display_name="  North Ops  ",
        is_enabled=True,
    )

    assert activated.display_name == "North Ops"
    assert activated.is_enabled is True
    assert activated.version == 2
    # P10A: enabling `second` never disables `created` -- no mutual exclusion.
    reloaded_first = service._organization_repo.get(created.id)
    assert reloaded_first is not None
    assert reloaded_first.is_enabled is True

    with pytest.raises(ValidationError) as exc_name:
        service.update_organization(
            activated.id,
            expected_version=activated.version,
            display_name=" ",
        )
    assert exc_name.value.code == "ORGANIZATION_NAME_REQUIRED"


def test_site_dto_normalizes_and_validates_fields():
    now = datetime.now(timezone.utc)
    site = Site.create(
        "  org-1  ",
        "  hub  ",
        "  Main Hub  ",
        description="  Central distribution point.  ",
        country="  Germany  ",
        city="  Berlin  ",
        timezone="  Europe/Berlin  ",
        currency_code=" eur ",
        status=" ",
        is_active=False,
        opened_at=now,
        closed_at=now,
        notes="  Keep gate 3 reserved.  ",
    )

    assert site.organization_id == "org-1"
    assert site.site_code == "HUB"
    assert site.name == "Main Hub"
    assert site.description == "Central distribution point."
    assert site.country == "Germany"
    assert site.city == "Berlin"
    assert site.timezone == "Europe/Berlin"
    assert site.currency_code == "EUR"
    assert site.status == "INACTIVE"
    assert site.notes == "Keep gate 3 reserved."

    with pytest.raises(ValidationError) as exc_org:
        Site.create(" ", "HQ", "Headquarters")
    assert exc_org.value.code == "SITE_ORGANIZATION_REQUIRED"

    with pytest.raises(ValidationError) as exc_name:
        Site.create("org-1", "HQ", " ")
    assert exc_name.value.code == "SITE_NAME_REQUIRED"

    with pytest.raises(ValidationError) as exc_currency:
        Site.create("org-1", "HQ", "Headquarters", currency_code="ZZZ")
    assert exc_currency.value.code == "SITE_CURRENCY_INVALID"

    with pytest.raises(ValidationError) as exc_range:
        Site.create(
            "org-1",
            "HQ",
            "Headquarters",
            opened_at=datetime(2026, 7, 25, 10, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc),
        )
    assert exc_range.value.code == "SITE_DATE_RANGE_INVALID"


def test_site_service_uses_entity_validation_and_final_state(monkeypatch: pytest.MonkeyPatch):
    service, organization = _make_site_service(monkeypatch)

    created = service.create_site(
        site_code="  hq  ",
        name="  Headquarters  ",
        city="  Lagos  ",
        country="  Nigeria  ",
        timezone_name=" ",
        currency_code=" ",
        default_calendar_id=" ",
    )

    assert created.organization_id == organization.id
    assert created.site_code == "HQ"
    assert created.name == "Headquarters"
    assert created.city == "Lagos"
    assert created.country == "Nigeria"
    assert created.timezone == "UTC"
    assert created.currency_code == "EUR"
    assert created.default_calendar_id == "default"
    assert created.status == "ACTIVE"

    updated = service.update_site(
        created.id,
        expected_version=created.version,
        name="  North Hub  ",
        city="  Berlin  ",
        country="  Germany  ",
        site_type="  warehouse  ",
        is_active=False,
    )

    assert updated.name == "North Hub"
    assert updated.city == "Berlin"
    assert updated.country == "Germany"
    assert updated.site_type == "warehouse"
    assert updated.status == "INACTIVE"
    assert updated.closed_at is not None
    assert updated.version == 2

    reopened = service.update_site(
        updated.id,
        expected_version=updated.version,
        is_active=True,
    )

    assert reopened.status == "ACTIVE"
    assert reopened.closed_at is None
    assert reopened.version == 3

    with pytest.raises(ValidationError) as exc_name:
        service.update_site(
            reopened.id,
            expected_version=reopened.version,
            name=" ",
        )
    assert exc_name.value.code == "SITE_NAME_REQUIRED"
