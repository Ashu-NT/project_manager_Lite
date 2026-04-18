from __future__ import annotations

from datetime import date

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderTask,
    MaintenanceWorkRequest,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetRepository,
    MaintenanceAssetComponentRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkRequestRepository,
)
from core.modules.maintenance_management.services import (
    MaintenanceAssetService,
    MaintenanceAssetComponentService,
    MaintenanceLocationService,
    MaintenanceSystemService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkRequestService,
)
from src.core.platform.auth.domain import UserAccount
from core.modules.maintenance_management.support import coerce_priority, coerce_trigger_mode
from src.core.platform.auth.contracts import UserRepository
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from core.platform.common.exceptions import ValidationError
from src.core.platform.org.contracts import OrganizationRepository, SiteRepository
from core.platform.notifications.domain_events import domain_events
from src.core.platform.org.domain import Organization, Site
from core.platform.party.domain import Party, PartyType
from core.platform.party.interfaces import PartyRepository


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


class _AssetRepo(MaintenanceAssetRepository):
    def __init__(self) -> None:
        self._rows = {}

    def add(self, asset) -> None:
        self._rows[asset.id] = asset

    def update(self, asset) -> None:
        self._rows[asset.id] = asset

    def get(self, asset_id: str):
        return self._rows.get(asset_id)

    def get_by_code(self, organization_id: str, asset_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.asset_code == asset_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only=None,
        site_id=None,
        location_id=None,
        system_id=None,
        parent_asset_id=None,
        asset_category=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if parent_asset_id is not None:
            rows = [row for row in rows if row.parent_asset_id == parent_asset_id]
        if asset_category is not None:
            rows = [row for row in rows if row.asset_category == asset_category]
        return rows


class _ComponentRepo(MaintenanceAssetComponentRepository):
    def __init__(self) -> None:
        self._rows = {}

    def add(self, component) -> None:
        self._rows[component.id] = component

    def update(self, component) -> None:
        self._rows[component.id] = component

    def get(self, component_id: str):
        return self._rows.get(component_id)

    def get_by_code(self, organization_id: str, component_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.component_code == component_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only=None,
        asset_id=None,
        parent_component_id=None,
        component_type=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if parent_component_id is not None:
            rows = [row for row in rows if row.parent_component_id == parent_component_id]
        if component_type is not None:
            rows = [row for row in rows if row.component_type == component_type]
        return rows


class _PartyRepo(PartyRepository):
    def __init__(self, parties: list[Party] | None = None) -> None:
        self._rows = {party.id: party for party in parties or []}

    def add(self, party: Party) -> None:
        self._rows[party.id] = party

    def update(self, party: Party) -> None:
        self._rows[party.id] = party

    def get(self, party_id: str):
        return self._rows.get(party_id)

    def get_by_code(self, organization_id: str, party_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.party_code == party_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is None:
            return rows
        return [row for row in rows if row.is_active == bool(active_only)]


class _UserRepo(UserRepository):
    def __init__(self, users: list[UserAccount] | None = None) -> None:
        self._rows = {user.id: user for user in users or []}

    def add(self, user: UserAccount) -> None:
        self._rows[user.id] = user

    def update(self, user: UserAccount) -> None:
        self._rows[user.id] = user

    def get(self, user_id: str):
        return self._rows.get(user_id)

    def get_by_username(self, username: str):
        normalized = (username or "").strip().lower()
        for row in self._rows.values():
            if row.username == normalized:
                return row
        return None

    def get_by_federated_identity(self, identity_provider: str, federated_subject: str):
        for row in self._rows.values():
            if row.identity_provider == identity_provider and row.federated_subject == federated_subject:
                return row
        return None

    def list_all(self):
        return list(self._rows.values())


class _WorkRequestRepo(MaintenanceWorkRequestRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceWorkRequest] = {}

    def add(self, work_request: MaintenanceWorkRequest) -> None:
        self._rows[work_request.id] = work_request

    def update(self, work_request: MaintenanceWorkRequest) -> None:
        work_request.version += 1
        self._rows[work_request.id] = work_request

    def get(self, work_request_id: str):
        return self._rows.get(work_request_id)

    def get_by_code(self, organization_id: str, work_request_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.work_request_code == work_request_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        location_id=None,
        status=None,
        priority=None,
        requested_by_user_id=None,
        triaged_by_user_id=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if component_id is not None:
            rows = [row for row in rows if row.component_id == component_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if priority is not None:
            rows = [row for row in rows if row.priority == priority]
        if requested_by_user_id is not None:
            rows = [row for row in rows if row.requested_by_user_id == requested_by_user_id]
        if triaged_by_user_id is not None:
            rows = [row for row in rows if row.triaged_by_user_id == triaged_by_user_id]
        return rows


class _WorkOrderRepo(MaintenanceWorkOrderRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceWorkOrder] = {}

    def add(self, work_order: MaintenanceWorkOrder) -> None:
        self._rows[work_order.id] = work_order

    def update(self, work_order: MaintenanceWorkOrder) -> None:
        work_order.version += 1
        self._rows[work_order.id] = work_order

    def get(self, work_order_id: str):
        return self._rows.get(work_order_id)

    def get_by_code(self, organization_id: str, work_order_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.work_order_code == work_order_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        location_id=None,
        status=None,
        priority=None,
        assigned_employee_id=None,
        assigned_team_id=None,
        planner_user_id=None,
        supervisor_user_id=None,
        work_order_type=None,
        is_preventive=None,
        is_emergency=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if component_id is not None:
            rows = [row for row in rows if row.component_id == component_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if location_id is not None:
            rows = [row for row in rows if row.location_id == location_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if priority is not None:
            rows = [row for row in rows if row.priority == priority]
        if assigned_employee_id is not None:
            rows = [row for row in rows if row.assigned_employee_id == assigned_employee_id]
        if assigned_team_id is not None:
            rows = [row for row in rows if row.assigned_team_id == assigned_team_id]
        if planner_user_id is not None:
            rows = [row for row in rows if row.planner_user_id == planner_user_id]
        if supervisor_user_id is not None:
            rows = [row for row in rows if row.supervisor_user_id == supervisor_user_id]
        if work_order_type is not None:
            rows = [row for row in rows if row.work_order_type == work_order_type]
        if is_preventive is not None:
            rows = [row for row in rows if row.is_preventive == bool(is_preventive)]
        if is_emergency is not None:
            rows = [row for row in rows if row.is_emergency == bool(is_emergency)]
        return rows


class _WorkOrderTaskRepo(MaintenanceWorkOrderTaskRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceWorkOrderTask] = {}

    def add(self, work_order_task: MaintenanceWorkOrderTask) -> None:
        self._rows[work_order_task.id] = work_order_task

    def update(self, work_order_task: MaintenanceWorkOrderTask) -> None:
        work_order_task.version += 1
        self._rows[work_order_task.id] = work_order_task

    def get(self, work_order_task_id: str):
        return self._rows.get(work_order_task_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id=None,
        status=None,
        assigned_employee_id=None,
        assigned_team_id=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if work_order_id is not None:
            rows = [row for row in rows if row.work_order_id == work_order_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if assigned_employee_id is not None:
            rows = [row for row in rows if row.assigned_employee_id == assigned_employee_id]
        if assigned_team_id is not None:
            rows = [row for row in rows if row.assigned_team_id == assigned_team_id]
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


def test_maintenance_asset_service_creates_assets_and_emits_domain_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location_repo = _LocationRepo()
    system_repo = _SystemRepo()
    asset_repo = _AssetRepo()
    manufacturer = Party.create(
        organization_id=organization.id,
        party_code="MFG-001",
        party_name="Maker Co",
        party_type=PartyType.MANUFACTURER,
    )
    supplier = Party.create(
        organization_id=organization.id,
        party_code="SUP-001",
        party_name="Supply Co",
        party_type=PartyType.SUPPLIER,
    )
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    location_repo.add(location)
    spare_location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-B",
        name="Area B",
    )
    location_repo.add(spare_location)
    process_system = MaintenanceSystemService(
        session,
        system_repo,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        location_repo=location_repo,
        user_session=_user_session(),
    ).create_system(
        site_id=site.id,
        system_code="STEAM-MAIN",
        name="Steam Main",
        location_id=location.id,
    )
    service = MaintenanceAssetService(
        session,
        asset_repo,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        location_repo=location_repo,
        system_repo=system_repo,
        party_repo=_PartyRepo([manufacturer, supplier]),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    asset = service.create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="pump-001",
        name="Boiler Feed Pump",
        system_id=process_system.id,
        asset_type="PUMP",
        asset_category="ROTATING",
        manufacturer_party_id=manufacturer.id,
        supplier_party_id=supplier.id,
        install_date=date(2024, 1, 10),
        commission_date=date(2024, 1, 15),
        warranty_start=date(2024, 1, 15),
        warranty_end=date(2026, 1, 15),
        expected_life_years=12,
        replacement_cost="12500.50",
        maintenance_strategy="CBM",
        service_level="CRITICAL",
        requires_shutdown_for_major_work=True,
    )

    assert asset.asset_code == "PUMP-001"
    assert asset.system_id == process_system.id
    assert asset.asset_category == "ROTATING"
    assert asset.requires_shutdown_for_major_work is True
    assert service.find_asset_by_code("PUMP-001").id == asset.id
    assert service.search_assets(search_text="feed pump")[0].id == asset.id
    assert captured[-1].entity_type == "maintenance_asset"
    assert captured[-1].source_event == "maintenance_assets_changed"


def test_maintenance_asset_service_rejects_cross_site_system_reference(session) -> None:
    organization = Organization.create("ORG", "Org")
    site_a = Site.create(organization.id, "A", "Site A")
    site_b = Site.create(organization.id, "B", "Site B")
    location_repo = _LocationRepo()
    system_repo = _SystemRepo()
    location_a = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site_a.id,
        location_code="AREA-A",
        name="Area A",
    )
    location_b = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site_b.id,
        location_code="AREA-B",
        name="Area B",
    )
    location_repo.add(location_a)
    location_repo.add(location_b)
    system = MaintenanceSystemService(
        session,
        system_repo,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site_a, site_b]),
        location_repo=location_repo,
        user_session=_user_session(),
    ).create_system(
        site_id=site_b.id,
        system_code="REMOTE-SYS",
        name="Remote System",
        location_id=location_b.id,
    )
    service = MaintenanceAssetService(
        session,
        _AssetRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site_a, site_b]),
        location_repo=location_repo,
        system_repo=system_repo,
        party_repo=_PartyRepo(),
        user_session=_user_session(),
    )

    try:
        service.create_asset(
            site_id=site_a.id,
            location_id=location_a.id,
            asset_code="BAD-ASSET",
            name="Bad Asset",
            system_id=system.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_ASSET_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance asset site mismatch validation error.")


def test_maintenance_asset_component_service_creates_components_and_emits_domain_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location_repo = _LocationRepo()
    system_repo = _SystemRepo()
    asset_repo = _AssetRepo()
    component_repo = _ComponentRepo()
    supplier = Party.create(
        organization_id=organization.id,
        party_code="SUP-COMP",
        party_name="Component Supplier",
        party_type=PartyType.SUPPLIER,
    )
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    location_repo.add(location)
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="PUMP-001",
        name="Process Pump",
    )
    asset_repo.add(asset)
    service = MaintenanceAssetComponentService(
        session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=_OrgRepo(organization),
        party_repo=_PartyRepo([supplier]),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    component = service.create_component(
        asset_id=asset.id,
        component_code="seal-001",
        name="Seal Cartridge",
        component_type="SEAL",
        supplier_party_id=supplier.id,
        expected_life_hours=12000,
        is_critical_component=True,
    )

    assert component.component_code == "SEAL-001"
    assert component.asset_id == asset.id
    assert component.component_type == "SEAL"
    assert component.is_critical_component is True
    assert service.find_component_by_code("SEAL-001").id == component.id
    assert service.search_components(search_text="seal")[0].id == component.id
    assert captured[-1].entity_type == "maintenance_asset_component"
    assert captured[-1].source_event == "maintenance_asset_components_changed"


def test_maintenance_asset_component_service_rejects_parent_from_other_asset(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-A",
        name="Area A",
    )
    asset_repo = _AssetRepo()
    first_asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-A",
        name="Asset A",
    )
    second_asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-B",
        name="Asset B",
    )
    asset_repo.add(first_asset)
    asset_repo.add(second_asset)
    component_repo = _ComponentRepo()
    parent = MaintenanceAssetComponent.create(
        organization_id=organization.id,
        asset_id=first_asset.id,
        component_code="COMP-A",
        name="Component A",
    )
    component_repo.add(parent)
    service = MaintenanceAssetComponentService(
        session,
        component_repo,
        asset_repo=asset_repo,
        organization_repo=_OrgRepo(organization),
        party_repo=_PartyRepo(),
        user_session=_user_session(),
    )

    try:
        service.create_component(
            asset_id=second_asset.id,
            component_code="COMP-B",
            name="Component B",
            parent_component_id=parent.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_COMPONENT_ASSET_MISMATCH"
    else:
        raise AssertionError("Expected maintenance component asset mismatch validation error.")


def test_maintenance_work_request_service_creates_and_triages_requests(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-REQ",
        name="Request Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-REQ",
        name="Request Asset",
    )
    current_user = UserAccount.create("maintenance.admin", "hash", display_name="Maintenance Admin")
    current_user.id = "u1"
    work_request_repo = _WorkRequestRepo()
    service = MaintenanceWorkRequestService(
        session,
        work_request_repo,
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        user_repo=_UserRepo([current_user]),
        asset_repo=_AssetRepo(),
        component_repo=_ComponentRepo(),
        location_repo=_LocationRepo(),
        system_repo=_SystemRepo(),
        user_session=_user_session(),
    )
    service._asset_repo.add(asset)
    service._location_repo.add(location)
    captured = []
    domain_events.domain_changed.connect(captured.append)

    request = service.create_work_request(
        site_id=site.id,
        work_request_code="wr-001",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        title="Pump leaking",
        priority="high",
    )
    triaged = service.update_work_request(
        request.id,
        status="TRIAGED",
        expected_version=request.version,
    )

    assert request.work_request_code == "WR-001"
    assert request.source_type.value == "MANUAL"
    assert request.request_type == "BREAKDOWN"
    assert request.requested_by_user_id == "u1"
    assert request.requested_by_name_snapshot == "Maintenance Admin"
    assert triaged.status.value == "TRIAGED"
    assert triaged.triaged_by_user_id == "u1"
    assert triaged.triaged_at is not None
    assert captured[-1].entity_type == "maintenance_work_request"
    assert captured[-1].source_event == "maintenance_work_requests_changed"


def test_maintenance_work_order_service_creates_from_request_and_tracks_status(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-WO",
        name="Order Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-WO",
        name="Work Order Asset",
    )
    work_request = MaintenanceWorkRequest.create(
        organization_id=organization.id,
        site_id=site.id,
        work_request_code="WR-WO-001",
        source_type="MANUAL",
        request_type="BREAKDOWN",
        asset_id=asset.id,
        location_id=location.id,
        title="Repair pump",
        description="Repair leaking pump",
        priority="HIGH",
    )
    asset_repo = _AssetRepo()
    asset_repo.add(asset)
    location_repo = _LocationRepo()
    location_repo.add(location)
    work_request_repo = _WorkRequestRepo()
    work_request_repo.add(work_request)
    service = MaintenanceWorkOrderService(
        session,
        _WorkOrderRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        user_repo=_UserRepo(),
        asset_repo=asset_repo,
        component_repo=_ComponentRepo(),
        location_repo=location_repo,
        system_repo=_SystemRepo(),
        work_request_repo=work_request_repo,
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    work_order = service.create_work_order(
        site_id=site.id,
        work_order_code="wo-001",
        work_order_type="corrective",
        source_type="work_request",
        source_id=work_request.id,
        assigned_team_id="TEAM-A",
    )
    planned = service.update_work_order(work_order.id, status="PLANNED", expected_version=work_order.version)
    released = service.update_work_order(work_order.id, status="RELEASED", expected_version=planned.version)
    started = service.update_work_order(work_order.id, status="IN_PROGRESS", expected_version=released.version)
    completed = service.update_work_order(work_order.id, status="COMPLETED", expected_version=started.version)
    closed = service.update_work_order(work_order.id, status="CLOSED", expected_version=completed.version)

    assert work_order.work_order_code == "WO-001"
    assert work_order.work_order_type.value == "CORRECTIVE"
    assert work_order.asset_id == asset.id
    assert work_order.location_id == location.id
    assert work_order.title == "Repair pump"
    assert work_order.assigned_team_id == "TEAM-A"
    assert started.actual_start is not None
    assert completed.actual_end is not None
    assert closed.closed_at is not None
    assert closed.closed_by_user_id == "u1"
    assert captured[-1].entity_type == "maintenance_work_order"
    assert captured[-1].source_event == "maintenance_work_orders_changed"


def test_maintenance_work_order_task_service_creates_and_progresses_tasks(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-TASK",
        name="Task Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-TASK",
        name="Task Asset",
    )
    work_order = MaintenanceWorkOrder.create(
        organization_id=organization.id,
        site_id=site.id,
        work_order_code="WO-TASK-001",
        work_order_type="CORRECTIVE",
        source_type="MANUAL",
        asset_id=asset.id,
        location_id=location.id,
        title="Repair fan",
    )
    work_order_repo = _WorkOrderRepo()
    work_order_repo.add(work_order)
    service = MaintenanceWorkOrderTaskService(
        session,
        _WorkOrderTaskRepo(),
        organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo,
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    task = service.create_task(
        work_order_id=work_order.id,
        task_name="Isolate power",
        assigned_team_id="TEAM-LOCKOUT",
        estimated_minutes=30,
    )
    created_status = task.status.value
    started = service.update_task(task.id, status="IN_PROGRESS", expected_version=task.version)
    completed = service.update_task(started.id, status="COMPLETED", actual_minutes=28, expected_version=started.version)

    assert task.sequence_no == 1
    assert created_status == "NOT_STARTED"
    assert task.assigned_team_id == "TEAM-LOCKOUT"
    assert started.started_at is not None
    assert completed.completed_at is not None
    assert completed.actual_minutes == 28
    assert captured[-1].entity_type == "maintenance_work_order_task"
    assert captured[-1].source_event == "maintenance_work_order_tasks_changed"


def test_maintenance_support_helpers_cover_priority_and_trigger_modes() -> None:
    assert coerce_priority("emergency").value == "EMERGENCY"
    assert coerce_trigger_mode("hybrid").value == "HYBRID"
