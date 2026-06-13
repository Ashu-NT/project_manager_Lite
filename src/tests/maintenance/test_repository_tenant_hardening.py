from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.modules.maintenance.domain import MaintenancePreventivePlanInstance
from src.core.modules.maintenance.infrastructure.persistence.repositories.repository import (
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceAssetComponentRepository,
    SqlAlchemyMaintenanceIntegrationSourceRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenancePreventivePlanRepository,
    SqlAlchemyMaintenancePreventivePlanTaskRepository,
    SqlAlchemyMaintenanceSensorRepository,
    SqlAlchemyMaintenanceSensorExceptionRepository,
    SqlAlchemyMaintenanceSensorReadingRepository,
    SqlAlchemyMaintenanceSensorSourceMappingRepository,
    SqlAlchemyMaintenanceSystemRepository,
    SqlAlchemyMaintenanceTaskStepTemplateRepository,
    SqlAlchemyMaintenanceTaskTemplateRepository,
    SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
    SqlAlchemyMaintenanceWorkOrderRepository,
    SqlAlchemyMaintenanceWorkOrderTaskRepository,
    SqlAlchemyMaintenanceWorkOrderTaskStepRepository,
    SqlAlchemyMaintenanceWorkRequestRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories.preventive_instance_repository import (
    SqlAlchemyMaintenancePreventivePlanInstanceRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories.reliability_repository import (
    SqlAlchemyMaintenanceDowntimeEventRepository,
    SqlAlchemyMaintenanceFailureCodeRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


def _maintenance_repo(repo_factory, services):
    return repo_factory(
        services["session"],
        tenant_context_service=services["tenant_context_service"],
    )


def _seed_maintenance_root_scope_rows(services):
    organization_service = services["organization_service"]
    current_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="MNT-TENANT-OPS",
        display_name="Maintenance Tenant Operations",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )

    assert current_org is not None
    assert other_org is not None

    site_service = services["site_service"]
    location_service = services["maintenance_location_service"]
    system_service = services["maintenance_system_service"]
    asset_service = services["maintenance_asset_service"]
    sensor_service = services["maintenance_sensor_service"]
    integration_source_service = services["maintenance_integration_source_service"]
    failure_code_service = services["maintenance_failure_code_service"]
    task_template_service = services["maintenance_task_template_service"]
    work_request_service = services["maintenance_work_request_service"]
    work_order_service = services["maintenance_work_order_service"]
    preventive_plan_service = services["maintenance_preventive_plan_service"]

    def build_rows(prefix: str) -> dict[str, object]:
        site = site_service.create_site(
            site_code=f"{prefix}-MNT-SITE",
            name=f"{prefix} Maintenance Site",
            city="Berlin",
            currency_code="EUR",
        )
        location = location_service.create_location(
            site_id=site.id,
            location_code="SCOPE-LOC",
            name=f"{prefix} Scoped Location",
            location_type="AREA",
        )
        system = system_service.create_system(
            site_id=site.id,
            system_code="SCOPE-SYS",
            name=f"{prefix} Scoped System",
            location_id=location.id,
            system_type="LINE",
        )
        asset = asset_service.create_asset(
            site_id=site.id,
            location_id=location.id,
            asset_code="SCOPE-AST",
            name=f"{prefix} Scoped Asset",
            system_id=system.id,
            asset_type="PUMP",
        )
        sensor = sensor_service.create_sensor(
            site_id=site.id,
            sensor_code="SCOPE-SNS",
            sensor_name=f"{prefix} Scoped Sensor",
            asset_id=asset.id,
            system_id=system.id,
            sensor_type="RUN_HOURS",
            unit="H",
        )
        integration_source = integration_source_service.create_source(
            integration_code="SCOPE-SRC",
            name=f"{prefix} Scoped Source",
            integration_type="ERP_BRIDGE",
            endpoint_or_path=f"https://{prefix.lower()}.example.test/maintenance",
        )
        failure_code = failure_code_service.create_failure_code(
            failure_code="SCOPE-FAIL",
            name=f"{prefix} Scoped Failure",
            code_type="symptom",
        )
        task_template = task_template_service.create_task_template(
            task_template_code="SCOPE-TASK",
            name=f"{prefix} Scoped Task Template",
            maintenance_type="preventive",
            template_status="active",
            estimated_minutes=30,
        )
        work_request = work_request_service.create_work_request(
            site_id=site.id,
            work_request_code="SCOPE-WR",
            source_type="manual",
            request_type="inspection",
            asset_id=asset.id,
            location_id=location.id,
            title=f"{prefix} Scoped Work Request",
        )
        work_order = work_order_service.create_work_order(
            site_id=site.id,
            work_order_code="SCOPE-WO",
            work_order_type="inspection",
            source_type="work_request",
            source_id=work_request.id,
        )
        preventive_plan = preventive_plan_service.create_preventive_plan(
            site_id=site.id,
            plan_code="SCOPE-PLAN",
            name=f"{prefix} Scoped Plan",
            asset_id=asset.id,
            plan_type="preventive",
            trigger_mode="calendar",
            calendar_frequency_unit="monthly",
            calendar_frequency_value=1,
        )
        return {
            "site": site,
            "location": location,
            "system": system,
            "asset": asset,
            "sensor": sensor,
            "integration_source": integration_source,
            "failure_code": failure_code,
            "task_template": task_template,
            "work_request": work_request,
            "work_order": work_order,
            "preventive_plan": preventive_plan,
        }

    current_rows = build_rows("CUR")
    organization_service.set_active_organization(other_org.id)
    other_rows = build_rows("OTH")
    organization_service.set_active_organization(current_org.id)

    return {
        "current_org_id": current_org.id,
        "other_org_id": other_org.id,
        "current_location_id": current_rows["location"].id,
        "other_location_id": other_rows["location"].id,
        "current_location_code": current_rows["location"].location_code,
        "current_site": current_rows["site"],
        "current_location": current_rows["location"],
        "current_system_id": current_rows["system"].id,
        "other_system_id": other_rows["system"].id,
        "current_system_code": current_rows["system"].system_code,
        "current_system": current_rows["system"],
        "current_asset_id": current_rows["asset"].id,
        "other_asset_id": other_rows["asset"].id,
        "current_asset_code": current_rows["asset"].asset_code,
        "current_asset": current_rows["asset"],
        "current_sensor_id": current_rows["sensor"].id,
        "other_sensor_id": other_rows["sensor"].id,
        "current_sensor_code": current_rows["sensor"].sensor_code,
        "current_sensor": current_rows["sensor"],
        "current_integration_source_id": current_rows["integration_source"].id,
        "other_integration_source_id": other_rows["integration_source"].id,
        "current_integration_code": current_rows["integration_source"].integration_code,
        "current_integration_source": current_rows["integration_source"],
        "current_failure_code_id": current_rows["failure_code"].id,
        "other_failure_code_id": other_rows["failure_code"].id,
        "current_failure_code": current_rows["failure_code"].failure_code,
        "current_task_template_id": current_rows["task_template"].id,
        "other_task_template_id": other_rows["task_template"].id,
        "current_task_template_code": current_rows["task_template"].task_template_code,
        "current_task_template": current_rows["task_template"],
        "current_work_request_id": current_rows["work_request"].id,
        "other_work_request_id": other_rows["work_request"].id,
        "current_work_request_code": current_rows["work_request"].work_request_code,
        "current_work_request": current_rows["work_request"],
        "current_work_order_id": current_rows["work_order"].id,
        "other_work_order_id": other_rows["work_order"].id,
        "current_work_order_code": current_rows["work_order"].work_order_code,
        "current_work_order": current_rows["work_order"],
        "current_preventive_plan_id": current_rows["preventive_plan"].id,
        "other_preventive_plan_id": other_rows["preventive_plan"].id,
        "current_preventive_plan_code": current_rows["preventive_plan"].plan_code,
        "current_preventive_plan": current_rows["preventive_plan"],
        "other_location": other_rows["location"],
        "other_system": other_rows["system"],
        "other_asset": other_rows["asset"],
        "other_sensor": other_rows["sensor"],
        "other_integration_source": other_rows["integration_source"],
        "other_failure_code": other_rows["failure_code"],
        "other_task_template": other_rows["task_template"],
        "other_work_request": other_rows["work_request"],
        "other_work_order": other_rows["work_order"],
        "other_preventive_plan": other_rows["preventive_plan"],
    }


def _seed_maintenance_secondary_scope_rows(services):
    seeded = _seed_maintenance_root_scope_rows(services)
    organization_service = services["organization_service"]
    component_service = services["maintenance_asset_component_service"]
    sensor_reading_service = services["maintenance_sensor_reading_service"]
    sensor_source_mapping_service = services["maintenance_sensor_source_mapping_service"]
    sensor_exception_service = services["maintenance_sensor_exception_service"]
    work_order_task_service = services["maintenance_work_order_task_service"]
    work_order_task_step_service = services["maintenance_work_order_task_step_service"]
    material_requirement_service = services["maintenance_work_order_material_requirement_service"]
    task_step_template_service = services["maintenance_task_step_template_service"]
    plan_task_service = services["maintenance_preventive_plan_task_service"]
    downtime_event_service = services["maintenance_downtime_event_service"]
    preventive_instance_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanInstanceRepository,
        services,
    )
    session = services["session"]

    def build_rows(prefix: str, root_rows: dict[str, object]) -> dict[str, object]:
        component = component_service.create_component(
            asset_id=root_rows["asset"].id,
            component_code="SCOPE-COMP",
            name=f"{prefix} Scoped Component",
        )
        step_template = task_step_template_service.create_step_template(
            task_template_id=root_rows["task_template"].id,
            step_number=1,
            instruction=f"{prefix} Scoped Step Template",
        )
        mapping = sensor_source_mapping_service.create_mapping(
            integration_source_id=root_rows["integration_source"].id,
            sensor_id=root_rows["sensor"].id,
            external_measurement_key=f"{prefix}-MEASURE",
        )
        reading = sensor_reading_service.record_reading(
            sensor_id=root_rows["sensor"].id,
            reading_value="125",
            reading_unit="H",
            reading_timestamp=datetime.now(timezone.utc),
            source_batch_id=f"{prefix}-BATCH",
        )
        sensor_exception = sensor_exception_service.raise_exception(
            sensor_id=root_rows["sensor"].id,
            integration_source_id=root_rows["integration_source"].id,
            source_mapping_id=mapping.id,
            exception_type="STALE_READING",
            message=f"{prefix} Scoped Sensor Exception",
            detected_at=datetime.now(timezone.utc),
        )
        work_order_task = work_order_task_service.create_task(
            work_order_id=root_rows["work_order"].id,
            task_template_id=root_rows["task_template"].id,
            task_name=f"{prefix} Scoped Work Order Task",
            sequence_no=1,
        )
        work_order_task_step = work_order_task_step_service.create_step(
            work_order_task_id=work_order_task.id,
            source_step_template_id=step_template.id,
            step_number=1,
            instruction=f"{prefix} Scoped Work Order Step",
        )
        material_requirement = material_requirement_service.create_requirement(
            work_order_id=root_rows["work_order"].id,
            description=f"{prefix} Scoped Material",
            required_qty="1",
            required_uom="EA",
            is_stock_item=False,
        )
        plan_task = plan_task_service.create_plan_task(
            plan_id=root_rows["preventive_plan"].id,
            task_template_id=root_rows["task_template"].id,
            sequence_no=1,
            trigger_scope="inherit_plan",
        )
        downtime_event = downtime_event_service.create_downtime_event(
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            downtime_type="UNPLANNED",
            work_order_id=root_rows["work_order"].id,
            asset_id=root_rows["asset"].id,
            system_id=root_rows["system"].id,
        )
        preventive_instance = MaintenancePreventivePlanInstance.create(
            organization_id=root_rows["preventive_plan"].organization_id,
            plan_id=root_rows["preventive_plan"].id,
            due_at=datetime.now(timezone.utc) - timedelta(days=1),
            generated_work_order_id=root_rows["work_order"].id,
        )
        preventive_instance_repo.add(preventive_instance)
        session.commit()
        return {
            "component": component,
            "sensor_reading": reading,
            "sensor_source_mapping": mapping,
            "sensor_exception": sensor_exception,
            "work_order_task": work_order_task,
            "work_order_task_step": work_order_task_step,
            "material_requirement": material_requirement,
            "task_step_template": step_template,
            "preventive_plan_task": plan_task,
            "downtime_event": downtime_event,
            "preventive_plan_instance": preventive_instance,
        }

    current_rows = build_rows(
        "CUR",
        {
            "asset": seeded["current_asset"],
            "sensor": seeded["current_sensor"],
            "integration_source": seeded["current_integration_source"],
            "task_template": seeded["current_task_template"],
            "work_order": seeded["current_work_order"],
            "system": seeded["current_system"],
            "preventive_plan": seeded["current_preventive_plan"],
        },
    )
    organization_service.set_active_organization(seeded["other_org_id"])
    other_rows = build_rows(
        "OTH",
        {
            "asset": seeded["other_asset"],
            "sensor": seeded["other_sensor"],
            "integration_source": seeded["other_integration_source"],
            "task_template": seeded["other_task_template"],
            "work_order": seeded["other_work_order"],
            "system": seeded["other_system"],
            "preventive_plan": seeded["other_preventive_plan"],
        },
    )
    organization_service.set_active_organization(seeded["current_org_id"])

    seeded.update(
        {
            "current_component_id": current_rows["component"].id,
            "other_component_id": other_rows["component"].id,
            "current_component_code": current_rows["component"].component_code,
            "current_component": current_rows["component"],
            "other_component": other_rows["component"],
            "current_sensor_reading_id": current_rows["sensor_reading"].id,
            "other_sensor_reading_id": other_rows["sensor_reading"].id,
            "current_sensor_source_mapping_id": current_rows["sensor_source_mapping"].id,
            "other_sensor_source_mapping_id": other_rows["sensor_source_mapping"].id,
            "current_sensor_source_mapping": current_rows["sensor_source_mapping"],
            "other_sensor_source_mapping": other_rows["sensor_source_mapping"],
            "current_sensor_exception_id": current_rows["sensor_exception"].id,
            "other_sensor_exception_id": other_rows["sensor_exception"].id,
            "current_sensor_exception": current_rows["sensor_exception"],
            "other_sensor_exception": other_rows["sensor_exception"],
            "current_work_order_task_id": current_rows["work_order_task"].id,
            "other_work_order_task_id": other_rows["work_order_task"].id,
            "current_work_order_task": current_rows["work_order_task"],
            "other_work_order_task": other_rows["work_order_task"],
            "current_work_order_task_step_id": current_rows["work_order_task_step"].id,
            "other_work_order_task_step_id": other_rows["work_order_task_step"].id,
            "current_work_order_task_step": current_rows["work_order_task_step"],
            "other_work_order_task_step": other_rows["work_order_task_step"],
            "current_material_requirement_id": current_rows["material_requirement"].id,
            "other_material_requirement_id": other_rows["material_requirement"].id,
            "current_material_requirement": current_rows["material_requirement"],
            "other_material_requirement": other_rows["material_requirement"],
            "current_task_step_template_id": current_rows["task_step_template"].id,
            "other_task_step_template_id": other_rows["task_step_template"].id,
            "current_task_step_template": current_rows["task_step_template"],
            "other_task_step_template": other_rows["task_step_template"],
            "current_preventive_plan_task_id": current_rows["preventive_plan_task"].id,
            "other_preventive_plan_task_id": other_rows["preventive_plan_task"].id,
            "current_preventive_plan_task": current_rows["preventive_plan_task"],
            "other_preventive_plan_task": other_rows["preventive_plan_task"],
            "current_downtime_event_id": current_rows["downtime_event"].id,
            "other_downtime_event_id": other_rows["downtime_event"].id,
            "current_downtime_event": current_rows["downtime_event"],
            "other_downtime_event": other_rows["downtime_event"],
            "current_preventive_plan_instance_id": current_rows["preventive_plan_instance"].id,
            "other_preventive_plan_instance_id": other_rows["preventive_plan_instance"].id,
            "current_preventive_plan_instance": current_rows["preventive_plan_instance"],
            "other_preventive_plan_instance": other_rows["preventive_plan_instance"],
        }
    )
    return seeded


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (SqlAlchemyMaintenanceLocationRepository, lambda repo: repo.get("location-1")),
        (SqlAlchemyMaintenanceSystemRepository, lambda repo: repo.get("system-1")),
        (SqlAlchemyMaintenanceAssetRepository, lambda repo: repo.get("asset-1")),
        (SqlAlchemyMaintenanceSensorRepository, lambda repo: repo.get("sensor-1")),
        (
            SqlAlchemyMaintenanceIntegrationSourceRepository,
            lambda repo: repo.get("integration-source-1"),
        ),
        (SqlAlchemyMaintenanceFailureCodeRepository, lambda repo: repo.get("failure-code-1")),
        (SqlAlchemyMaintenanceTaskTemplateRepository, lambda repo: repo.get("task-template-1")),
        (SqlAlchemyMaintenanceWorkRequestRepository, lambda repo: repo.get("work-request-1")),
        (SqlAlchemyMaintenanceWorkOrderRepository, lambda repo: repo.get("work-order-1")),
        (
            SqlAlchemyMaintenancePreventivePlanRepository,
            lambda repo: repo.get("preventive-plan-1"),
        ),
    ],
)
def test_maintenance_root_repositories_require_tenant_context_service(
    session,
    repo_factory,
    operation,
) -> None:
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        repo_factory(session)


