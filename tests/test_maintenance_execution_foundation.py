from __future__ import annotations

from types import SimpleNamespace

from core.modules.inventory_procurement.services.maintenance_integration.contracts import (
    MaintenanceMaterialAvailability,
    MaintenanceMaterialAvailabilityStatus,
)
from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceLocation,
    MaintenanceMaterialProcurementStatus,
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceWorkOrderTaskStep,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceWorkOrderMaterialRequirementRepository,
    MaintenanceWorkOrderTaskStepRepository,
)
from core.modules.maintenance_management.services import (
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
)
from core.platform.notifications.domain_events import domain_events
from tests.test_maintenance_foundation import _OrgRepo, _WorkOrderRepo, _WorkOrderTaskRepo, _user_session
from src.core.platform.org.domain import Organization, Site
from core.platform.common.exceptions import ValidationError


class _WorkOrderTaskStepRepo(MaintenanceWorkOrderTaskStepRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceWorkOrderTaskStep] = {}

    def add(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None:
        self._rows[work_order_task_step.id] = work_order_task_step

    def update(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None:
        work_order_task_step.version += 1
        self._rows[work_order_task_step.id] = work_order_task_step

    def get(self, work_order_task_step_id: str):
        return self._rows.get(work_order_task_step_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_task_id=None,
        status=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if work_order_task_id is not None:
            rows = [row for row in rows if row.work_order_task_id == work_order_task_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return rows


class _WorkOrderMaterialRequirementRepo(MaintenanceWorkOrderMaterialRequirementRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceWorkOrderMaterialRequirement] = {}

    def add(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None:
        self._rows[material_requirement.id] = material_requirement

    def update(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None:
        material_requirement.version += 1
        self._rows[material_requirement.id] = material_requirement

    def get(self, material_requirement_id: str):
        return self._rows.get(material_requirement_id)

    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id=None,
        procurement_status=None,
        preferred_storeroom_id=None,
        stock_item_id=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if work_order_id is not None:
            rows = [row for row in rows if row.work_order_id == work_order_id]
        if procurement_status is not None:
            rows = [row for row in rows if row.procurement_status.value == procurement_status]
        if preferred_storeroom_id is not None:
            rows = [row for row in rows if row.preferred_storeroom_id == preferred_storeroom_id]
        if stock_item_id is not None:
            rows = [row for row in rows if row.stock_item_id == stock_item_id]
        return rows


class _InventoryItemLookup:
    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get_item_for_internal_use(self, item_id: str):
        return self._items[item_id]


class _StoreroomLookup:
    def __init__(self, storerooms: dict[str, object]) -> None:
        self._storerooms = storerooms

    def get_storeroom_for_internal_use(self, storeroom_id: str):
        return self._storerooms[storeroom_id]


class _MaintenanceMaterialContract:
    def get_material_availability(self, **kwargs):
        return MaintenanceMaterialAvailability(
            source_reference_type=kwargs["source_reference_type"],
            source_reference_id=kwargs["source_reference_id"],
            stock_item_id=kwargs["stock_item_id"],
            storeroom_id=kwargs["storeroom_id"],
            requested_qty=float(kwargs["quantity"]),
            requested_uom=kwargs["uom"],
            requested_stock_qty=float(kwargs["quantity"]),
            on_hand_stock_qty=25.0,
            reserved_stock_qty=0.0,
            available_stock_qty=25.0,
            on_order_stock_qty=0.0,
            missing_stock_qty=0.0,
            status=MaintenanceMaterialAvailabilityStatus.AVAILABLE_FROM_STOCK,
            can_reserve=True,
            can_issue_from_stock=True,
            can_direct_procure=False,
        )


def test_maintenance_work_order_task_step_service_progresses_steps_and_unblocks_task_completion(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-STEP",
        name="Step Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-STEP",
        name="Step Asset",
    )
    work_order = MaintenanceWorkOrder.create(
        organization_id=organization.id,
        site_id=site.id,
        work_order_code="WO-STEP-001",
        work_order_type="CORRECTIVE",
        source_type="MANUAL",
        asset_id=asset.id,
        location_id=location.id,
        title="Repair compressor",
    )
    work_order_repo = _WorkOrderRepo()
    work_order_repo.add(work_order)
    task_repo = _WorkOrderTaskRepo()
    step_repo = _WorkOrderTaskStepRepo()
    task_service = MaintenanceWorkOrderTaskService(
        session,
        task_repo,
        organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo,
        work_order_task_step_repo=step_repo,
        user_session=_user_session(),
    )
    step_service = MaintenanceWorkOrderTaskStepService(
        session,
        step_repo,
        organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo,
        work_order_task_repo=task_repo,
        user_session=_user_session(),
    )

    task = task_service.create_task(
        work_order_id=work_order.id,
        task_name="Verify seal alignment",
        completion_rule=MaintenanceTaskCompletionRule.ALL_STEPS_REQUIRED,
    )
    step = step_service.create_step(
        work_order_task_id=task.id,
        instruction="Record seal temperature",
        requires_confirmation=True,
        requires_measurement=True,
        measurement_unit="C",
    )

    try:
        task_service.update_task(task.id, status="COMPLETED", expected_version=task.version)
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_WORK_ORDER_TASK_STEPS_INCOMPLETE"
    else:
        raise AssertionError("Expected task completion to be blocked until steps are done.")

    in_progress = step_service.update_step(
        step.id,
        status="IN_PROGRESS",
        expected_version=step.version,
    )
    in_progress_task = task_repo.get(task.id)
    in_progress_status = in_progress_task.status.value if in_progress_task is not None else None
    done = step_service.update_step(
        step.id,
        measurement_value="82.4",
        status="DONE",
        expected_version=in_progress.version,
    )
    confirmed = step_service.update_step(
        step.id,
        confirm_completion=True,
        expected_version=done.version,
    )
    completed_task = task_service.update_task(
        task.id,
        status="COMPLETED",
        expected_version=task.version,
    )

    assert in_progress_status == "IN_PROGRESS"
    assert confirmed.completed_by_user_id == "u1"
    assert confirmed.confirmed_by_user_id == "u1"
    assert confirmed.confirmed_at is not None
    assert completed_task.completed_at is not None


def test_maintenance_material_requirement_service_tracks_stock_demand_and_availability(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-MAT",
        name="Material Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-MAT",
        name="Material Asset",
    )
    work_order = MaintenanceWorkOrder.create(
        organization_id=organization.id,
        site_id=site.id,
        work_order_code="WO-MAT-001",
        work_order_type="CORRECTIVE",
        source_type="MANUAL",
        asset_id=asset.id,
        location_id=location.id,
        title="Replace seal",
    )
    work_order_repo = _WorkOrderRepo()
    work_order_repo.add(work_order)
    requirement_repo = _WorkOrderMaterialRequirementRepo()
    item_lookup = _InventoryItemLookup(
        {
            "item-1": SimpleNamespace(
                id="item-1",
                name="Seal Kit",
                issue_uom="EA",
                stock_uom="EA",
            )
        }
    )
    storeroom_lookup = _StoreroomLookup(
        {
            "store-1": SimpleNamespace(
                id="store-1",
                site_id=site.id,
            )
        }
    )
    service = MaintenanceWorkOrderMaterialRequirementService(
        session,
        requirement_repo,
        organization_repo=_OrgRepo(organization),
        work_order_repo=work_order_repo,
        item_service=item_lookup,
        inventory_service=storeroom_lookup,
        maintenance_material_service=_MaintenanceMaterialContract(),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    requirement = service.create_requirement(
        work_order_id=work_order.id,
        stock_item_id="item-1",
        preferred_storeroom_id="store-1",
        required_qty="2.5",
        notes="Seal kit demand",
    )
    refreshed = service.refresh_requirement_availability(
        requirement.id,
        expected_version=requirement.version,
    )

    assert requirement.required_uom == "EA"
    assert requirement.description == "Seal Kit"
    assert refreshed.procurement_status == MaintenanceMaterialProcurementStatus.AVAILABLE_FROM_STOCK
    assert refreshed.last_availability_status == "AVAILABLE_FROM_STOCK"
    assert str(refreshed.last_missing_qty) == "0.0"
    assert captured[-1].entity_type == "maintenance_material_requirement"
    assert captured[-1].source_event == "maintenance_material_requirements_changed"
