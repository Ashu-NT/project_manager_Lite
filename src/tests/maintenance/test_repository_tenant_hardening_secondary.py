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

from src.tests.maintenance._maintenance_tenant_hardening_helpers import (
    _maintenance_repo,
    _seed_maintenance_root_scope_rows,
)


def _seed_maintenance_secondary_scope_rows(services):
    root = _seed_maintenance_root_scope_rows(services)

    organization_service = services["organization_service"]
    component_service = services["maintenance_asset_component_service"]
    sensor_reading_service = services["maintenance_sensor_reading_service"]
    sensor_source_mapping_service = services["maintenance_sensor_source_mapping_service"]
    sensor_exception_service = services["maintenance_sensor_exception_service"]
    work_order_task_service = services["maintenance_work_order_task_service"]
    work_order_task_step_service = services["maintenance_work_order_task_step_service"]
    material_requirement_service = services["maintenance_work_order_material_requirement_service"]
    task_step_template_service = services["maintenance_task_step_template_service"]
    preventive_plan_task_service = services["maintenance_preventive_plan_task_service"]
    downtime_event_service = services["maintenance_downtime_event_service"]

    # Current org secondary entities (root seeder leaves context as current_org)
    current_component = component_service.create_component(
        asset_id=root["current_asset_id"],
        component_code="SCOPE-COMP",
        name="CUR Scoped Component",
    )
    current_sensor_reading = sensor_reading_service.record_reading(
        sensor_id=root["current_sensor_id"],
        reading_value=42.0,
        reading_unit="H",
    )
    current_sensor_source_mapping = sensor_source_mapping_service.create_mapping(
        integration_source_id=root["current_integration_source_id"],
        sensor_id=root["current_sensor_id"],
        external_measurement_key="CUR.SENSOR.RUN_HOURS",
    )
    current_sensor_exception = sensor_exception_service.raise_exception(
        exception_type="EXTERNAL_SYNC_FAILURE",
        message="CUR sensor sync failure",
        sensor_id=root["current_sensor_id"],
    )
    current_work_order_task = work_order_task_service.create_task(
        work_order_id=root["current_work_order_id"],
        task_name="CUR Scoped WO Task",
    )
    current_work_order_task_step = work_order_task_step_service.create_step(
        work_order_task_id=current_work_order_task.id,
        instruction="CUR: Perform inspection step.",
    )
    current_material_requirement = material_requirement_service.create_requirement(
        work_order_id=root["current_work_order_id"],
        description="CUR Spare Part",
        required_qty=1,
        required_uom="EA",
        is_stock_item=False,
    )
    current_task_step_template = task_step_template_service.create_step_template(
        task_template_id=root["current_task_template_id"],
        step_number=1,
        instruction="CUR: Inspect component.",
    )
    current_preventive_plan_task = preventive_plan_task_service.create_plan_task(
        plan_id=root["current_preventive_plan_id"],
        task_template_id=root["current_task_template_id"],
    )
    current_downtime_event = downtime_event_service.create_downtime_event(
        started_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        downtime_type="unplanned",
        work_order_id=root["current_work_order_id"],
    )
    current_plan_instance_repo = SqlAlchemyMaintenancePreventivePlanInstanceRepository(
        services["session"],
        tenant_context_service=services["tenant_context_service"],
    )
    current_plan_instance = MaintenancePreventivePlanInstance.create(
        organization_id=root["current_org_id"],
        plan_id=root["current_preventive_plan_id"],
        due_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
    )
    current_plan_instance_repo.add(current_plan_instance)
    services["session"].flush()

    # Switch to other org for secondary entities
    organization_service.set_active_organization(root["other_org_id"])

    other_component = component_service.create_component(
        asset_id=root["other_asset_id"],
        component_code="SCOPE-COMP",
        name="OTH Scoped Component",
    )
    other_sensor_reading = sensor_reading_service.record_reading(
        sensor_id=root["other_sensor_id"],
        reading_value=99.0,
        reading_unit="H",
    )
    other_sensor_source_mapping = sensor_source_mapping_service.create_mapping(
        integration_source_id=root["other_integration_source_id"],
        sensor_id=root["other_sensor_id"],
        external_measurement_key="OTH.SENSOR.RUN_HOURS",
    )
    other_sensor_exception = sensor_exception_service.raise_exception(
        exception_type="EXTERNAL_SYNC_FAILURE",
        message="OTH sensor sync failure",
        sensor_id=root["other_sensor_id"],
    )
    other_work_order_task = work_order_task_service.create_task(
        work_order_id=root["other_work_order_id"],
        task_name="OTH Scoped WO Task",
    )
    other_work_order_task_step = work_order_task_step_service.create_step(
        work_order_task_id=other_work_order_task.id,
        instruction="OTH: Perform inspection step.",
    )
    other_material_requirement = material_requirement_service.create_requirement(
        work_order_id=root["other_work_order_id"],
        description="OTH Spare Part",
        required_qty=1,
        required_uom="EA",
        is_stock_item=False,
    )
    other_task_step_template = task_step_template_service.create_step_template(
        task_template_id=root["other_task_template_id"],
        step_number=1,
        instruction="OTH: Inspect component.",
    )
    other_preventive_plan_task = preventive_plan_task_service.create_plan_task(
        plan_id=root["other_preventive_plan_id"],
        task_template_id=root["other_task_template_id"],
    )
    other_downtime_event = downtime_event_service.create_downtime_event(
        started_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        downtime_type="unplanned",
        work_order_id=root["other_work_order_id"],
    )
    other_plan_instance_repo = SqlAlchemyMaintenancePreventivePlanInstanceRepository(
        services["session"],
        tenant_context_service=services["tenant_context_service"],
    )
    other_plan_instance = MaintenancePreventivePlanInstance.create(
        organization_id=root["other_org_id"],
        plan_id=root["other_preventive_plan_id"],
        due_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
        generated_work_order_id=root["other_work_order_id"],
    )
    other_plan_instance_repo.add(other_plan_instance)
    services["session"].flush()

    # Restore current org context
    organization_service.set_active_organization(root["current_org_id"])

    return {
        **root,
        "current_component_id": current_component.id,
        "current_component_code": current_component.component_code,
        "current_component": current_component,
        "other_component_id": other_component.id,
        "other_component": other_component,
        "current_sensor_reading_id": current_sensor_reading.id,
        "other_sensor_reading_id": other_sensor_reading.id,
        "current_sensor_source_mapping_id": current_sensor_source_mapping.id,
        "other_sensor_source_mapping_id": other_sensor_source_mapping.id,
        "current_sensor_source_mapping": current_sensor_source_mapping,
        "other_sensor_source_mapping": other_sensor_source_mapping,
        "current_sensor_exception_id": current_sensor_exception.id,
        "other_sensor_exception_id": other_sensor_exception.id,
        "current_sensor_exception": current_sensor_exception,
        "other_sensor_exception": other_sensor_exception,
        "current_work_order_task_id": current_work_order_task.id,
        "other_work_order_task_id": other_work_order_task.id,
        "current_work_order_task": current_work_order_task,
        "other_work_order_task": other_work_order_task,
        "current_work_order_task_step_id": current_work_order_task_step.id,
        "other_work_order_task_step_id": other_work_order_task_step.id,
        "current_work_order_task_step": current_work_order_task_step,
        "other_work_order_task_step": other_work_order_task_step,
        "current_material_requirement_id": current_material_requirement.id,
        "other_material_requirement_id": other_material_requirement.id,
        "current_material_requirement": current_material_requirement,
        "other_material_requirement": other_material_requirement,
        "current_task_step_template_id": current_task_step_template.id,
        "other_task_step_template_id": other_task_step_template.id,
        "current_task_step_template": current_task_step_template,
        "other_task_step_template": other_task_step_template,
        "current_preventive_plan_task_id": current_preventive_plan_task.id,
        "other_preventive_plan_task_id": other_preventive_plan_task.id,
        "current_preventive_plan_task": current_preventive_plan_task,
        "other_preventive_plan_task": other_preventive_plan_task,
        "current_downtime_event_id": current_downtime_event.id,
        "other_downtime_event_id": other_downtime_event.id,
        "current_downtime_event": current_downtime_event,
        "other_downtime_event": other_downtime_event,
        "current_preventive_plan_instance_id": current_plan_instance.id,
        "other_preventive_plan_instance_id": other_plan_instance.id,
        "current_preventive_plan_instance": current_plan_instance,
        "other_preventive_plan_instance": other_plan_instance,
    }
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