def test_maintenance_root_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_maintenance_root_scope_rows(services)

    location_repo = _maintenance_repo(SqlAlchemyMaintenanceLocationRepository, services)
    system_repo = _maintenance_repo(SqlAlchemyMaintenanceSystemRepository, services)
    asset_repo = _maintenance_repo(SqlAlchemyMaintenanceAssetRepository, services)
    sensor_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorRepository, services)
    integration_source_repo = _maintenance_repo(
        SqlAlchemyMaintenanceIntegrationSourceRepository,
        services,
    )
    failure_code_repo = _maintenance_repo(SqlAlchemyMaintenanceFailureCodeRepository, services)
    task_template_repo = _maintenance_repo(SqlAlchemyMaintenanceTaskTemplateRepository, services)
    work_request_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkRequestRepository, services)
    work_order_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderRepository, services)
    preventive_plan_repo = _maintenance_repo(SqlAlchemyMaintenancePreventivePlanRepository, services)

    assert location_repo.get(seeded["other_location_id"]) is None
    assert system_repo.get(seeded["other_system_id"]) is None
    assert asset_repo.get(seeded["other_asset_id"]) is None
    assert sensor_repo.get(seeded["other_sensor_id"]) is None
    assert integration_source_repo.get(seeded["other_integration_source_id"]) is None
    assert failure_code_repo.get(seeded["other_failure_code_id"]) is None
    assert task_template_repo.get(seeded["other_task_template_id"]) is None
    assert work_request_repo.get(seeded["other_work_request_id"]) is None
    assert work_order_repo.get(seeded["other_work_order_id"]) is None
    assert preventive_plan_repo.get(seeded["other_preventive_plan_id"]) is None

    assert location_repo.get_by_code(seeded["other_org_id"], seeded["current_location_code"]) is None
    assert system_repo.get_by_code(seeded["other_org_id"], seeded["current_system_code"]) is None
    assert asset_repo.get_by_code(seeded["other_org_id"], seeded["current_asset_code"]) is None
    assert sensor_repo.get_by_code(seeded["other_org_id"], seeded["current_sensor_code"]) is None
    assert (
        integration_source_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_integration_code"],
        )
        is None
    )
    assert (
        failure_code_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_failure_code"],
        )
        is None
    )
    assert (
        task_template_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_task_template_code"],
        )
        is None
    )
    assert (
        work_request_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_work_request_code"],
        )
        is None
    )
    assert (
        work_order_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_work_order_code"],
        )
        is None
    )
    assert (
        preventive_plan_repo.get_by_code(
            seeded["other_org_id"],
            seeded["current_preventive_plan_code"],
        )
        is None
    )

    current_location_ids = {
        row.id
        for row in location_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_system_ids = {
        row.id
        for row in system_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_asset_ids = {
        row.id
        for row in asset_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_sensor_ids = {
        row.id
        for row in sensor_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_integration_source_ids = {
        row.id
        for row in integration_source_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_failure_code_ids = {
        row.id
        for row in failure_code_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_task_template_ids = {
        row.id
        for row in task_template_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_work_request_ids = {
        row.id for row in work_request_repo.list_for_organization(seeded["current_org_id"])
    }
    current_work_order_ids = {
        row.id for row in work_order_repo.list_for_organization(seeded["current_org_id"])
    }
    current_preventive_plan_ids = {
        row.id
        for row in preventive_plan_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }

    assert location_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert system_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert asset_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert sensor_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert (
        integration_source_repo.list_for_organization(
            seeded["other_org_id"],
            active_only=None,
        )
        == []
    )
    assert failure_code_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert task_template_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert work_request_repo.list_for_organization(seeded["other_org_id"]) == []
    assert work_order_repo.list_for_organization(seeded["other_org_id"]) == []
    assert preventive_plan_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []

    assert seeded["current_location_id"] in current_location_ids
    assert seeded["other_location_id"] not in current_location_ids
    assert seeded["current_system_id"] in current_system_ids
    assert seeded["other_system_id"] not in current_system_ids
    assert seeded["current_asset_id"] in current_asset_ids
    assert seeded["other_asset_id"] not in current_asset_ids
    assert seeded["current_sensor_id"] in current_sensor_ids
    assert seeded["other_sensor_id"] not in current_sensor_ids
    assert seeded["current_integration_source_id"] in current_integration_source_ids
    assert seeded["other_integration_source_id"] not in current_integration_source_ids
    assert seeded["current_failure_code_id"] in current_failure_code_ids
    assert seeded["other_failure_code_id"] not in current_failure_code_ids
    assert seeded["current_task_template_id"] in current_task_template_ids
    assert seeded["other_task_template_id"] not in current_task_template_ids
    assert seeded["current_work_request_id"] in current_work_request_ids
    assert seeded["other_work_request_id"] not in current_work_request_ids
    assert seeded["current_work_order_id"] in current_work_order_ids
    assert seeded["other_work_order_id"] not in current_work_order_ids
    assert seeded["current_preventive_plan_id"] in current_preventive_plan_ids
    assert seeded["other_preventive_plan_id"] not in current_preventive_plan_ids


def test_maintenance_root_repositories_reject_cross_organization_updates(services) -> None:
    seeded = _seed_maintenance_root_scope_rows(services)

    location_repo = _maintenance_repo(SqlAlchemyMaintenanceLocationRepository, services)
    system_repo = _maintenance_repo(SqlAlchemyMaintenanceSystemRepository, services)
    asset_repo = _maintenance_repo(SqlAlchemyMaintenanceAssetRepository, services)
    sensor_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorRepository, services)
    integration_source_repo = _maintenance_repo(
        SqlAlchemyMaintenanceIntegrationSourceRepository,
        services,
    )
    failure_code_repo = _maintenance_repo(SqlAlchemyMaintenanceFailureCodeRepository, services)
    task_template_repo = _maintenance_repo(SqlAlchemyMaintenanceTaskTemplateRepository, services)
    work_request_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkRequestRepository, services)
    work_order_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderRepository, services)
    preventive_plan_repo = _maintenance_repo(SqlAlchemyMaintenancePreventivePlanRepository, services)

    with pytest.raises(NotFoundError, match="Maintenance location not found"):
        location_repo.update(seeded["other_location"])
    with pytest.raises(NotFoundError, match="Maintenance system not found"):
        system_repo.update(seeded["other_system"])
    with pytest.raises(NotFoundError, match="Maintenance asset not found"):
        asset_repo.update(seeded["other_asset"])
    with pytest.raises(NotFoundError, match="Maintenance sensor not found"):
        sensor_repo.update(seeded["other_sensor"])
    with pytest.raises(NotFoundError, match="Maintenance integration source not found"):
        integration_source_repo.update(seeded["other_integration_source"])
    with pytest.raises(NotFoundError, match="Maintenance failure code not found"):
        failure_code_repo.update(seeded["other_failure_code"])
    with pytest.raises(NotFoundError, match="Maintenance task template not found"):
        task_template_repo.update(seeded["other_task_template"])
    with pytest.raises(NotFoundError, match="Maintenance work request not found"):
        work_request_repo.update(seeded["other_work_request"])
    with pytest.raises(NotFoundError, match="Maintenance work order not found"):
        work_order_repo.update(seeded["other_work_order"])
    with pytest.raises(NotFoundError, match="Maintenance preventive plan not found"):
        preventive_plan_repo.update(seeded["other_preventive_plan"])


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (SqlAlchemyMaintenanceAssetComponentRepository, lambda repo: repo.get("component-1")),
        (SqlAlchemyMaintenanceSensorReadingRepository, lambda repo: repo.get("sensor-reading-1")),
        (SqlAlchemyMaintenanceSensorSourceMappingRepository, lambda repo: repo.get("sensor-source-mapping-1")),
        (SqlAlchemyMaintenanceSensorExceptionRepository, lambda repo: repo.get("sensor-exception-1")),
        (SqlAlchemyMaintenanceWorkOrderTaskRepository, lambda repo: repo.get("work-order-task-1")),
        (SqlAlchemyMaintenanceWorkOrderTaskStepRepository, lambda repo: repo.get("work-order-task-step-1")),
        (
            SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
            lambda repo: repo.get("material-requirement-1"),
        ),
        (SqlAlchemyMaintenanceTaskStepTemplateRepository, lambda repo: repo.get("task-step-template-1")),
        (SqlAlchemyMaintenancePreventivePlanTaskRepository, lambda repo: repo.get("preventive-plan-task-1")),
        (SqlAlchemyMaintenanceDowntimeEventRepository, lambda repo: repo.get("downtime-event-1")),
        (
            SqlAlchemyMaintenancePreventivePlanInstanceRepository,
            lambda repo: repo.get("preventive-instance-1"),
        ),
    ],
)
def test_maintenance_secondary_repositories_require_tenant_context_service(
    session,
    repo_factory,
    operation,
) -> None:
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        repo_factory(session)


def test_maintenance_secondary_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_maintenance_secondary_scope_rows(services)

    component_repo = _maintenance_repo(SqlAlchemyMaintenanceAssetComponentRepository, services)
    sensor_reading_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorReadingRepository, services)
    sensor_source_mapping_repo = _maintenance_repo(
        SqlAlchemyMaintenanceSensorSourceMappingRepository,
        services,
    )
    sensor_exception_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorExceptionRepository, services)
    work_order_task_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskRepository, services)
    work_order_task_step_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskStepRepository, services)
    material_requirement_repo = _maintenance_repo(
        SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
        services,
    )
    task_step_template_repo = _maintenance_repo(
        SqlAlchemyMaintenanceTaskStepTemplateRepository,
        services,
    )
    preventive_plan_task_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanTaskRepository,
        services,
    )
    downtime_event_repo = _maintenance_repo(SqlAlchemyMaintenanceDowntimeEventRepository, services)
    preventive_plan_instance_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanInstanceRepository,
        services,
    )

    assert component_repo.get(seeded["other_component_id"]) is None
    assert sensor_reading_repo.get(seeded["other_sensor_reading_id"]) is None
    assert sensor_source_mapping_repo.get(seeded["other_sensor_source_mapping_id"]) is None
    assert sensor_exception_repo.get(seeded["other_sensor_exception_id"]) is None
    assert work_order_task_repo.get(seeded["other_work_order_task_id"]) is None
    assert work_order_task_step_repo.get(seeded["other_work_order_task_step_id"]) is None
    assert material_requirement_repo.get(seeded["other_material_requirement_id"]) is None
    assert task_step_template_repo.get(seeded["other_task_step_template_id"]) is None
    assert preventive_plan_task_repo.get(seeded["other_preventive_plan_task_id"]) is None
    assert downtime_event_repo.get(seeded["other_downtime_event_id"]) is None
    assert preventive_plan_instance_repo.get(seeded["other_preventive_plan_instance_id"]) is None

    assert component_repo.get_by_code(seeded["other_org_id"], seeded["current_component_code"]) is None
    assert (
        preventive_plan_instance_repo.get_by_generated_work_order_id(
            seeded["current_org_id"],
            seeded["other_work_order_id"],
        )
        is None
    )

    current_component_ids = {
        row.id
        for row in component_repo.list_for_organization(seeded["current_org_id"], active_only=None)
    }
    current_sensor_reading_ids = {
        row.id for row in sensor_reading_repo.list_for_organization(seeded["current_org_id"])
    }
    current_sensor_source_mapping_ids = {
        row.id
        for row in sensor_source_mapping_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_sensor_exception_ids = {
        row.id for row in sensor_exception_repo.list_for_organization(seeded["current_org_id"])
    }
    current_work_order_task_ids = {
        row.id for row in work_order_task_repo.list_for_organization(seeded["current_org_id"])
    }
    current_work_order_task_step_ids = {
        row.id for row in work_order_task_step_repo.list_for_organization(seeded["current_org_id"])
    }
    current_material_requirement_ids = {
        row.id for row in material_requirement_repo.list_for_organization(seeded["current_org_id"])
    }
    current_task_step_template_ids = {
        row.id
        for row in task_step_template_repo.list_for_organization(
            seeded["current_org_id"],
            active_only=None,
        )
    }
    current_preventive_plan_task_ids = {
        row.id for row in preventive_plan_task_repo.list_for_organization(seeded["current_org_id"])
    }
    current_downtime_event_ids = {
        row.id for row in downtime_event_repo.list_for_organization(seeded["current_org_id"])
    }
    current_preventive_plan_instance_ids = {
        row.id for row in preventive_plan_instance_repo.list_for_organization(seeded["current_org_id"])
    }

    assert component_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert sensor_reading_repo.list_for_organization(seeded["other_org_id"]) == []
    assert sensor_source_mapping_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert sensor_exception_repo.list_for_organization(seeded["other_org_id"]) == []
    assert work_order_task_repo.list_for_organization(seeded["other_org_id"]) == []
    assert work_order_task_step_repo.list_for_organization(seeded["other_org_id"]) == []
    assert material_requirement_repo.list_for_organization(seeded["other_org_id"]) == []
    assert task_step_template_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert preventive_plan_task_repo.list_for_organization(seeded["other_org_id"]) == []
    assert downtime_event_repo.list_for_organization(seeded["other_org_id"]) == []
    assert preventive_plan_instance_repo.list_for_organization(seeded["other_org_id"]) == []

    assert seeded["current_component_id"] in current_component_ids
    assert seeded["other_component_id"] not in current_component_ids
    assert seeded["current_sensor_reading_id"] in current_sensor_reading_ids
    assert seeded["other_sensor_reading_id"] not in current_sensor_reading_ids
    assert seeded["current_sensor_source_mapping_id"] in current_sensor_source_mapping_ids
    assert seeded["other_sensor_source_mapping_id"] not in current_sensor_source_mapping_ids
    assert seeded["current_sensor_exception_id"] in current_sensor_exception_ids
    assert seeded["other_sensor_exception_id"] not in current_sensor_exception_ids
    assert seeded["current_work_order_task_id"] in current_work_order_task_ids
    assert seeded["other_work_order_task_id"] not in current_work_order_task_ids
    assert seeded["current_work_order_task_step_id"] in current_work_order_task_step_ids
    assert seeded["other_work_order_task_step_id"] not in current_work_order_task_step_ids
    assert seeded["current_material_requirement_id"] in current_material_requirement_ids
    assert seeded["other_material_requirement_id"] not in current_material_requirement_ids
    assert seeded["current_task_step_template_id"] in current_task_step_template_ids
    assert seeded["other_task_step_template_id"] not in current_task_step_template_ids
    assert seeded["current_preventive_plan_task_id"] in current_preventive_plan_task_ids
    assert seeded["other_preventive_plan_task_id"] not in current_preventive_plan_task_ids
    assert seeded["current_downtime_event_id"] in current_downtime_event_ids
    assert seeded["other_downtime_event_id"] not in current_downtime_event_ids
    assert seeded["current_preventive_plan_instance_id"] in current_preventive_plan_instance_ids
    assert seeded["other_preventive_plan_instance_id"] not in current_preventive_plan_instance_ids


def test_maintenance_secondary_repositories_reject_cross_organization_updates(services) -> None:
    seeded = _seed_maintenance_secondary_scope_rows(services)

    component_repo = _maintenance_repo(SqlAlchemyMaintenanceAssetComponentRepository, services)
    sensor_source_mapping_repo = _maintenance_repo(
        SqlAlchemyMaintenanceSensorSourceMappingRepository,
        services,
    )
    sensor_exception_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorExceptionRepository, services)
    work_order_task_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskRepository, services)
    work_order_task_step_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskStepRepository, services)
    material_requirement_repo = _maintenance_repo(
        SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
        services,
    )
    task_step_template_repo = _maintenance_repo(
        SqlAlchemyMaintenanceTaskStepTemplateRepository,
        services,
    )
    preventive_plan_task_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanTaskRepository,
        services,
    )
    downtime_event_repo = _maintenance_repo(SqlAlchemyMaintenanceDowntimeEventRepository, services)
    preventive_plan_instance_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanInstanceRepository,
        services,
    )

    with pytest.raises(NotFoundError, match="Maintenance asset component not found"):
        component_repo.update(seeded["other_component"])
    with pytest.raises(NotFoundError, match="Maintenance sensor source mapping not found"):
        sensor_source_mapping_repo.update(seeded["other_sensor_source_mapping"])
    with pytest.raises(NotFoundError, match="Maintenance sensor exception not found"):
        sensor_exception_repo.update(seeded["other_sensor_exception"])
    with pytest.raises(NotFoundError, match="Maintenance work order task not found"):
        work_order_task_repo.update(seeded["other_work_order_task"])
    with pytest.raises(NotFoundError, match="Maintenance work order task step not found"):
        work_order_task_step_repo.update(seeded["other_work_order_task_step"])
    with pytest.raises(NotFoundError, match="Maintenance material requirement not found"):
        material_requirement_repo.update(seeded["other_material_requirement"])
    with pytest.raises(NotFoundError, match="Maintenance task step template not found"):
        task_step_template_repo.update(seeded["other_task_step_template"])
    with pytest.raises(NotFoundError, match="Maintenance preventive plan task not found"):
        preventive_plan_task_repo.update(seeded["other_preventive_plan_task"])
    with pytest.raises(NotFoundError, match="Maintenance downtime event not found"):
        downtime_event_repo.update(seeded["other_downtime_event"])
    with pytest.raises(NotFoundError, match="Maintenance preventive plan instance not found"):
        preventive_plan_instance_repo.update(seeded["other_preventive_plan_instance"])


