from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.core.modules.maintenance.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceBlackoutWindow,
    MaintenanceCriticality,
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceIntegrationSource,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
    MaintenanceMaterialProcurementStatus,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanInstance,
    MaintenancePreventivePlanTask,
    MaintenanceSensor,
    MaintenanceSensorException,
    MaintenanceSensorReading,
    MaintenanceSensorSourceMapping,
    MaintenanceSystem,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStep,
    MaintenanceWorkOrderTaskStepStatus,
    MaintenanceWorkRequest,
)
from src.core.platform.common.exceptions import ValidationError


def test_maintenance_location_and_system_dtos_normalize_fields() -> None:
    location = MaintenanceLocation.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        location_code="  area-1  ",
        name="  Area 1  ",
        description="  Main production area  ",
        parent_location_id="  parent-1  ",
        location_type="  process  ",
        criticality="high",
        is_active=False,
        notes="  Monitored daily  ",
    )

    assert location.organization_id == "org-1"
    assert location.site_id == "site-1"
    assert location.location_code == "AREA-1"
    assert location.name == "Area 1"
    assert location.description == "Main production area"
    assert location.parent_location_id == "parent-1"
    assert location.location_type == "process"
    assert location.criticality is MaintenanceCriticality.HIGH
    assert location.status is MaintenanceLifecycleStatus.INACTIVE
    assert location.notes == "Monitored daily"

    location.version = "2"
    assert location.version == 2

    system = MaintenanceSystem.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        system_code="  cw-001  ",
        name="  Cooling Water  ",
        location_id="  location-1  ",
        parent_system_id="  parent-system  ",
        system_type="  utility  ",
        status="active",
        notes="  Core loop  ",
    )

    assert system.system_code == "CW-001"
    assert system.name == "Cooling Water"
    assert system.location_id == "location-1"
    assert system.parent_system_id == "parent-system"
    assert system.system_type == "utility"
    assert system.status is MaintenanceLifecycleStatus.ACTIVE
    assert system.notes == "Core loop"


def test_maintenance_asset_dto_normalizes_fields_and_validates_ranges() -> None:
    asset = MaintenanceAsset.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        location_id="  loc-1  ",
        asset_code="  pump-001  ",
        name="  Boiler Feed Pump  ",
        system_id="  sys-1  ",
        description="  Primary duty pump  ",
        parent_asset_id="  asset-parent  ",
        asset_type="  pump  ",
        asset_category="  rotating  ",
        criticality="critical",
        manufacturer_party_id="  party-mfg  ",
        supplier_party_id="  party-sup  ",
        model_number="  mdl-22  ",
        serial_number="  sn-900  ",
        barcode="  bc-500  ",
        install_date="2025-01-10",
        commission_date="2025-01-15",
        warranty_start=date(2025, 1, 15),
        warranty_end="2027-01-15",
        expected_life_years="12",
        replacement_cost="12500.50",
        maintenance_strategy="  cbm  ",
        service_level="  critical  ",
        requires_shutdown_for_major_work=True,
        notes="  Inspect monthly  ",
    )

    assert asset.organization_id == "org-1"
    assert asset.asset_code == "PUMP-001"
    assert asset.name == "Boiler Feed Pump"
    assert asset.system_id == "sys-1"
    assert asset.description == "Primary duty pump"
    assert asset.parent_asset_id == "asset-parent"
    assert asset.asset_type == "pump"
    assert asset.asset_category == "ROTATING"
    assert asset.criticality is MaintenanceCriticality.CRITICAL
    assert asset.manufacturer_party_id == "party-mfg"
    assert asset.supplier_party_id == "party-sup"
    assert asset.model_number == "mdl-22"
    assert asset.serial_number == "sn-900"
    assert asset.barcode == "bc-500"
    assert asset.install_date == date(2025, 1, 10)
    assert asset.commission_date == date(2025, 1, 15)
    assert asset.warranty_end == date(2027, 1, 15)
    assert asset.expected_life_years == 12
    assert asset.replacement_cost == Decimal("12500.50")
    assert asset.maintenance_strategy == "cbm"
    assert asset.service_level == "critical"
    assert asset.notes == "Inspect monthly"

    asset.updated_at = datetime(2026, 7, 26, 8, 30, 0)
    asset.version = "2"

    assert asset.updated_at == datetime(2026, 7, 26, 8, 30, 0, tzinfo=timezone.utc)
    assert asset.version == 2

    with pytest.raises(ValidationError) as exc_date_sequence:
        MaintenanceAsset.create(
            organization_id="org-1",
            site_id="site-1",
            location_id="loc-1",
            asset_code="PUMP-002",
            name="Bad Commission Window",
            install_date="2025-02-10",
            commission_date="2025-02-01",
        )
    assert exc_date_sequence.value.code == "MAINTENANCE_ASSET_DATE_SEQUENCE_INVALID"

    with pytest.raises(ValidationError) as exc_warranty_range:
        MaintenanceAsset.create(
            organization_id="org-1",
            site_id="site-1",
            location_id="loc-1",
            asset_code="PUMP-003",
            name="Bad Warranty Window",
            warranty_start="2025-04-10",
            warranty_end="2025-04-01",
        )
    assert exc_warranty_range.value.code == "MAINTENANCE_ASSET_WARRANTY_RANGE_INVALID"


