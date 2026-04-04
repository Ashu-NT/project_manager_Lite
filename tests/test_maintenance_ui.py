from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from openpyxl import load_workbook

from tests.ui_runtime_helpers import make_settings_store
from ui.modules.maintenance_management import (
    MaintenanceAssetsTab,
    MaintenanceDashboardTab,
    MaintenanceReliabilityTab,
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
    _select_combo_value(tab.site_combo, site.id)
    qapp.processEvents()

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.asset_table.rowCount() >= 1
    assert "Pump 101" in tab.asset_table.item(0, 0).text()
    assert tab.detail_title.text() == "PUMP-101 - Pump 101"
    assert tab.component_table.rowCount() >= 1
    assert "Mechanical Seal" in tab.component_table.item(0, 0).text()


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
    assert "Reliability" in labels

    maintenance_section = window.shell_navigation.tree.topLevelItem(3)
    assert maintenance_section.text(0) == "Maintenance Management"
    assert _child_labels(maintenance_section) == ["Overview", "Records", "Analytics"]
    assert _child_labels(maintenance_section.child(0)) == ["Maintenance Dashboard"]
    assert _child_labels(maintenance_section.child(1)) == ["Assets"]
    assert _child_labels(maintenance_section.child(2)) == ["Reliability"]