def test_maintenance_secondary_repositories_reject_cross_scope_parent_references(services) -> None:
    seeded = _seed_maintenance_secondary_scope_rows(services)

    component_repo = _maintenance_repo(SqlAlchemyMaintenanceAssetComponentRepository, services)
    sensor_source_mapping_repo = _maintenance_repo(
        SqlAlchemyMaintenanceSensorSourceMappingRepository,
        services,
    )
    sensor_exception_repo = _maintenance_repo(SqlAlchemyMaintenanceSensorExceptionRepository, services)
    work_order_task_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskRepository, services)
    work_order_task_step_repo = _maintenance_repo(SqlAlchemyMaintenanceWorkOrderTaskStepRepository, services)
    material_requirement_repo = _maintenance_repo(
        SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
        services,
    )
    task_step_template_repo = _maintenance_repo(
        SqlAlchemyMaintenanceTaskStepTemplateRepository,
        services,
    )
    preventive_plan_task_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanTaskRepository,
        services,
    )
    downtime_event_repo = _maintenance_repo(SqlAlchemyMaintenanceDowntimeEventRepository, services)
    preventive_plan_instance_repo = _maintenance_repo(
        SqlAlchemyMaintenancePreventivePlanInstanceRepository,
        services,
    )

    seeded["current_component"].asset_id = seeded["other_asset_id"]
    with pytest.raises(NotFoundError, match="Maintenance asset not found"):
        component_repo.update(seeded["current_component"])

    seeded["current_sensor_source_mapping"].sensor_id = seeded["other_sensor_id"]
    with pytest.raises(NotFoundError, match="Maintenance sensor not found"):
        sensor_source_mapping_repo.update(seeded["current_sensor_source_mapping"])

    seeded["current_sensor_exception"].sensor_id = seeded["other_sensor_id"]
    with pytest.raises(NotFoundError, match="Maintenance sensor not found"):
        sensor_exception_repo.update(seeded["current_sensor_exception"])

    seeded["current_work_order_task"].work_order_id = seeded["other_work_order_id"]
    with pytest.raises(NotFoundError, match="Maintenance work order not found"):
        work_order_task_repo.update(seeded["current_work_order_task"])

    seeded["current_work_order_task_step"].work_order_task_id = seeded["other_work_order_task_id"]
    with pytest.raises(NotFoundError, match="Maintenance work order task not found"):
        work_order_task_step_repo.update(seeded["current_work_order_task_step"])

    seeded["current_material_requirement"].work_order_id = seeded["other_work_order_id"]
    with pytest.raises(NotFoundError, match="Maintenance work order not found"):
        material_requirement_repo.update(seeded["current_material_requirement"])

    seeded["current_task_step_template"].task_template_id = seeded["other_task_template_id"]
    with pytest.raises(NotFoundError, match="Maintenance task template not found"):
        task_step_template_repo.update(seeded["current_task_step_template"])

    seeded["current_preventive_plan_task"].plan_id = seeded["other_preventive_plan_id"]
    with pytest.raises(NotFoundError, match="Maintenance preventive plan not found"):
        preventive_plan_task_repo.update(seeded["current_preventive_plan_task"])

    seeded["current_downtime_event"].work_order_id = seeded["other_work_order_id"]
    with pytest.raises(NotFoundError, match="Maintenance work order not found"):
        downtime_event_repo.update(seeded["current_downtime_event"])

    seeded["current_preventive_plan_instance"].plan_id = seeded["other_preventive_plan_id"]
    with pytest.raises(NotFoundError, match="Maintenance preventive plan not found"):
        preventive_plan_instance_repo.update(seeded["current_preventive_plan_instance"])