def test_maintenance_component_dto_normalizes_fields_and_validates_ranges() -> None:
    component = MaintenanceAssetComponent.create(
        organization_id="  org-1  ",
        asset_id="  asset-1  ",
        component_code="  seal-001  ",
        name="  Seal Cartridge  ",
        description="  Dual mechanical seal  ",
        parent_component_id="  parent-1  ",
        component_type="  seal  ",
        supplier_party_id="  supplier-1  ",
        manufacturer_part_number="  mpn-1  ",
        supplier_part_number="  spn-1  ",
        model_number="  mdl-1  ",
        serial_number="  sn-1  ",
        install_date="2025-03-01",
        warranty_end="2026-03-01",
        expected_life_hours="12000",
        expected_life_cycles="5000",
        is_critical_component=True,
        notes="  Spare kept onsite  ",
    )

    assert component.organization_id == "org-1"
    assert component.asset_id == "asset-1"
    assert component.component_code == "SEAL-001"
    assert component.name == "Seal Cartridge"
    assert component.description == "Dual mechanical seal"
    assert component.parent_component_id == "parent-1"
    assert component.component_type == "SEAL"
    assert component.supplier_party_id == "supplier-1"
    assert component.manufacturer_part_number == "mpn-1"
    assert component.supplier_part_number == "spn-1"
    assert component.expected_life_hours == 12000
    assert component.expected_life_cycles == 5000
    assert component.is_critical_component is True
    assert component.notes == "Spare kept onsite"

    component.status = "inactive"
    component.version = "2"

    assert component.status is MaintenanceLifecycleStatus.INACTIVE
    assert component.version == 2

    with pytest.raises(ValidationError) as exc_warranty:
        MaintenanceAssetComponent.create(
            organization_id="org-1",
            asset_id="asset-1",
            component_code="SEAL-002",
            name="Bad Seal",
            install_date="2025-03-10",
            warranty_end="2025-03-01",
        )
    assert exc_warranty.value.code == "MAINTENANCE_COMPONENT_WARRANTY_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_version:
        component.version = 0
    assert exc_version.value.code == "MAINTENANCE_COMPONENT_VERSION_INVALID"


