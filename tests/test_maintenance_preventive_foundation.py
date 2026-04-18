from __future__ import annotations

from decimal import Decimal

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceLocation,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceSensor,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
)
from core.modules.maintenance_management.interfaces import (
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from core.modules.maintenance_management.services import (
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.org.domain import Organization, Site
from tests.test_maintenance_foundation import (
    _AssetRepo,
    _ComponentRepo,
    _LocationRepo,
    _OrgRepo,
    _SiteRepo,
    _SystemRepo,
    _user_session,
)
from tests.test_maintenance_sensor_foundation import _SensorRepo


class _TaskTemplateRepo(MaintenanceTaskTemplateRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceTaskTemplate] = {}

    def add(self, task_template: MaintenanceTaskTemplate) -> None:
        self._rows[task_template.id] = task_template

    def update(self, task_template: MaintenanceTaskTemplate) -> None:
        task_template.version += 1
        self._rows[task_template.id] = task_template

    def get(self, task_template_id: str):
        return self._rows.get(task_template_id)

    def get_by_code(self, organization_id: str, task_template_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.task_template_code == task_template_code:
                return row
        return None

    def list_for_organization(self, organization_id: str, *, active_only=None, maintenance_type=None, template_status=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if maintenance_type is not None:
            rows = [row for row in rows if row.maintenance_type == maintenance_type]
        if template_status is not None:
            rows = [row for row in rows if row.template_status == template_status]
        return rows


class _TaskStepTemplateRepo(MaintenanceTaskStepTemplateRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenanceTaskStepTemplate] = {}

    def add(self, task_step_template: MaintenanceTaskStepTemplate) -> None:
        self._rows[task_step_template.id] = task_step_template

    def update(self, task_step_template: MaintenanceTaskStepTemplate) -> None:
        task_step_template.version += 1
        self._rows[task_step_template.id] = task_step_template

    def get(self, task_step_template_id: str):
        return self._rows.get(task_step_template_id)

    def list_for_organization(self, organization_id: str, *, task_template_id=None, active_only=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if task_template_id is not None:
            rows = [row for row in rows if row.task_template_id == task_template_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        return rows


class _PreventivePlanRepo(MaintenancePreventivePlanRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenancePreventivePlan] = {}

    def add(self, preventive_plan: MaintenancePreventivePlan) -> None:
        self._rows[preventive_plan.id] = preventive_plan

    def update(self, preventive_plan: MaintenancePreventivePlan) -> None:
        preventive_plan.version += 1
        self._rows[preventive_plan.id] = preventive_plan

    def get(self, preventive_plan_id: str):
        return self._rows.get(preventive_plan_id)

    def get_by_code(self, organization_id: str, plan_code: str):
        for row in self._rows.values():
            if row.organization_id == organization_id and row.plan_code == plan_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only=None,
        site_id=None,
        asset_id=None,
        component_id=None,
        system_id=None,
        status=None,
        plan_type=None,
        trigger_mode=None,
        sensor_id=None,
    ):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active == bool(active_only)]
        if site_id is not None:
            rows = [row for row in rows if row.site_id == site_id]
        if asset_id is not None:
            rows = [row for row in rows if row.asset_id == asset_id]
        if component_id is not None:
            rows = [row for row in rows if row.component_id == component_id]
        if system_id is not None:
            rows = [row for row in rows if row.system_id == system_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if plan_type is not None:
            rows = [row for row in rows if row.plan_type == plan_type]
        if trigger_mode is not None:
            rows = [row for row in rows if row.trigger_mode == trigger_mode]
        if sensor_id is not None:
            rows = [row for row in rows if row.sensor_id == sensor_id]
        return rows


class _PreventivePlanTaskRepo(MaintenancePreventivePlanTaskRepository):
    def __init__(self) -> None:
        self._rows: dict[str, MaintenancePreventivePlanTask] = {}

    def add(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None:
        self._rows[preventive_plan_task.id] = preventive_plan_task

    def update(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None:
        preventive_plan_task.version += 1
        self._rows[preventive_plan_task.id] = preventive_plan_task

    def get(self, preventive_plan_task_id: str):
        return self._rows.get(preventive_plan_task_id)

    def list_for_organization(self, organization_id: str, *, plan_id=None, task_template_id=None):
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if plan_id is not None:
            rows = [row for row in rows if row.plan_id == plan_id]
        if task_template_id is not None:
            rows = [row for row in rows if row.task_template_id == task_template_id]
        return rows


def test_maintenance_task_template_service_creates_searches_and_emits_events(session) -> None:
    organization = Organization.create("ORG", "Org")
    service = MaintenanceTaskTemplateService(
        session,
        _TaskTemplateRepo(),
        organization_repo=_OrgRepo(organization),
        user_session=_user_session(),
    )
    captured = []
    domain_events.domain_changed.connect(captured.append)

    template = service.create_task_template(
        task_template_code="pm-pump-lube",
        name="Pump Lubrication",
        maintenance_type="preventive",
        revision_no=2,
        template_status="active",
        estimated_minutes=45,
        required_skill="MECHANICAL",
        requires_shutdown=True,
    )

    assert template.task_template_code == "PM-PUMP-LUBE"
    assert template.template_status.value == "ACTIVE"
    assert service.find_task_template_by_code("pm-pump-lube").id == template.id
    assert service.search_task_templates(search_text="lube")[0].id == template.id
    assert captured[-1].entity_type == "maintenance_task_template"
    assert captured[-1].source_event == "maintenance_task_templates_changed"


def test_maintenance_task_step_template_service_rejects_duplicate_step_numbers(session) -> None:
    organization = Organization.create("ORG", "Org")
    task_template_repo = _TaskTemplateRepo()
    template = MaintenanceTaskTemplate.create(
        organization_id=organization.id,
        task_template_code="PM-SEAL",
        name="Seal PM",
    )
    task_template_repo.add(template)
    service = MaintenanceTaskStepTemplateService(
        session,
        _TaskStepTemplateRepo(),
        organization_repo=_OrgRepo(organization),
        task_template_repo=task_template_repo,
        user_session=_user_session(),
    )

    first = service.create_step_template(
        task_template_id=template.id,
        step_number=1,
        instruction="Lock out and tag out",
        requires_confirmation=True,
    )
    assert first.step_number == 1

    try:
        service.create_step_template(
            task_template_id=template.id,
            step_number=1,
            instruction="Duplicate step",
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_TASK_STEP_TEMPLATE_STEP_EXISTS"
    else:
        raise AssertionError("Expected duplicate task-step-template validation error.")


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
