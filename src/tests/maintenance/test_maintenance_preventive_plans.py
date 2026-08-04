from __future__ import annotations

from decimal import Decimal

from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceLocation,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceSensor,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
)
from src.core.modules.maintenance.contracts.repositories import (
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from src.core.modules.maintenance import (
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.org.domain import Organization
from src.core.platform.domain.master_data.site import Site
from .test_maintenance_foundation_asset import (
    _AssetRepo,
    _LocationRepo,
    _OrgRepo,
    _SiteRepo,
    _SystemRepo,
    _TenantContext,
    _user_session,
)
from .test_maintenance_sensor_foundation import _SensorRepo
from .test_maintenance_preventive_foundation_task_template import (
    _PreventivePlanRepo,
    _PreventivePlanTaskRepo,
    _TaskTemplateRepo,
    _TaskStepTemplateRepo,
)
from .test_maintenance_foundation_component import _ComponentRepo

def test_maintenance_preventive_plan_service_creates_hybrid_asset_plan(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-PM",
        name="PM Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-PM",
        name="PM Asset",
    )
    sensor = MaintenanceSensor.create(
        organization_id=organization.id,
        site_id=site.id,
        sensor_code="SNS-PM",
        sensor_name="Running Hours",
        asset_id=asset.id,
        sensor_type="RUNNING_HOURS",
        unit="H",
    )
    asset_repo = _AssetRepo()
    asset_repo.add(asset)
    location_repo = _LocationRepo()
    location_repo.add(location)
    sensor_repo = _SensorRepo()
    sensor_repo.add(sensor)
    service = MaintenancePreventivePlanService(
        session,
        _PreventivePlanRepo(),
        organization_repo=_OrgRepo(organization),
        site_repo=_SiteRepo([site]),
        asset_repo=asset_repo,
        component_repo=_ComponentRepo(),
        system_repo=_SystemRepo(),
        sensor_repo=sensor_repo,
        tenant_context_service=_TenantContext(organization),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    plan = service.create_preventive_plan(
        site_id=site.id,
        plan_code="pm-asset-100",
        name="Asset 100 PM",
        asset_id=asset.id,
        trigger_mode="hybrid",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        sensor_id=sensor.id,
        sensor_threshold="500.0",
        sensor_direction="greater_or_equal",
        auto_generate_work_order=True,
    )

    assert plan.plan_code == "PM-ASSET-100"
    assert plan.trigger_mode.value == "HYBRID"
    assert plan.sensor_id == sensor.id
    assert service.find_preventive_plan_by_code("pm-asset-100").id == plan.id
    assert captured[-1].entity_type == "maintenance_preventive_plan"
    assert captured[-1].source_event == "maintenance_preventive_plans_changed"


def test_maintenance_preventive_plan_task_service_validates_override_sequences(session) -> None:
    organization = Organization.create("ORG", "Org")
    site = Site.create(organization.id, "MAIN", "Main Site")
    location = MaintenanceLocation.create(
        organization_id=organization.id,
        site_id=site.id,
        location_code="AREA-PLAN",
        name="Plan Area",
    )
    asset = MaintenanceAsset.create(
        organization_id=organization.id,
        site_id=site.id,
        location_id=location.id,
        asset_code="ASSET-PLAN",
        name="Plan Asset",
    )
    sensor = MaintenanceSensor.create(
        organization_id=organization.id,
        site_id=site.id,
        sensor_code="SNS-PLAN",
        sensor_name="Vibration",
        asset_id=asset.id,
        sensor_type="VIBRATION",
        unit="MM/S",
    )
    plan = MaintenancePreventivePlan.create(
        organization_id=organization.id,
        site_id=site.id,
        plan_code="PLAN-100",
        name="Plan 100",
        asset_id=asset.id,
        trigger_mode="CALENDAR",
        calendar_frequency_unit="MONTHLY",
        calendar_frequency_value=1,
    )
    task_template_repo = _TaskTemplateRepo()
    task_template = MaintenanceTaskTemplate.create(
        organization_id=organization.id,
        task_template_code="TPL-100",
        name="Inspect bearings",
        template_status="ACTIVE",
    )
    task_template_repo.add(task_template)
    plan_repo = _PreventivePlanRepo()
    plan_repo.add(plan)
    sensor_repo = _SensorRepo()
    sensor_repo.add(sensor)
    service = MaintenancePreventivePlanTaskService(
        session,
        _PreventivePlanTaskRepo(),
        organization_repo=_OrgRepo(organization),
        preventive_plan_repo=plan_repo,
        task_template_repo=task_template_repo,
        sensor_repo=sensor_repo,
        component_repo=_ComponentRepo(),
        tenant_context_service=_TenantContext(organization),
        user_session=_user_session(),
    )

    first = service.create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        trigger_scope="task_override",
        trigger_mode_override="sensor",
        sensor_id_override=sensor.id,
        sensor_threshold_override="7.5",
        sensor_direction_override="greater_or_equal",
        sequence_no=1,
    )

    assert first.sequence_no == 1
    assert first.trigger_scope.value == "TASK_OVERRIDE"
    assert first.sensor_threshold_override == Decimal("7.5")

    try:
        service.create_plan_task(
            plan_id=plan.id,
            task_template_id=task_template.id,
            sequence_no=1,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_PREVENTIVE_PLAN_TASK_SEQUENCE_EXISTS"
    else:
        raise AssertionError("Expected duplicate preventive-plan-task sequence validation error.")