def test_maintenance_work_request_dto_normalizes_fields_and_validates_ranges() -> None:
    work_request = MaintenanceWorkRequest.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        work_request_code="  wr-100  ",
        source_type="manual",
        source_id="  src-1  ",
        source_plan_task_ids=["  task-1  ", "", "task-2"],
        request_type="  breakdown  ",
        asset_id="  asset-1  ",
        component_id="  component-1  ",
        system_id="  system-1  ",
        location_id="  location-1  ",
        title="  Pump leak  ",
        description="  Seal leak on discharge side  ",
        priority="high",
        requested_by_user_id="  user-1  ",
        requested_by_name_snapshot="  Maintenance Admin  ",
        failure_symptom_code="  leak  ",
        safety_risk_level="  medium  ",
        production_impact_level="  high  ",
        notes="  Inspect on next stop  ",
    )

    assert work_request.organization_id == "org-1"
    assert work_request.site_id == "site-1"
    assert work_request.work_request_code == "WR-100"
    assert work_request.source_type.value == "MANUAL"
    assert work_request.source_id == "src-1"
    assert work_request.source_plan_task_ids == ("task-1", "task-2")
    assert work_request.request_type == "BREAKDOWN"
    assert work_request.asset_id == "asset-1"
    assert work_request.component_id == "component-1"
    assert work_request.system_id == "system-1"
    assert work_request.location_id == "location-1"
    assert work_request.title == "Pump leak"
    assert work_request.description == "Seal leak on discharge side"
    assert work_request.priority.value == "HIGH"
    assert work_request.requested_by_user_id == "user-1"
    assert work_request.requested_by_name_snapshot == "Maintenance Admin"
    assert work_request.failure_symptom_code == "LEAK"
    assert work_request.safety_risk_level == "MEDIUM"
    assert work_request.production_impact_level == "HIGH"
    assert work_request.notes == "Inspect on next stop"

    work_request.status = "triaged"
    assert work_request.status.value == "TRIAGED"

    work_request.requested_at = datetime(2026, 7, 26, 9, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_range:
        work_request.triaged_at = datetime(2026, 7, 26, 8, 0, 0, tzinfo=timezone.utc)
    assert exc_range.value.code == "MAINTENANCE_WORK_REQUEST_TRIAGE_RANGE_INVALID"


def test_maintenance_work_order_dto_normalizes_fields_and_validates_ranges() -> None:
    work_order = MaintenanceWorkOrder.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        work_order_code="  wo-100  ",
        work_order_type="corrective",
        source_type="manual",
        source_id="  src-1  ",
        asset_id="  asset-1  ",
        location_id="  location-1  ",
        title="  Replace coupling  ",
        description="  Correct shaft misalignment  ",
        priority="emergency",
        assigned_team_id="  TEAM-A  ",
        planned_start="2026-07-26T08:00:00",
        planned_end="2026-07-26T10:00:00",
        vendor_party_id="  vendor-1  ",
        notes="  Prepare lockout permit  ",
    )

    assert work_order.organization_id == "org-1"
    assert work_order.work_order_code == "WO-100"
    assert work_order.work_order_type.value == "CORRECTIVE"
    assert work_order.source_type == "MANUAL"
    assert work_order.source_id == "src-1"
    assert work_order.asset_id == "asset-1"
    assert work_order.location_id == "location-1"
    assert work_order.title == "Replace coupling"
    assert work_order.description == "Correct shaft misalignment"
    assert work_order.priority.value == "EMERGENCY"
    assert work_order.assigned_team_id == "TEAM-A"
    assert work_order.vendor_party_id == "vendor-1"
    assert work_order.notes == "Prepare lockout permit"

    work_order.parts_cost = "150.25"
    assert work_order.parts_cost == Decimal("150.25")

    with pytest.raises(ValidationError) as exc_range:
        work_order.planned_end = datetime(2026, 7, 26, 7, 0, 0, tzinfo=timezone.utc)
    assert exc_range.value.code == "MAINTENANCE_WORK_ORDER_PLANNED_RANGE_INVALID"


