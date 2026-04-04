from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from openpyxl import load_workbook

from tests.ui_runtime_helpers import make_settings_store
from ui.modules.maintenance_management import (
    MaintenanceAssetsTab,
    MaintenanceDashboardTab,
    MaintenanceDocumentsTab,
    MaintenancePlannerTab,
    MaintenancePreventivePlansTab,
    MaintenanceReliabilityTab,
    MaintenanceSensorsTab,
    MaintenanceWorkOrdersTab,
)
from ui.platform.shell.main_window import MainWindow


def _child_labels(item) -> list[str]:
    return [item.child(i).text(0) for i in range(item.childCount())]


def _enable_maintenance_module(services) -> None:
    services["module_catalog_service"].set_module_state(
        "maintenance_management",
        licensed=True,
        enabled=True,
        lifecycle_status="active",
    )


def _select_combo_value(combo, value) -> None:
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def _find_row_by_contains(table, column: int, needle: str) -> int:
    for row in range(table.rowCount()):
        item = table.item(row, column)
        if item is not None and needle in item.text():
            return row
    return -1


def _mute_message_boxes(monkeypatch) -> None:
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *args, **kwargs: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *args, **kwargs: None)


def _create_maintenance_context(services):
    site = services["site_service"].create_site(
        site_code="MNT-UI",
        name="Maintenance UI Site",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="area-a",
        name="Area A",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="pump-line",
        name="Pump Line",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="pump-101",
        name="Pump 101",
    )
    services["maintenance_asset_component_service"].create_component(
        asset_id=asset.id,
        component_code="seal-001",
        name="Mechanical Seal",
        component_type="seal",
        is_critical_component=True,
    )
    source = services["maintenance_integration_source_service"].create_source(
        integration_code="iot-ui-1",
        name="IoT Gateway UI",
        integration_type="iot_gateway",
        endpoint_or_path="mqtt://broker/pumps",
        authentication_mode="token",
        schedule_expression="*/10 * * * *",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="run-hours-101",
        sensor_name="Pump 101 Running Hours",
        asset_id=asset.id,
        sensor_type="running_hours",
        source_type="iot_gateway",
        source_name=source.name,
        source_key="pump-101.hours",
        unit="H",
    )
    services["maintenance_sensor_source_mapping_service"].create_mapping(
        integration_source_id=source.id,
        sensor_id=sensor.id,
        external_equipment_key="PUMP-101",
        external_measurement_key="run_hours",
    )
    services["maintenance_sensor_reading_service"].record_reading(
        sensor_id=sensor.id,
        reading_value="1240.5",
        reading_unit="H",
        quality_state="stale",
        source_name=source.name,
        source_batch_id="BATCH-UI-001",
    )
    services["maintenance_integration_source_service"].record_sync_failure(
        source.id,
        error_message="Gateway timeout during maintenance UI refresh.",
        expected_version=source.version,
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="pm-seal-check",
        name="Seal inspection route",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=60,
        required_skill="Mechanical",
    )
    services["maintenance_task_step_template_service"].create_step_template(
        task_template_id=task_template.id,
        step_number=1,
        instruction="Inspect the seal assembly and capture abnormal wear indicators.",
        expected_result="Seal condition confirmed and documented.",
        requires_confirmation=True,
    )
    symptom = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="seal-leak",
        name="Seal Leak",
        code_type="symptom",
    )
    cause = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="misalignment",
        name="Misalignment",
        code_type="cause",
    )
    now = datetime.now(timezone.utc)
    request_open = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-ui-open",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Open seal leak",
        failure_symptom_code=symptom.failure_code,
    )
    request_open = services["maintenance_work_request_service"].update_work_request(
        request_open.id,
        status="TRIAGED",
        expected_version=request_open.version,
    )
    open_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-ui-open",
        work_order_type="corrective",
        source_type="work_request",
        source_id=request_open.id,
    )
    services["maintenance_work_order_service"].update_work_order(
        open_order.id,
        status="planned",
        planned_start=now - timedelta(days=2),
        planned_end=now - timedelta(days=1),
        expected_version=open_order.version,
    )
    open_task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=open_order.id,
        task_name="Inspect seal housing",
        required_skill="Mechanical",
        estimated_minutes=45,
        completion_rule="all_steps_required",
    )
    services["maintenance_work_order_task_step_service"].create_step(
        work_order_task_id=open_task.id,
        instruction="Verify isolation, inspect seal area, and capture readings.",
        expected_result="Seal area inspected and condition confirmed.",
        requires_confirmation=True,
    )
    services["maintenance_work_order_material_requirement_service"].create_requirement(
        work_order_id=open_order.id,
        description="Seal kit",
        required_qty="1",
        required_uom="EA",
        is_stock_item=False,
        notes="Direct-charge seal kit pending release.",
    )

    request_closed = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-ui-closed",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Closed leak history",
        failure_symptom_code=symptom.failure_code,
    )
    closed_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-ui-closed",
        work_order_type="corrective",
        source_type="work_request",
        source_id=request_closed.id,
    )
    request_closed = services["maintenance_work_request_service"].update_work_request(
        request_closed.id,
        status="CONVERTED",
        expected_version=request_closed.version,
    )
    closed_order = services["maintenance_work_order_service"].update_work_order(
        closed_order.id,
        status="planned",
        planned_start=now - timedelta(days=10),
        planned_end=now - timedelta(days=9),
        expected_version=closed_order.version,
    )
    closed_order = services["maintenance_work_order_service"].update_work_order(
        closed_order.id,
        status="released",
        expected_version=closed_order.version,
    )
    closed_order = services["maintenance_work_order_service"].update_work_order(
        closed_order.id,
        status="in_progress",
        expected_version=closed_order.version,
    )
    closed_order = services["maintenance_work_order_service"].update_work_order(
        closed_order.id,
        status="completed",
        failure_code=symptom.failure_code,
        root_cause_code=cause.failure_code,
        downtime_minutes=90,
        expected_version=closed_order.version,
    )
    services["maintenance_downtime_event_service"].create_downtime_event(
        work_order_id=closed_order.id,
        started_at=(now - timedelta(days=10, hours=2)).isoformat(),
        ended_at=(now - timedelta(days=10, hours=1)).isoformat(),
        downtime_type="unplanned",
        reason_code=symptom.failure_code,
        impact_notes="Unplanned production loss.",
    )
    request_repeat = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-ui-repeat",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Repeat leak history",
        failure_symptom_code=symptom.failure_code,
    )
    repeat_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-ui-repeat",
        work_order_type="corrective",
        source_type="work_request",
        source_id=request_repeat.id,
    )
    request_repeat = services["maintenance_work_request_service"].update_work_request(
        request_repeat.id,
        status="CONVERTED",
        expected_version=request_repeat.version,
    )
    repeat_order = services["maintenance_work_order_service"].update_work_order(
        repeat_order.id,
        status="planned",
        planned_start=now - timedelta(days=20),
        planned_end=now - timedelta(days=19),
        expected_version=repeat_order.version,
    )
    repeat_order = services["maintenance_work_order_service"].update_work_order(
        repeat_order.id,
        status="released",
        expected_version=repeat_order.version,
    )
    repeat_order = services["maintenance_work_order_service"].update_work_order(
        repeat_order.id,
        status="in_progress",
        expected_version=repeat_order.version,
    )
    repeat_order = services["maintenance_work_order_service"].update_work_order(
        repeat_order.id,
        status="completed",
        failure_code=symptom.failure_code,
        root_cause_code=cause.failure_code,
        downtime_minutes=45,
        expected_version=repeat_order.version,
    )
    services["maintenance_downtime_event_service"].create_downtime_event(
        work_order_id=repeat_order.id,
        started_at=(now - timedelta(days=20, hours=1)).isoformat(),
        ended_at=(now - timedelta(days=20, minutes=15)).isoformat(),
        downtime_type="unplanned",
        reason_code=symptom.failure_code,
        impact_notes="Repeat leak recurrence.",
    )
    request_deferred = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-ui-deferred",
        source_type="manual",
        request_type="inspection",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Deferred inspection follow-up",
        failure_symptom_code=symptom.failure_code,
    )
    services["maintenance_work_request_service"].update_work_request(
        request_deferred.id,
        status="DEFERRED",
        expected_version=request_deferred.version,
    )
    due_plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-ui-due",
        name="Due seal inspection",
        asset_id=asset.id,
        plan_type="preventive",
        priority="high",
        trigger_mode="calendar",
        calendar_frequency_unit="weekly",
        calendar_frequency_value=1,
        next_due_at=(now - timedelta(days=1)).isoformat(),
        auto_generate_work_order=True,
        status="active",
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=due_plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
        estimated_minutes_override=50,
    )
    due_soon_plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-ui-soon",
        name="Due soon seal review",
        asset_id=asset.id,
        plan_type="inspection",
        priority="medium",
        trigger_mode="calendar",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        next_due_at=(now + timedelta(days=7)).isoformat(),
        status="active",
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=due_soon_plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )
    blocked_plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-ui-blocked",
        name="Blocked hybrid inspection",
        asset_id=asset.id,
        plan_type="condition_based",
        priority="high",
        trigger_mode="hybrid",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        sensor_id=sensor.id,
        sensor_threshold="1200",
        sensor_direction="greater_or_equal",
        next_due_at=(now + timedelta(days=14)).isoformat(),
        status="active",
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=blocked_plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="task_override",
        trigger_mode_override="sensor",
        sensor_id_override=sensor.id,
        sensor_threshold_override="1200",
        sensor_direction_override="greater_or_equal",
    )
    services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-ui-paused",
        name="Paused overhaul library",
        system_id=system.id,
        plan_type="preventive",
        priority="low",
        trigger_mode="calendar",
        calendar_frequency_unit="quarterly",
        calendar_frequency_value=1,
        next_due_at=(now + timedelta(days=45)).isoformat(),
        status="paused",
        is_active=False,
    )
    return site, location, system, asset, symptom


