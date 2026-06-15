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
    _seed_maintenance_secondary_scope_rows,
)


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
