from __future__ import annotations

from datetime import date

from src.core.modules.maintenance import MaintenanceAssetService, MaintenanceSystemService
from src.core.modules.maintenance.domain import MaintenanceLocation
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.site.contracts import SiteRepository
from src.core.shared.events.domain_events import domain_events
from src.core.platform.org.domain import Organization
from src.core.platform.site.domain import Site
from src.core.platform.party.domain import Party, PartyType
from src.core.platform.party.contracts import PartyRepository


class _OrgRepo(OrganizationRepository):
    def __init__(self, organization):
        self.organization = organization
    def add(self, organization): self.organization = organization
    def update(self, organization): self.organization = organization
    def get(self, organization_id):
        return self.organization if self.organization.id == organization_id else None
    def get_by_code(self, organization_code):
        return self.organization if self.organization.organization_code == organization_code else None
    def get_active(self): return self.organization
    def list_all(self, *, active_only=None):
        rows = [self.organization]
        return rows if active_only is None else [r for r in rows if r.is_active == bool(active_only)]
    def get_for_tenant(self, organization_id, tenant_id):
        if self.organization.tenant_id != tenant_id:
            return None
        return self.get(organization_id)
    def get_by_code_for_tenant(self, organization_code, tenant_id):
        if self.organization.tenant_id != tenant_id:
            return None
        return self.get_by_code(organization_code)
    def get_active_for_tenant(self, tenant_id):
        return self.organization if self.organization.tenant_id == tenant_id else None
    def list_for_tenant(self, tenant_id, *, active_only=None):
        rows = [self.organization] if self.organization.tenant_id == tenant_id else []
        return rows if active_only is None else [r for r in rows if r.is_active == bool(active_only)]


class _TenantContext:
    def __init__(self, organization):
        self.organization = organization
    def require_context(self, *, operation_label):
        return type("TenantContext", (), {"organization_id": self.organization.id, "organization": self.organization})()
    def require_organization_context(self, *, operation_label):
        return self.require_context(operation_label=operation_label)
    def require_active_organization_id(self, *, operation_label): return self.organization.id
    def get_active_organization_id(self): return self.organization.id
    def get_active_tenant_id(self): return self.organization.tenant_id


class _SiteRepo(SiteRepository):
    def __init__(self, sites):
        self._sites = {s.id: s for s in sites}
    def add(self, site): self._sites[site.id] = site
    def update(self, site): self._sites[site.id] = site
    def get(self, site_id): return self._sites.get(site_id)
    def get_by_code(self, organization_id, site_code):
        return next((s for s in self._sites.values() if s.organization_id == organization_id and s.site_code == site_code), None)
    def list_for_organization(self, organization_id, *, active_only=None):
        rows = [s for s in self._sites.values() if s.organization_id == organization_id]
        return rows if active_only is None else [s for s in rows if s.is_active == bool(active_only)]


