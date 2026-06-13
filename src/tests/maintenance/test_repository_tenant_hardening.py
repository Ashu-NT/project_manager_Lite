from __future__ import annotations

import pytest

from src.core.modules.maintenance.infrastructure.persistence.repositories.repository import (
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceIntegrationSourceRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenancePreventivePlanRepository,
    SqlAlchemyMaintenanceSensorRepository,
    SqlAlchemyMaintenanceSystemRepository,
    SqlAlchemyMaintenanceTaskTemplateRepository,
    SqlAlchemyMaintenanceWorkOrderRepository,
    SqlAlchemyMaintenanceWorkRequestRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories.reliability_repository import (
    SqlAlchemyMaintenanceFailureCodeRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


def _maintenance_repo(repo_factory, services):
    repo = repo_factory(services["session"])
    repo._tenant_context_service = services["tenant_context_service"]
    return repo


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
        "current_system_id": current_rows["system"].id,
        "other_system_id": other_rows["system"].id,
        "current_system_code": current_rows["system"].system_code,
        "current_asset_id": current_rows["asset"].id,
        "other_asset_id": other_rows["asset"].id,
        "current_asset_code": current_rows["asset"].asset_code,
        "current_sensor_id": current_rows["sensor"].id,
        "other_sensor_id": other_rows["sensor"].id,
        "current_sensor_code": current_rows["sensor"].sensor_code,
        "current_integration_source_id": current_rows["integration_source"].id,
        "other_integration_source_id": other_rows["integration_source"].id,
        "current_integration_code": current_rows["integration_source"].integration_code,
        "current_failure_code_id": current_rows["failure_code"].id,
        "other_failure_code_id": other_rows["failure_code"].id,
        "current_failure_code": current_rows["failure_code"].failure_code,
        "current_task_template_id": current_rows["task_template"].id,
        "other_task_template_id": other_rows["task_template"].id,
        "current_task_template_code": current_rows["task_template"].task_template_code,
        "current_work_request_id": current_rows["work_request"].id,
        "other_work_request_id": other_rows["work_request"].id,
        "current_work_request_code": current_rows["work_request"].work_request_code,
        "current_work_order_id": current_rows["work_order"].id,
        "other_work_order_id": other_rows["work_order"].id,
        "current_work_order_code": current_rows["work_order"].work_order_code,
        "current_preventive_plan_id": current_rows["preventive_plan"].id,
        "other_preventive_plan_id": other_rows["preventive_plan"].id,
        "current_preventive_plan_code": current_rows["preventive_plan"].plan_code,
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
    repo = repo_factory(session)
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        operation(repo)


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