def test_maintenance_work_order_task_dto_normalizes_fields_and_validates_ranges() -> None:
    task = MaintenanceWorkOrderTask.create(
        organization_id="  org-1  ",
        work_order_id="  wo-1  ",
        task_template_id="  template-1  ",
        task_name="  Isolate power  ",
        description="  Lock and tag out supply  ",
        assigned_team_id="  TEAM-LOCKOUT  ",
        estimated_minutes="30",
        actual_minutes="25",
        required_skill="  Electrical  ",
        sequence_no="2",
        completion_rule="all_steps_required",
        notes="  Verify zero energy  ",
    )

    assert task.organization_id == "org-1"
    assert task.work_order_id == "wo-1"
    assert task.task_template_id == "template-1"
    assert task.task_name == "Isolate power"
    assert task.description == "Lock and tag out supply"
    assert task.assigned_team_id == "TEAM-LOCKOUT"
    assert task.estimated_minutes == 30
    assert task.actual_minutes == 25
    assert task.required_skill == "Electrical"
    assert task.sequence_no == 2
    assert task.completion_rule.value == "ALL_STEPS_REQUIRED"
    assert task.notes == "Verify zero energy"

    task.started_at = datetime(2026, 7, 26, 9, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_range:
        task.completed_at = datetime(2026, 7, 26, 8, 45, 0, tzinfo=timezone.utc)
    assert exc_range.value.code == "MAINTENANCE_WORK_ORDER_TASK_RANGE_INVALID"


def test_maintenance_work_order_task_step_dto_normalizes_fields_and_requires_measurement() -> None:
    step = MaintenanceWorkOrderTaskStep.create(
        organization_id="  org-1  ",
        work_order_task_id="  task-1  ",
        source_step_template_id="  step-template-1  ",
        step_number="3",
        instruction="  Record final vibration  ",
        expected_result="  Within operating band  ",
        hint_level="  warning  ",
        hint_text="  Use handheld meter  ",
        requires_measurement=True,
        measurement_unit="  mm/s  ",
        notes="  Capture motor end reading  ",
    )

    assert step.organization_id == "org-1"
    assert step.work_order_task_id == "task-1"
    assert step.source_step_template_id == "step-template-1"
    assert step.step_number == 3
    assert step.instruction == "Record final vibration"
    assert step.expected_result == "Within operating band"
    assert step.hint_level == "WARNING"
    assert step.hint_text == "Use handheld meter"
    assert step.measurement_unit == "mm/s"
    assert step.notes == "Capture motor end reading"

    with pytest.raises(ValidationError) as exc_measurement:
        step.status = "done"
    assert exc_measurement.value.code == "MAINTENANCE_WORK_ORDER_TASK_STEP_MEASUREMENT_REQUIRED"

    step.measurement_value = "2.3"
    step.status = "done"
    assert step.status is MaintenanceWorkOrderTaskStepStatus.DONE
    assert step.measurement_value == "2.3"


def test_maintenance_material_requirement_dto_normalizes_and_validates_quantities() -> None:
    requirement = MaintenanceWorkOrderMaterialRequirement.create(
        organization_id="  org-1  ",
        work_order_id="  wo-1  ",
        stock_item_id="  item-1  ",
        required_qty="5",
        issued_qty="2",
        preferred_storeroom_id="  store-1  ",
        notes="  Issue before shutdown  ",
    )

    assert requirement.organization_id == "org-1"
    assert requirement.work_order_id == "wo-1"
    assert requirement.stock_item_id == "item-1"
    assert requirement.required_qty == Decimal("5")
    assert requirement.issued_qty == Decimal("2")
    assert requirement.preferred_storeroom_id == "store-1"
    assert requirement.procurement_status is MaintenanceMaterialProcurementStatus.PLANNED
    assert requirement.notes == "Issue before shutdown"

    with pytest.raises(ValidationError) as exc_issued:
        requirement.issued_qty = "6"
    assert exc_issued.value.code == "MAINTENANCE_MATERIAL_ISSUED_QTY_EXCEEDS_REQUIRED"

    with pytest.raises(ValidationError) as exc_non_stock:
        MaintenanceWorkOrderMaterialRequirement.create(
            organization_id="org-1",
            work_order_id="wo-1",
            is_stock_item=False,
            required_qty="1",
        )
    assert exc_non_stock.value.code == "MAINTENANCE_MATERIAL_DESCRIPTION_REQUIRED"


def test_maintenance_preventive_dtos_normalize_fields() -> None:
    task_template = MaintenanceTaskTemplate.create(
        organization_id="  org-1  ",
        task_template_code="  tpl-100  ",
        name="  Inspect Pump  ",
        description="  Monthly inspection route  ",
        maintenance_type="  lubrication  ",
        revision_no="2",
        template_status="active",
        estimated_minutes="45",
        required_skill="  mechanical  ",
        notes="  Capture abnormal noise  ",
    )
    step_template = MaintenanceTaskStepTemplate.create(
        organization_id="  org-1  ",
        task_template_id="  template-1  ",
        step_number="2",
        instruction="  Record vibration reading  ",
        expected_result="  Within normal band  ",
        hint_level="  warning  ",
        hint_text="  Use handheld meter  ",
        requires_measurement=True,
        measurement_unit="  mm/s  ",
        sort_order="5",
        notes="  Capture motor-end reading  ",
    )
    plan = MaintenancePreventivePlan.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        plan_code="  pm-100  ",
        name="  Pump PM  ",
        asset_id="  asset-1  ",
        description="  Monthly route  ",
        status="active",
        plan_type="lubrication",
        priority="high",
        trigger_mode="calendar",
        schedule_policy="floating",
        calendar_frequency_unit="monthly",
        calendar_frequency_value="2",
        generation_horizon_count="0",
        generation_lead_value=None,
        generation_lead_unit="weeks",
        sensor_reset_rule="  Reset on completion  ",
        notes="  Coordinate with operations  ",
    )
    plan_task = MaintenancePreventivePlanTask.create(
        organization_id="  org-1  ",
        plan_id="  plan-1  ",
        task_template_id="  template-1  ",
        trigger_scope="task_override",
        calendar_frequency_unit_override="weekly",
        calendar_frequency_value_override="1",
        sequence_no="3",
        default_assigned_employee_id="  emp-1  ",
        default_assigned_team_id="  team-a  ",
        estimated_minutes_override="25",
        notes="  Weekly override for startup period  ",
    )

    assert task_template.organization_id == "org-1"
    assert task_template.task_template_code == "TPL-100"
    assert task_template.name == "Inspect Pump"
    assert task_template.description == "Monthly inspection route"
    assert task_template.maintenance_type == "LUBRICATION"
    assert task_template.revision_no == 2
    assert task_template.template_status.value == "ACTIVE"
    assert task_template.estimated_minutes == 45
    assert task_template.required_skill == "mechanical"
    assert task_template.notes == "Capture abnormal noise"

    assert step_template.task_template_id == "template-1"
    assert step_template.step_number == 2
    assert step_template.instruction == "Record vibration reading"
    assert step_template.expected_result == "Within normal band"
    assert step_template.hint_level == "WARNING"
    assert step_template.hint_text == "Use handheld meter"
    assert step_template.measurement_unit == "MM/S"
    assert step_template.sort_order == 5
    assert step_template.notes == "Capture motor-end reading"

    assert plan.site_id == "site-1"
    assert plan.plan_code == "PM-100"
    assert plan.name == "Pump PM"
    assert plan.asset_id == "asset-1"
    assert plan.description == "Monthly route"
    assert plan.status.value == "ACTIVE"
    assert plan.plan_type.value == "LUBRICATION"
    assert plan.priority.value == "HIGH"
    assert plan.trigger_mode.value == "CALENDAR"
    assert plan.schedule_policy.value == "FLOATING"
    assert plan.calendar_frequency_unit.value == "MONTHLY"
    assert plan.calendar_frequency_value == 2
    assert plan.generation_horizon_count == 13
    assert plan.generation_lead_value == 0
    assert plan.generation_lead_unit.value == "WEEKS"
    assert plan.sensor_reset_rule == "Reset on completion"
    assert plan.notes == "Coordinate with operations"

    assert plan_task.trigger_scope.value == "TASK_OVERRIDE"
    assert plan_task.trigger_mode_override.value == "CALENDAR"
    assert plan_task.calendar_frequency_unit_override.value == "WEEKLY"
    assert plan_task.calendar_frequency_value_override == 1
    assert plan_task.sequence_no == 3
    assert plan_task.default_assigned_employee_id == "emp-1"
    assert plan_task.default_assigned_team_id == "team-a"
    assert plan_task.estimated_minutes_override == 25
    assert plan_task.notes == "Weekly override for startup period"