class _LocationRepo(MaintenanceLocationRepository):
    def __init__(self): self._rows: dict[str, MaintenanceLocation] = {}
    def add(self, location): self._rows[location.id] = location
    def update(self, location): self._rows[location.id] = location
    def get(self, location_id): return self._rows.get(location_id)
    def get_by_code(self, organization_id, location_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.location_code == location_code), None)
    def list_for_organization(self, organization_id, *, active_only=None, site_id=None, parent_location_id=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if active_only is not None: rows = [r for r in rows if r.is_active == bool(active_only)]
        if site_id is not None: rows = [r for r in rows if r.site_id == site_id]
        if parent_location_id is not None: rows = [r for r in rows if r.parent_location_id == parent_location_id]
        return rows


class _SystemRepo(MaintenanceSystemRepository):
    def __init__(self): self._rows = {}
    def add(self, system): self._rows[system.id] = system
    def update(self, system): self._rows[system.id] = system
    def get(self, system_id): return self._rows.get(system_id)
    def get_by_code(self, organization_id, system_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.system_code == system_code), None)
    def list_for_organization(self, organization_id, *, active_only=None, site_id=None, location_id=None, parent_system_id=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if active_only is not None: rows = [r for r in rows if r.is_active == bool(active_only)]
        if site_id is not None: rows = [r for r in rows if r.site_id == site_id]
        if location_id is not None: rows = [r for r in rows if r.location_id == location_id]
        if parent_system_id is not None: rows = [r for r in rows if r.parent_system_id == parent_system_id]
        return rows


class _AssetRepo(MaintenanceAssetRepository):
    def __init__(self): self._rows = {}
    def add(self, asset): self._rows[asset.id] = asset
    def update(self, asset): self._rows[asset.id] = asset
    def get(self, asset_id): return self._rows.get(asset_id)
    def get_by_code(self, organization_id, asset_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.asset_code == asset_code), None)
    def list_for_organization(self, organization_id, *, active_only=None, site_id=None, location_id=None, system_id=None, parent_asset_id=None, asset_category=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if active_only is not None: rows = [r for r in rows if r.is_active == bool(active_only)]
        if site_id is not None: rows = [r for r in rows if r.site_id == site_id]
        if location_id is not None: rows = [r for r in rows if r.location_id == location_id]
        if system_id is not None: rows = [r for r in rows if r.system_id == system_id]
        if parent_asset_id is not None: rows = [r for r in rows if r.parent_asset_id == parent_asset_id]
        if asset_category is not None: rows = [r for r in rows if r.asset_category == asset_category]
        return rows


class _PartyRepo(PartyRepository):
    def __init__(self, parties=None): self._rows = {p.id: p for p in parties or []}
    def add(self, party): self._rows[party.id] = party
    def update(self, party): self._rows[party.id] = party
    def get(self, party_id): return self._rows.get(party_id)
    def get_by_code(self, organization_id, party_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.party_code == party_code), None)
    def list_for_organization(self, organization_id, *, active_only=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        return rows if active_only is None else [r for r in rows if r.is_active == bool(active_only)]


def _user_session() -> UserSessionContext:
    user_session = UserSessionContext()
    user_session.set_principal(UserSessionPrincipal(
        user_id="u1", username="maintenance.admin", display_name="Maintenance Admin",
        role_names=frozenset({"maintenance_admin"}),
        permissions=frozenset({"maintenance.read", "maintenance.manage"}),
    ))
    return user_session


def test_maintenance_asset_service_creates_assets_and_emits_domain_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location_repo = _LocationRepo()
    system_repo = _SystemRepo()
    asset_repo = _AssetRepo()
    manufacturer = Party.create(organization_id=organization.id, party_code="MFG-001", party_name="Maker Co", party_type=PartyType.MANUFACTURER)
    supplier = Party.create(organization_id=organization.id, party_code="SUP-001", party_name="Supply Co", party_type=PartyType.SUPPLIER)
    location = MaintenanceLocation.create(organization_id=organization.id, site_id=site.id, location_code="AREA-A", name="Area A")
    location_repo.add(location)
    spare_location = MaintenanceLocation.create(organization_id=organization.id, site_id=site.id, location_code="AREA-B", name="Area B")
    location_repo.add(spare_location)
    process_system = MaintenanceSystemService(
        session, system_repo, organization_repo=_OrgRepo(organization), site_repo=_SiteRepo([site]),
        location_repo=location_repo, tenant_context_service=_TenantContext(organization), user_session=_user_session(),
    ).create_system(site_id=site.id, system_code="STEAM-MAIN", name="Steam Main", location_id=location.id)
    service = MaintenanceAssetService(
        session, asset_repo, organization_repo=_OrgRepo(organization), site_repo=_SiteRepo([site]),
        location_repo=location_repo, system_repo=system_repo, party_repo=_PartyRepo([manufacturer, supplier]),
        tenant_context_service=_TenantContext(organization), user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    asset = service.create_asset(
        site_id=site.id, location_id=location.id, asset_code="pump-001", name="Boiler Feed Pump",
        system_id=process_system.id, asset_type="PUMP", asset_category="ROTATING",
        manufacturer_party_id=manufacturer.id, supplier_party_id=supplier.id,
        install_date=date(2024, 1, 10), commission_date=date(2024, 1, 15),
        warranty_start=date(2024, 1, 15), warranty_end=date(2026, 1, 15),
        expected_life_years=12, replacement_cost="12500.50", maintenance_strategy="CBM",
        service_level="CRITICAL", requires_shutdown_for_major_work=True,
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
    location_a = MaintenanceLocation.create(organization_id=organization.id, site_id=site_a.id, location_code="AREA-A", name="Area A")
    location_b = MaintenanceLocation.create(organization_id=organization.id, site_id=site_b.id, location_code="AREA-B", name="Area B")
    location_repo.add(location_a)
    location_repo.add(location_b)
    system = MaintenanceSystemService(
        session, system_repo, organization_repo=_OrgRepo(organization), site_repo=_SiteRepo([site_a, site_b]),
        location_repo=location_repo, tenant_context_service=_TenantContext(organization), user_session=_user_session(),
    ).create_system(site_id=site_b.id, system_code="REMOTE-SYS", name="Remote System", location_id=location_b.id)
    service = MaintenanceAssetService(
        session, _AssetRepo(), organization_repo=_OrgRepo(organization), site_repo=_SiteRepo([site_a, site_b]),
        location_repo=location_repo, system_repo=system_repo, party_repo=_PartyRepo(),
        tenant_context_service=_TenantContext(organization), user_session=_user_session(),
    )

    try:
        service.create_asset(site_id=site_a.id, location_id=location_a.id, asset_code="BAD-ASSET", name="Bad Asset", system_id=system.id)
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_ASSET_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance asset site mismatch validation error.")
