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