def test_maintenance_preventive_instance_and_blackout_dtos_validate_ranges() -> None:
    instance = MaintenancePreventivePlanInstance.create(
        organization_id="  org-1  ",
        plan_id="  plan-1  ",
        due_at="2026-08-01T08:00:00",
        due_counter="120.5",
        status="generated",
        generated_at="2026-07-30T08:00:00",
        generated_work_request_id="  wr-1  ",
        generated_work_order_id="  wo-1  ",
        completed_at="2026-08-01T09:00:00",
        notes="  Generated ahead of shutdown  ",
    )
    blackout = MaintenanceBlackoutWindow.create(
        organization_id="  org-1  ",
        preventive_plan_id="  plan-1  ",
        name="  Shutdown Window  ",
        start_date="2026-12-20",
        end_date="2026-01-05",
        recurrence="annual",
        notes="  Freeze PM generation  ",
    )

    assert instance.organization_id == "org-1"
    assert instance.plan_id == "plan-1"
    assert instance.due_at == datetime(2026, 8, 1, 8, 0, 0, tzinfo=timezone.utc)
    assert instance.due_counter == Decimal("120.5")
    assert instance.status.value == "GENERATED"
    assert instance.generated_work_request_id == "wr-1"
    assert instance.generated_work_order_id == "wo-1"
    assert instance.completed_at == datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)
    assert instance.notes == "Generated ahead of shutdown"

    assert blackout.organization_id == "org-1"
    assert blackout.preventive_plan_id == "plan-1"
    assert blackout.name == "Shutdown Window"
    assert blackout.start_date == date(2026, 12, 20)
    assert blackout.end_date == date(2026, 1, 5)
    assert blackout.recurrence == "ANNUAL"
    assert blackout.notes == "Freeze PM generation"

    with pytest.raises(ValidationError) as exc_instance_range:
        MaintenancePreventivePlanInstance.create(
            organization_id="org-1",
            plan_id="plan-1",
            due_at="2026-08-01T08:00:00+00:00",
            generated_at="2026-08-01T09:00:00+00:00",
            completed_at="2026-08-01T08:30:00+00:00",
        )
    assert (
        exc_instance_range.value.code
        == "MAINTENANCE_PREVENTIVE_PLAN_INSTANCE_COMPLETED_RANGE_INVALID"
    )

    with pytest.raises(ValidationError) as exc_blackout_range:
        MaintenanceBlackoutWindow.create(
            organization_id="org-1",
            preventive_plan_id="plan-1",
            name="Bad Window",
            start_date="2026-08-10",
            end_date="2026-08-01",
            recurrence="none",
        )
    assert exc_blackout_range.value.code == "MAINTENANCE_BLACKOUT_WINDOW_DATE_RANGE_INVALID"


