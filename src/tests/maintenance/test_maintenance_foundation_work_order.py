from __future__ import annotations

from src.core.modules.maintenance import MaintenanceWorkOrderService, MaintenanceWorkOrderTaskService
from src.core.modules.maintenance.domain import (
    MaintenanceAsset, MaintenanceLocation, MaintenanceWorkOrder, MaintenanceWorkOrderTask, MaintenanceWorkRequest,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenanceAssetComponentRepository, MaintenanceAssetRepository, MaintenanceLocationRepository,
    MaintenanceSystemRepository, MaintenanceWorkOrderRepository, MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkRequestRepository,
)
from src.core.modules.maintenance.application.common.support import coerce_priority, coerce_trigger_mode
from src.core.platform.auth.domain import UserAccount
from src.core.platform.auth.contracts import UserRepository
from src.core.platform.auth.domain.session import UserSessionContext, UserSessionPrincipal
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.site.contracts import SiteRepository
from src.core.shared.events.domain_events import domain_events
from src.core.platform.org.domain import Organization
from src.core.platform.site.domain import Site


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


class _ComponentRepo(MaintenanceAssetComponentRepository):
    def __init__(self): self._rows = {}
    def add(self, component): self._rows[component.id] = component
    def update(self, component): self._rows[component.id] = component
    def get(self, component_id): return self._rows.get(component_id)
    def get_by_code(self, organization_id, component_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.component_code == component_code), None)
    def list_for_organization(self, organization_id, *, active_only=None, asset_id=None, parent_component_id=None, component_type=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if active_only is not None: rows = [r for r in rows if r.is_active == bool(active_only)]
        if asset_id is not None: rows = [r for r in rows if r.asset_id == asset_id]
        if parent_component_id is not None: rows = [r for r in rows if r.parent_component_id == parent_component_id]
        if component_type is not None: rows = [r for r in rows if r.component_type == component_type]
        return rows


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


class _UserRepo(UserRepository):
    def __init__(self, users=None): self._rows = {u.id: u for u in users or []}
    def add(self, user): self._rows[user.id] = user
    def update(self, user): self._rows[user.id] = user
    def get(self, user_id): return self._rows.get(user_id)
    def get_by_username(self, username):
        normalized = (username or "").strip().lower()
        return next((r for r in self._rows.values() if r.username == normalized), None)
    def get_by_federated_identity(self, identity_provider, federated_subject):
        return next((r for r in self._rows.values() if r.identity_provider == identity_provider and r.federated_subject == federated_subject), None)
    def list_all(self): return list(self._rows.values())


class _WorkRequestRepo(MaintenanceWorkRequestRepository):
    def __init__(self): self._rows: dict[str, MaintenanceWorkRequest] = {}
    def add(self, work_request): self._rows[work_request.id] = work_request
    def update(self, work_request):
        work_request.version += 1
        self._rows[work_request.id] = work_request
    def get(self, work_request_id): return self._rows.get(work_request_id)
    def get_by_code(self, organization_id, work_request_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.work_request_code == work_request_code), None)
    def list_for_organization(self, organization_id, *, site_id=None, asset_id=None, component_id=None, system_id=None, location_id=None, status=None, priority=None, requested_by_user_id=None, triaged_by_user_id=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if site_id is not None: rows = [r for r in rows if r.site_id == site_id]
        if asset_id is not None: rows = [r for r in rows if r.asset_id == asset_id]
        if component_id is not None: rows = [r for r in rows if r.component_id == component_id]
        if system_id is not None: rows = [r for r in rows if r.system_id == system_id]
        if location_id is not None: rows = [r for r in rows if r.location_id == location_id]
        if status is not None: rows = [r for r in rows if r.status == status]
        if priority is not None: rows = [r for r in rows if r.priority == priority]
        if requested_by_user_id is not None: rows = [r for r in rows if r.requested_by_user_id == requested_by_user_id]
        if triaged_by_user_id is not None: rows = [r for r in rows if r.triaged_by_user_id == triaged_by_user_id]
        return rows


class _WorkOrderRepo(MaintenanceWorkOrderRepository):
    def __init__(self): self._rows: dict[str, MaintenanceWorkOrder] = {}
    def add(self, work_order): self._rows[work_order.id] = work_order
    def update(self, work_order):
        work_order.version += 1
        self._rows[work_order.id] = work_order
    def get(self, work_order_id): return self._rows.get(work_order_id)
    def get_by_code(self, organization_id, work_order_code):
        return next((r for r in self._rows.values() if r.organization_id == organization_id and r.work_order_code == work_order_code), None)
    def list_for_organization(self, organization_id, *, site_id=None, asset_id=None, component_id=None, system_id=None, location_id=None, status=None, priority=None, assigned_employee_id=None, assigned_team_id=None, planner_user_id=None, supervisor_user_id=None, work_order_type=None, is_preventive=None, is_emergency=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if site_id is not None: rows = [r for r in rows if r.site_id == site_id]
        if asset_id is not None: rows = [r for r in rows if r.asset_id == asset_id]
        if component_id is not None: rows = [r for r in rows if r.component_id == component_id]
        if system_id is not None: rows = [r for r in rows if r.system_id == system_id]
        if location_id is not None: rows = [r for r in rows if r.location_id == location_id]
        if status is not None: rows = [r for r in rows if r.status == status]
        if priority is not None: rows = [r for r in rows if r.priority == priority]
        if assigned_employee_id is not None: rows = [r for r in rows if r.assigned_employee_id == assigned_employee_id]
        if assigned_team_id is not None: rows = [r for r in rows if r.assigned_team_id == assigned_team_id]
        if planner_user_id is not None: rows = [r for r in rows if r.planner_user_id == planner_user_id]
        if supervisor_user_id is not None: rows = [r for r in rows if r.supervisor_user_id == supervisor_user_id]
        if work_order_type is not None: rows = [r for r in rows if r.work_order_type == work_order_type]
        if is_preventive is not None: rows = [r for r in rows if r.is_preventive == bool(is_preventive)]
        if is_emergency is not None: rows = [r for r in rows if r.is_emergency == bool(is_emergency)]
        return rows


class _WorkOrderTaskRepo(MaintenanceWorkOrderTaskRepository):
    def __init__(self): self._rows: dict[str, MaintenanceWorkOrderTask] = {}
    def add(self, work_order_task): self._rows[work_order_task.id] = work_order_task
    def update(self, work_order_task):
        work_order_task.version += 1
        self._rows[work_order_task.id] = work_order_task
    def get(self, work_order_task_id): return self._rows.get(work_order_task_id)
    def list_for_organization(self, organization_id, *, work_order_id=None, status=None, assigned_employee_id=None, assigned_team_id=None):
        rows = [r for r in self._rows.values() if r.organization_id == organization_id]
        if work_order_id is not None: rows = [r for r in rows if r.work_order_id == work_order_id]
        if status is not None: rows = [r for r in rows if r.status == status]
        if assigned_employee_id is not None: rows = [r for r in rows if r.assigned_employee_id == assigned_employee_id]
        if assigned_team_id is not None: rows = [r for r in rows if r.assigned_team_id == assigned_team_id]
        return rows


def _user_session() -> UserSessionContext:
    user_session = UserSessionContext()
    user_session.set_principal(UserSessionPrincipal(
        user_id="u1", username="maintenance.admin", display_name="Maintenance Admin",
        role_names=frozenset({"maintenance_admin"}),
        permissions=frozenset({"maintenance.read", "maintenance.manage"}),
    ))
    return user_session


def test_maintenance_work_order_service_creates_from_request_and_tracks_status(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(organization_id=organization.id, site_id=site.id, location_code="AREA-WO", name="Order Area")
    asset = MaintenanceAsset.create(organization_id=organization.id, site_id=site.id, location_id=location.id, asset_code="ASSET-WO", name="Work Order Asset")
    work_request = MaintenanceWorkRequest.create(
        organization_id=organization.id, site_id=site.id, work_request_code="WR-WO-001",
        source_type="MANUAL", request_type="BREAKDOWN", asset_id=asset.id, location_id=location.id,
        title="Repair pump", description="Repair leaking pump", priority="HIGH",
    )
    asset_repo = _AssetRepo()
    asset_repo.add(asset)
    location_repo = _LocationRepo()
    location_repo.add(location)
    work_request_repo = _WorkRequestRepo()
    work_request_repo.add(work_request)
    service = MaintenanceWorkOrderService(
        session, _WorkOrderRepo(), organization_repo=_OrgRepo(organization), site_repo=_SiteRepo([site]),
        user_repo=_UserRepo(), asset_repo=asset_repo, component_repo=_ComponentRepo(),
        location_repo=location_repo, system_repo=_SystemRepo(), work_request_repo=work_request_repo,
        tenant_context_service=_TenantContext(organization), user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    work_order = service.create_work_order(
        site_id=site.id, work_order_code="wo-001", work_order_type="corrective",
        source_type="work_request", source_id=work_request.id, assigned_team_id="TEAM-A",
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
    location = MaintenanceLocation.create(organization_id=organization.id, site_id=site.id, location_code="AREA-TASK", name="Task Area")
    asset = MaintenanceAsset.create(organization_id=organization.id, site_id=site.id, location_id=location.id, asset_code="ASSET-TASK", name="Task Asset")
    work_order = MaintenanceWorkOrder.create(
        organization_id=organization.id, site_id=site.id, work_order_code="WO-TASK-001",
        work_order_type="CORRECTIVE", source_type="MANUAL", asset_id=asset.id,
        location_id=location.id, title="Repair fan",
    )
    work_order_repo = _WorkOrderRepo()
    work_order_repo.add(work_order)
    service = MaintenanceWorkOrderTaskService(
        session, _WorkOrderTaskRepo(), organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo, tenant_context_service=_TenantContext(organization),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    task = service.create_task(work_order_id=work_order.id, task_name="Isolate power", assigned_team_id="TEAM-LOCKOUT", estimated_minutes=30)
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
