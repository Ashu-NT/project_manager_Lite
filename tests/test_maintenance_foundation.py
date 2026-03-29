from __future__ import annotations

from core.modules.maintenance_management.domain import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from core.modules.maintenance_management.services import (
    MaintenanceLocationService,
    MaintenanceSystemService,
)
from core.modules.maintenance_management.support import coerce_priority, coerce_trigger_mode
from core.platform.auth.session import UserSessionContext, UserSessionPrincipal
from core.platform.common.exceptions import ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.notifications.domain_events import domain_events
from core.platform.org.domain import Organization, Site


class _OrgRepo(OrganizationRepository):
    def __init__(self, organization: Organization) -> None:
        self.organization = organization

    def add(self, organization: Organization) -> None:
        self.organization = organization

    def update(self, organization: Organization) -> None:
        self.organization = organization

    def get(self, organization_id: str):
        return self.organization if self.organization.id == organization_id else None

    def get_by_code(self, organization_code: str):
        return self.organization if self.organization.organization_code == organization_code else None

    def get_active(self):
        return self.organization

    def list_all(self, *, active_only=None):
        rows = [self.organization]
        if active_only is None:
            return rows
        return [row for row in rows if row.is_active == bool(active_only)]


class _SiteRepo(SiteRepository):
    def __init__(self, sites: list[Site]) -> None:
        self._sites = {site.id: site for site in sites}

    def add(self, site: Site) -> None:
        self._sites[site.id] = site

    def update(self, site: Site) -> None:
        self._sites[site.id] = site

    def get(self, site_id: str):
        return self._sites.get(site_id)

    def get_by_code(self, organization_id: str, site_code: str):
        for site in self._sites.values():
            if site.organization_id == organization_id and site.site_code == site_code:
                return site
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None):
        rows = [site for site in self._sites.values() if site.organization_id == organization_id]
        if active_only is None:
            return rows
        return [site for site in rows if site.is_active == bool(active_only)]


class _LocationRepo(MaintenanceLocationRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceLocation] = {}

    def add(self, location: MaintenanceLocation) -> None:
        self._rows[location.id] = location

    def update(self, location: MaintenanceLocation) -> None:
        self._rows[location.id] = location

    def get(self, location_id: str):
        return self._rows.get(location_id)

    def get_by_code(self, organization_id: str, location_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.location_code == location_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, site_id=None, parent_location_id=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if parent_location_id is not None:
            rows = [row for row in rows if row.parent_location_id == parent_location_id]
        return rows


class _SystemRepo(MaintenanceSystemRepository):
    def __init__(self) -> None:
        self._rows = {}

    def add(self, system) -> None:
        self._rows[system.id] = system

    def update(self, system) -> None:
        self._rows[system.id] = system

    def get(self, system_id: str):
        return self._rows.get(system_id)

    def get_by_code(self, organization_id: str, system_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.system_code == system_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, site_id=None, location_id=None, parent_system_id=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if parent_system_id is not None:
            rows = [row for row in rows if row.parent_system_id == parent_system_id]
        return rows


def _user_session() -> UserSessionContext:
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="u1",
            username="maintenance.admin",
            display_name="Maintenance Admin",
            role_names=frozenset({"maintenance_admin"}),
            permissions=frozenset({"maintenance.read", "maintenance.manage"}),
        )
    )
    return user_session


def test_maintenance_location_service_creates_searches_and_emits_domain_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    service = MaintenanceLocationService(
        session,
        _LocationRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    location = service.create_location(
        site_id=site.id,
        location_code="area-1",
        name="Area 1",
        location_type="AREA",
    )

    assert location.location_code == "AREA-1"
    assert location.status == MaintenanceLifecycleStatus.ACTIVE
    assert location.criticality == MaintenanceCriticality.MEDIUM
    assert service.search_locations(search_text="area")[0].id == location.id
    assert captured[-1].entity_type == "maintenance_location"
    assert captured[-1].scope_code == "maintenance_management"
    assert captured[-1].source_event == "maintenance_locations_changed"


def test_maintenance_location_service_rejects_parent_from_other_site(session) -> None:
    organization = Organization.create("ORG", "Org")
    site_a = Site.create(organization.id, "A", "Site A")
    site_b = Site.create(organization.id, "B", "Site B")
    location_repo = _LocationRepo()
    parent = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site_a.id,
        location_code="AREA-A",
        name="Area A",
    )
    location_repo.add(parent)
    service = MaintenanceLocationService(
        session,
        location_repo,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site_a, site_b]),
        user_session=_user_session(),
    )

    try:
        service.create_location(
            site_id=site_b.id,
            location_code="AREA-B",
            name="Area B",
            parent_location_id=parent.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_LOCATION_SITE_MISMATCH"
    else:
        raise AssertionError("Expected site mismatch validation error.")


def test_maintenance_system_service_creates_systems_and_validates_location_scope(session) -> None:
    organization = Organization.create("ORG", "Org")
    site_a = Site.create(organization.id, "A", "Site A")
    site_b = Site.create(organization.id, "B", "Site B")
    location_repo = _LocationRepo()
    valid_location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site_a.id,
        location_code="AREA-A",
        name="Area A",
    )
    other_site_location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site_b.id,
        location_code="AREA-B",
        name="Area B",
    )
    location_repo.add(valid_location)
    location_repo.add(other_site_location)
    service = MaintenanceSystemService(
        session,
        _SystemRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site_a, site_b]),
        location_repo=location_repo,
        user_session=_user_session(),
    )

    system = service.create_system(
        site_id=site_a.id,
        system_code="sys-001",
        name="Cooling Water",
        location_id=valid_location.id,
        system_type="UTILITY",
    )

    assert system.system_code == "SYS-001"
    assert service.find_system_by_code("SYS-001").id == system.id
    assert service.search_systems(search_text="cooling")[0].id == system.id

    try:
        service.create_system(
            site_id=site_a.id,
            system_code="sys-002",
            name="Invalid System",
            location_id=other_site_location.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_SYSTEM_SITE_MISMATCH"
    else:
        raise AssertionError("Expected site mismatch validation error.")


def test_maintenance_support_helpers_cover_priority_and_trigger_modes() -> None:
    assert coerce_priority("emergency").value == "EMERGENCY"
    assert coerce_trigger_mode("hybrid").value == "HYBRID"