def test_maintenance_reliability_dtos_normalize_fields() -> None:
    sensor = MaintenanceSensor.create(
        organization_id="  org-1  ",
        site_id="  site-1  ",
        sensor_code="  temp-001  ",
        sensor_name="  Main Temperature  ",
        sensor_tag="  tag-1  ",
        sensor_type="  analog  ",
        asset_id="  asset-1  ",
        source_type="  historian  ",
        source_name="  PI  ",
        source_key="  ai-100  ",
        unit="  c  ",
        current_value="-12.5",
        last_read_at="2026-07-25T10:15:00",
        last_quality_state="stale",
        notes="  Needs calibration review  ",
    )
    integration = MaintenanceIntegrationSource.create(
        organization_id="  org-1  ",
        integration_code="  iot-gateway-1  ",
        name="  IoT Gateway 1  ",
        integration_type="  mqtt_bridge  ",
        endpoint_or_path="  mqtt://broker/factory  ",
        authentication_mode="  token  ",
        schedule_expression="  */10 * * * *  ",
        notes="  Poll every 10 minutes  ",
    )
    failure_code = MaintenanceFailureCode.create(
        organization_id="  org-1  ",
        failure_code="  seal-leak  ",
        name="  Seal Leak  ",
        description="  Mechanical seal leakage  ",
        code_type="cause",
        parent_code_id="  parent-1  ",
    )
    mapping = MaintenanceSensorSourceMapping.create(
        organization_id="  org-1  ",
        integration_source_id="  source-1  ",
        sensor_id="  sensor-1  ",
        external_equipment_key="  eq-100  ",
        external_measurement_key="  TEMP_MAIN  ",
        transform_rule="  x * 1.8 + 32  ",
        unit_conversion_rule="  C_TO_F  ",
        notes="  Derived display value  ",
    )

    assert sensor.organization_id == "org-1"
    assert sensor.site_id == "site-1"
    assert sensor.sensor_code == "TEMP-001"
    assert sensor.sensor_name == "Main Temperature"
    assert sensor.sensor_tag == "tag-1"
    assert sensor.sensor_type == "ANALOG"
    assert sensor.source_type == "HISTORIAN"
    assert sensor.source_name == "PI"
    assert sensor.source_key == "ai-100"
    assert sensor.unit == "C"
    assert sensor.current_value == Decimal("-12.5")
    assert sensor.last_read_at == datetime(2026, 7, 25, 10, 15, 0, tzinfo=timezone.utc)
    assert sensor.last_quality_state.value == "STALE"
    assert sensor.notes == "Needs calibration review"

    assert integration.integration_code == "IOT-GATEWAY-1"
    assert integration.name == "IoT Gateway 1"
    assert integration.integration_type == "MQTT_BRIDGE"
    assert integration.endpoint_or_path == "mqtt://broker/factory"
    assert integration.authentication_mode == "TOKEN"
    assert integration.schedule_expression == "*/10 * * * *"
    assert integration.notes == "Poll every 10 minutes"

    assert failure_code.failure_code == "SEAL-LEAK"
    assert failure_code.name == "Seal Leak"
    assert failure_code.description == "Mechanical seal leakage"
    assert failure_code.code_type.value == "CAUSE"
    assert failure_code.parent_code_id == "parent-1"

    assert mapping.integration_source_id == "source-1"
    assert mapping.sensor_id == "sensor-1"
    assert mapping.external_equipment_key == "eq-100"
    assert mapping.external_measurement_key == "TEMP_MAIN"
    assert mapping.transform_rule == "x * 1.8 + 32"
    assert mapping.unit_conversion_rule == "C_TO_F"
    assert mapping.notes == "Derived display value"