def test_maintenance_assets_tab_lists_assets_and_components(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, asset, _symptom = _create_maintenance_context(services)

    tab = MaintenanceAssetsTab(
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_service=services["site_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    assert tab.btn_filters.text().strip() == "Filters"
    assert tab.filter_panel.isHidden()
    tab.btn_filters.click()
    qapp.processEvents()
    assert not tab.filter_panel.isHidden()
    assert tab.btn_filters.text().strip() == "Hide Filters"
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.asset_table.rowCount() >= 1
    assert "Pump 101" in tab.asset_table.item(0, 0).text()
    assert tab.detail_title.text() == "PUMP-101 - Pump 101"
    assert tab.component_table.rowCount() >= 1
    assert "Mechanical Seal" in tab.component_table.item(0, 0).text()


def test_maintenance_requests_tab_lists_queue_and_linked_orders(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, _asset, _symptom = _create_maintenance_context(services)

    from ui.modules.maintenance_management import MaintenanceRequestsTab

    tab = MaintenanceRequestsTab(
        work_request_service=services["maintenance_work_request_service"],
        work_order_service=services["maintenance_work_order_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.request_table.rowCount() >= 4
    assert tab.total_card._lbl_value.text() == str(tab.request_table.rowCount())
    row = _find_row_by_contains(tab.request_table, 0, "WR-UI-OPEN")
    assert row >= 0
    tab.request_table.selectRow(row)
    qapp.processEvents()
    assert "Open seal leak" in tab.detail_title.text()
    assert tab.linked_orders_table.rowCount() >= 1
    assert "WO-UI-OPEN" in tab.linked_orders_table.item(0, 0).text()


def test_maintenance_work_orders_tab_lists_execution_queue_and_detail(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, _asset, _symptom = _create_maintenance_context(services)

    tab = MaintenanceWorkOrdersTab(
        work_order_service=services["maintenance_work_order_service"],
        work_order_task_service=services["maintenance_work_order_task_service"],
        work_order_task_step_service=services["maintenance_work_order_task_step_service"],
        material_requirement_service=services["maintenance_work_order_material_requirement_service"],
        work_request_service=services["maintenance_work_request_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.work_order_table.rowCount() >= 3
    assert tab.total_card._lbl_value.text() == str(tab.work_order_table.rowCount())
    row = _find_row_by_contains(tab.work_order_table, 0, "WO-UI-OPEN")
    assert row >= 0
    tab.work_order_table.selectRow(row)
    qapp.processEvents()
    assert "Open seal leak" in tab.detail_title.text()
    assert tab.task_table.rowCount() >= 1
    assert "Inspect seal housing" in tab.task_table.item(0, 0).text()
    assert tab.material_table.rowCount() >= 1
    assert "Seal kit" in tab.material_table.item(0, 0).text()


def test_maintenance_documents_tab_lists_linked_documents(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, asset, _symptom = _create_maintenance_context(services)
    document = services["document_service"].create_document(
        document_code="DOC-UI-MNT",
        title="Maintenance SOP",
        document_type="PROCEDURE",
        storage_kind="FILE_PATH",
        storage_uri="C:/docs/maintenance-sop.pdf",
    )
    services["maintenance_document_service"].link_existing_document(
        entity_type="asset",
        entity_id=asset.id,
        document_id=document.id,
        link_role="reference",
    )

    tab = MaintenanceDocumentsTab(
        document_service=services["maintenance_document_service"],
        site_service=services["site_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.document_table.rowCount() >= 1
    row = _find_row_by_contains(tab.document_table, 0, "DOC-UI-MNT")
    assert row >= 0
    tab.document_table.selectRow(row)
    qapp.processEvents()
    assert tab.detail_title.text() == "Maintenance SOP"
    assert "Asset: PUMP-101 - Pump 101" in tab.metadata_labels["linked_record"].text()
    assert tab.metadata_labels["type"].text() == "Procedure"


def test_maintenance_sensors_tab_lists_sensor_register_and_exception_queue(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, asset, _symptom = _create_maintenance_context(services)

    tab = MaintenanceSensorsTab(
        sensor_service=services["maintenance_sensor_service"],
        sensor_reading_service=services["maintenance_sensor_reading_service"],
        sensor_source_mapping_service=services["maintenance_sensor_source_mapping_service"],
        sensor_exception_service=services["maintenance_sensor_exception_service"],
        integration_source_service=services["maintenance_integration_source_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    assert tab.btn_filters.text().strip() == "Filters"
    assert tab.filter_panel.isHidden()
    tab.btn_filters.click()
    qapp.processEvents()
    assert not tab.filter_panel.isHidden()
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()
    _select_combo_value(tab.asset_combo, asset.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.sensor_table.rowCount() >= 1
    assert "RUN-HOURS-101" in tab.sensor_table.item(0, 0).text()
    assert tab.integration_table.rowCount() >= 1
    assert tab.exception_table.rowCount() >= 1
    assert tab.attention_card._lbl_value.text() != "0"
    assert tab.open_exceptions_card._lbl_value.text() != "0"
    assert tab.detail_title.text() == "RUN-HOURS-101 - Pump 101 Running Hours"
    assert tab.reading_table.rowCount() >= 1
    assert tab.mapping_table.rowCount() >= 1


def test_maintenance_planner_tab_surfaces_backlog_material_and_recurring_queues(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, asset, _symptom = _create_maintenance_context(services)

    tab = MaintenancePlannerTab(
        work_request_service=services["maintenance_work_request_service"],
        work_order_service=services["maintenance_work_order_service"],
        material_requirement_service=services["maintenance_work_order_material_requirement_service"],
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_generation_service=services["maintenance_preventive_generation_service"],
        reliability_service=services["maintenance_reliability_service"],
        sensor_exception_service=services["maintenance_sensor_exception_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    assert tab.btn_filters.text().strip() == "Filters"
    assert tab.filter_panel.isHidden()
    tab.btn_filters.click()
    qapp.processEvents()
    assert not tab.filter_panel.isHidden()
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()
    _select_combo_value(tab.asset_combo, asset.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.request_table.rowCount() >= 1
    assert tab.work_order_table.rowCount() >= 1
    assert tab.preventive_table.rowCount() >= 1
    assert tab.material_table.rowCount() >= 1
    assert tab.recurring_table.rowCount() >= 1
    assert tab.backlog_card._lbl_value.text() != "0"
    assert tab.preventive_card._lbl_value.text() != "0"
    assert tab.material_card._lbl_value.text() != "0"
    assert "WO-UI-OPEN" in tab.work_order_table.item(0, 0).text()
    due_row = _find_row_by_contains(tab.preventive_table, 0, "PM-UI-DUE")
    blocked_row = _find_row_by_contains(tab.preventive_table, 0, "PM-UI-BLOCKED")
    assert due_row >= 0
    assert blocked_row >= 0
    assert due_row < blocked_row
    assert tab.preventive_table.item(due_row, 2).text() == "Due"
    assert tab.preventive_table.item(blocked_row, 2).text() == "Blocked"


def test_maintenance_preventive_tab_surfaces_due_blocked_and_inactive_plan_states(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, _asset, _symptom = _create_maintenance_context(services)

    tab = MaintenancePreventivePlansTab(
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_plan_task_service=services["maintenance_preventive_plan_task_service"],
        preventive_generation_service=services["maintenance_preventive_generation_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        system_service=services["maintenance_system_service"],
        sensor_service=services["maintenance_sensor_service"],
        task_template_service=services["maintenance_task_template_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    assert tab.btn_filters.text().strip() == "Filters"
    assert tab.filter_panel.isHidden()
    tab.btn_filters.click()
    qapp.processEvents()
    assert not tab.filter_panel.isHidden()
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.plan_table.rowCount() >= 4
    assert tab.due_now_card._lbl_value.text() != "0"
    assert tab.due_soon_card._lbl_value.text() != "0"
    assert tab.blocked_card._lbl_value.text() != "0"

    row = _find_row_by_contains(tab.plan_table, 0, "PM-UI-DUE")
    assert row >= 0
    tab.plan_table.selectRow(row)
    qapp.processEvents()
    assert "Due seal inspection" in tab.detail_title.text()
    assert "Due state: Due" in tab.detail_summary.text()
    assert tab.task_table.rowCount() >= 1
    assert "PM-SEAL-CHECK" in tab.task_table.item(0, 1).text()

    _select_combo_value(tab.due_state_combo, "BLOCKED")
    qapp.processEvents()
    assert tab.plan_table.rowCount() >= 1
    assert "PM-UI-BLOCKED" in tab.plan_table.item(0, 0).text()


def test_maintenance_dashboard_tab_surfaces_reliability_metrics(qapp, services):
    _enable_maintenance_module(services)
    site, _location, _system, asset, _symptom = _create_maintenance_context(services)

    tab = MaintenanceDashboardTab(
        reliability_service=services["maintenance_reliability_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()
    _select_combo_value(tab.asset_combo, asset.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.window_badge.text() == "90 day window"
    assert tab.root_cause_table.rowCount() >= 1
    assert tab.recurring_table.rowCount() >= 1
    assert "Pump 101" in tab.recurring_table.item(0, 0).text()
    assert "Misalignment" in tab.root_cause_table.item(0, 1).text()


def test_maintenance_reliability_tab_exports_report_packs(qapp, services, tmp_path, monkeypatch):
    _enable_maintenance_module(services)
    _mute_message_boxes(monkeypatch)
    site, _location, _system, asset, symptom = _create_maintenance_context(services)

    tab = MaintenanceReliabilityTab(
        reliability_service=services["maintenance_reliability_service"],
        reporting_service=services["maintenance_reporting_service"],
        failure_code_service=services["maintenance_failure_code_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()
    _select_combo_value(tab.asset_combo, asset.id)
    qapp.processEvents()
    _select_combo_value(tab.failure_code_combo, symptom.failure_code)
    qapp.processEvents()

    backlog_path = tab.export_backlog_excel(tmp_path / "maintenance-ui-backlog.xlsx")
    downtime_path = tab.export_downtime_pdf(tmp_path / "maintenance-ui-downtime.pdf")

    assert tab.export_badge.text() == "Export Enabled"
    assert tab.suggestions_table.rowCount() >= 1
    assert tab.root_cause_table.rowCount() >= 1
    assert tab.recurring_table.rowCount() >= 1
    assert backlog_path is not None
    assert downtime_path is not None
    assert Path(backlog_path).exists()
    assert Path(downtime_path).exists()
    workbook = load_workbook(backlog_path)
    assert {"Summary", "Open Work Orders", "Top Root Causes", "Recurring Failure Patterns"} <= set(workbook.sheetnames)


def test_main_window_exposes_maintenance_workspaces_when_module_is_enabled(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    _enable_maintenance_module(services)
    _create_maintenance_context(services)
    store = make_settings_store(repo_workspace, prefix="maintenance-shell")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Maintenance Dashboard" in labels
    assert "Assets" in labels
    assert "Planner" in labels
    assert "Preventive Plans" in labels
    assert "Sensors" in labels
    assert "Requests" in labels
    assert "Work Orders" in labels
    assert "Documents" in labels
    assert "Reliability" in labels

    maintenance_section = window.shell_navigation.tree.topLevelItem(3)
    assert maintenance_section.text(0) == "Maintenance Management"
    assert _child_labels(maintenance_section) == ["Overview", "Records", "Planning", "Analytics"]
    assert _child_labels(maintenance_section.child(0)) == ["Maintenance Dashboard"]
    assert _child_labels(maintenance_section.child(1)) == ["Assets", "Sensors", "Requests", "Work Orders", "Documents"]
    assert _child_labels(maintenance_section.child(2)) == ["Preventive Plans", "Planner"]
    assert _child_labels(maintenance_section.child(3)) == ["Reliability"]
