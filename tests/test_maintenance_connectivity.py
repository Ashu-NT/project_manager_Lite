from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ui.modules.maintenance_management.preventive.tab import MaintenancePreventivePlansTab


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


def test_preventive_plans_tab_generates_due_work_into_operational_queue(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site = services["site_service"].create_site(site_code="MNT-CONN", name="Connectivity Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="conn-area",
        name="Connectivity Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="conn-asset",
        name="Connectivity Asset",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="conn-task",
        name="Connectivity PM Task",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=25,
    )
    due_plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="conn-plan",
        name="Connectivity Due Plan",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="calendar",
        calendar_frequency_unit="weekly",
        calendar_frequency_value=1,
        next_due_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        auto_generate_work_order=True,
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=due_plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

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
    site_index = tab.site_combo.findData(site.id)
    assert site_index >= 0
    tab.site_combo.setCurrentIndex(site_index)
    qapp.processEvents()
    row = _find_row_by_contains(tab.plan_table, 0, "CONN-PLAN")
    assert row >= 0
    tab.plan_table.selectRow(row)
    qapp.processEvents()

    assert tab.btn_generate_due_work.isEnabled()
    tab.btn_generate_due_work.click()
    qapp.processEvents()

    generated_orders = [
        row
        for row in services["maintenance_work_order_service"].list_work_orders(site_id=site.id, is_preventive=True)
        if row.source_type == "PREVENTIVE_PLAN" and row.source_id == due_plan.id
    ]
    assert len(generated_orders) == 1