def test_maintenance_sensor_reading_dto_normalizes_fields_and_validates_required_values() -> None:
    reading = MaintenanceSensorReading.create(
        organization_id="  org-1  ",
        sensor_id="  sensor-1  ",
        reading_value="-12.5",
        reading_unit="  c  ",
        reading_timestamp="2026-07-25T10:05:00",
        quality_state="error",
        source_name="  PLC  ",
        source_batch_id="  batch-1  ",
        received_at="2026-07-25T10:06:00",
        raw_payload_ref="  payload-1  ",
    )

    assert reading.organization_id == "org-1"
    assert reading.sensor_id == "sensor-1"
    assert reading.reading_value == Decimal("-12.5")
    assert reading.reading_unit == "C"
    assert reading.reading_timestamp == datetime(2026, 7, 25, 10, 5, 0, tzinfo=timezone.utc)
    assert reading.quality_state.value == "ERROR"
    assert reading.source_name == "PLC"
    assert reading.source_batch_id == "batch-1"
    assert reading.received_at == datetime(2026, 7, 25, 10, 6, 0, tzinfo=timezone.utc)
    assert reading.raw_payload_ref == "payload-1"

    reading.version = "2"
    assert reading.version == 2

    with pytest.raises(ValidationError) as exc_unit:
        MaintenanceSensorReading.create(
            organization_id="org-1",
            sensor_id="sensor-1",
            reading_value="1.2",
            reading_unit="",
        )
    assert exc_unit.value.code == "MAINTENANCE_SENSOR_READING_UNIT_REQUIRED"

    with pytest.raises(ValidationError) as exc_value:
        MaintenanceSensorReading.create(
            organization_id="org-1",
            sensor_id="sensor-1",
            reading_value=None,
            reading_unit="C",
        )
    assert exc_value.value.code == "MAINTENANCE_SENSOR_READING_VALUE_REQUIRED"


def test_maintenance_reliability_dtos_validate_chronology() -> None:
    downtime = MaintenanceDowntimeEvent.create(
        organization_id="org-1",
        work_order_id="wo-1",
        started_at="2026-07-25T08:00:00+00:00",
        ended_at="2026-07-25T09:15:00+00:00",
        duration_minutes="75",
        downtime_type="unplanned",
        reason_code="seal-leak",
        impact_notes="Production stopped",
    )
    exception = MaintenanceSensorException.create(
        organization_id="org-1",
        sensor_id="sensor-1",
        exception_type="missing_feed",
        message="Feed missing",
        source_batch_id="batch-1",
        detected_at="2026-07-25T10:00:00+00:00",
        notes="Check gateway",
    )

    assert downtime.work_order_id == "wo-1"
    assert downtime.downtime_type == "UNPLANNED"
    assert downtime.reason_code == "SEAL-LEAK"
    assert downtime.duration_minutes == 75
    assert downtime.impact_notes == "Production stopped"

    assert exception.sensor_id == "sensor-1"
    assert exception.exception_type.value == "MISSING_FEED"
    assert exception.status.value == "OPEN"
    assert exception.source_batch_id == "batch-1"
    assert exception.notes == "Check gateway"

    with pytest.raises(ValidationError) as exc_downtime:
        MaintenanceDowntimeEvent.create(
            organization_id="org-1",
            work_order_id="wo-1",
            started_at="2026-07-25T09:15:00+00:00",
            ended_at="2026-07-25T08:00:00+00:00",
            duration_minutes="75",
            downtime_type="unplanned",
        )
    assert exc_downtime.value.code == "MAINTENANCE_DOWNTIME_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_sensor_updated:
        sensor = MaintenanceSensor.create(
            organization_id="org-1",
            site_id="site-1",
            sensor_code="TEMP-200",
            sensor_name="Temp 200",
            asset_id="asset-1",
        )
        sensor.updated_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assert exc_sensor_updated.value.code == "MAINTENANCE_SENSOR_UPDATED_RANGE_INVALID"

    with pytest.raises(ValidationError) as exc_exception_range:
        exception.acknowledged_at = datetime(2026, 7, 25, 9, 59, 0, tzinfo=timezone.utc)
    assert exc_exception_range.value.code == "MAINTENANCE_SENSOR_EXCEPTION_ACKNOWLEDGED_RANGE_INVALID"
