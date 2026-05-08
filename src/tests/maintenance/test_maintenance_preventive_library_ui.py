from __future__ import annotations

from PySide6.QtWidgets import QDialog

from ui.modules.maintenance_management.preventive_library.edit_dialogs import (
    MaintenancePreventivePlanEditDialog,
)
from ui.modules.maintenance_management.preventive_library.detail_dialog import (
    MaintenancePreventivePlanLibraryDetailDialog,
)
from ui.modules.maintenance_management.preventive_library.tab import MaintenancePreventivePlanLibraryTab


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


def _create_preventive_library_context(services):
    site = services["site_service"].create_site(
        site_code="MNT-PP",
        name="Preventive Library Site",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="area-pp",
        name="Preventive Area",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="sys-pp",
        name="Preventive System",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="pump-pp",
        name="Preventive Pump",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        asset_id=asset.id,
        system_id=system.id,
        sensor_code="run-hours-pp",
        sensor_name="Run Hours",
        sensor_type="running_hours",
        source_type="manual",
        unit="H",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="pm-check-pp",
        name="Preventive inspection task",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=40,
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-lib-base",
        name="Base Preventive Library Plan",
        asset_id=asset.id,
        plan_type="preventive",
        priority="high",
        trigger_mode="calendar",
        calendar_frequency_unit="weekly",
        calendar_frequency_value=1,
        auto_generate_work_order=True,
        status="active",
    )
    plan_task = services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
        estimated_minutes_override=45,
    )
    return site, location, system, asset, sensor, task_template, plan, plan_task


def test_preventive_plan_library_tab_supports_create_edit_toggle_and_detail(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site, _location, _system, asset, sensor, _task_template, plan, _plan_task = _create_preventive_library_context(services)

    tab = MaintenancePreventivePlanLibraryTab(
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_plan_task_service=services["maintenance_preventive_plan_task_service"],
        site_service=services["site_service"],
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
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

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.table.rowCount() >= 1
    assert "Open Detail" in tab.selection_summary.text()

    class FakeCreateDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def site_id(self):
            return site.id

        @property
        def plan_code(self):
            return "pm-lib-next"

        @property
        def name(self):
            return "New Preventive Library Plan"

        @property
        def asset_id(self):
            return asset.id

        @property
        def component_id(self):
            return None

        @property
        def system_id(self):
            return ""

        @property
        def description(self):
            return "Created from preventive library UI."

        @property
        def status(self):
            return "ACTIVE"

        @property
        def plan_type(self):
            return "INSPECTION"

        @property
        def priority(self):
            return "MEDIUM"

        @property
        def trigger_mode(self):
            return "SENSOR"

        @property
        def calendar_frequency_unit(self):
            return None

        @property
        def calendar_frequency_value(self):
            return None

        @property
        def sensor_id(self):
            return sensor.id

        @property
        def sensor_threshold(self):
            return "1200"

        @property
        def sensor_direction(self):
            return "GREATER_OR_EQUAL"

        @property
        def sensor_reset_rule(self):
            return "manual reset"

        @property
        def requires_shutdown(self):
            return True

        @property
        def approval_required(self):
            return False

        @property
        def auto_generate_work_order(self):
            return False

        @property
        def is_active(self):
            return True

        @property
        def notes(self):
            return "Created in maintenance libraries."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.preventive_library.tab.MaintenancePreventivePlanEditDialog",
        FakeCreateDialog,
    )
    tab.btn_new_plan.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "PM-LIB-NEXT")
    assert created_row >= 0

    tab.table.selectRow(created_row)
    qapp.processEvents()

    class FakeEditDialog:
        def __init__(self, *args, **kwargs):
            self._plan = kwargs["preventive_plan"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def site_id(self):
            return self._plan.site_id

        @property
        def plan_code(self):
            return self._plan.plan_code

        @property
        def name(self):
            return "New Preventive Library Plan Updated"

        @property
        def asset_id(self):
            return self._plan.asset_id

        @property
        def component_id(self):
            return self._plan.component_id or ""

        @property
        def system_id(self):
            return self._plan.system_id or ""

        @property
        def description(self):
            return "Updated from preventive library."

        @property
        def status(self):
            return self._plan.status.value

        @property
        def plan_type(self):
            return self._plan.plan_type.value

        @property
        def priority(self):
            return self._plan.priority.value

        @property
        def trigger_mode(self):
            return self._plan.trigger_mode.value

        @property
        def calendar_frequency_unit(self):
            return None

        @property
        def calendar_frequency_value(self):
            return None

        @property
        def sensor_id(self):
            return self._plan.sensor_id

        @property
        def sensor_threshold(self):
            return "1400"

        @property
        def sensor_direction(self):
            return self._plan.sensor_direction.value

        @property
        def sensor_reset_rule(self):
            return self._plan.sensor_reset_rule

        @property
        def requires_shutdown(self):
            return self._plan.requires_shutdown

        @property
        def approval_required(self):
            return True

        @property
        def auto_generate_work_order(self):
            return True

        @property
        def is_active(self):
            return self._plan.is_active

        @property
        def notes(self):
            return self._plan.notes

    monkeypatch.setattr(
        "ui.modules.maintenance_management.preventive_library.tab.MaintenancePreventivePlanEditDialog",
        FakeEditDialog,
    )
    tab.btn_edit_plan.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "PM-LIB-NEXT")
    assert "Updated" in tab.table.item(created_row, 1).text()

    tab.table.selectRow(created_row)
    qapp.processEvents()
    tab.btn_toggle_active.click()
    qapp.processEvents()
    assert _find_row_by_contains(tab.table, 0, "PM-LIB-NEXT") == -1
    tab.active_combo.setCurrentIndex(2)
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "PM-LIB-NEXT")
    assert tab.table.item(created_row, 6).text() == "No"

    base_row = _find_row_by_contains(tab.table, 0, plan.plan_code)
    tab.table.selectRow(base_row)
    qapp.processEvents()
    tab.btn_open_detail.click()
    qapp.processEvents()
    dialog = tab._detail_dialog
    assert dialog is not None
    assert dialog.context_badge.text() == "Plan: PM-LIB-BASE"
    assert dialog.task_table.rowCount() >= 1


def test_preventive_plan_library_detail_supports_plan_task_create_and_edit(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site, _location, system, asset, sensor, task_template, plan, _plan_task = _create_preventive_library_context(services)

    dialog = MaintenancePreventivePlanLibraryDetailDialog(
        preventive_plan_service=services["maintenance_preventive_plan_service"],
        preventive_plan_task_service=services["maintenance_preventive_plan_task_service"],
        site_labels={site.id: site.name},
        asset_labels={asset.id: f"{asset.asset_code} - {asset.name}"},
        component_labels={},
        system_labels={system.id: f"{system.system_code} - {system.name}"},
        sensor_labels={sensor.id: f"{sensor.sensor_code} - {sensor.sensor_name}"},
        task_template_labels={task_template.id: f"{task_template.task_template_code} - {task_template.name}"},
        task_template_options=[(f"{task_template.task_template_code} - {task_template.name}", task_template.id)],
        can_manage=True,
    )
    dialog.load_plan(plan.id)
    assert dialog.task_table.rowCount() == 1

    class FakeCreateTaskDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def task_template_id(self):
            return task_template.id

        @property
        def sequence_no(self):
            return 2

        @property
        def trigger_scope(self):
            return "INHERIT_PLAN"

        @property
        def trigger_mode_override(self):
            return None

        @property
        def calendar_frequency_unit_override(self):
            return None

        @property
        def calendar_frequency_value_override(self):
            return None

        @property
        def sensor_id_override(self):
            return None

        @property
        def sensor_threshold_override(self):
            return None

        @property
        def sensor_direction_override(self):
            return None

        @property
        def is_mandatory(self):
            return True

        @property
        def default_assigned_team_id(self):
            return "MECH-A"

        @property
        def estimated_minutes_override(self):
            return 30

        @property
        def notes(self):
            return "Created from preventive detail."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.preventive_library.detail_dialog.MaintenancePreventivePlanTaskEditDialog",
        FakeCreateTaskDialog,
    )
    dialog.btn_new_plan_task.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.task_table, 0, "2")
    assert added_row >= 0

    dialog.task_table.selectRow(added_row)
    qapp.processEvents()

    class FakeEditTaskDialog:
        def __init__(self, *args, **kwargs):
            self._row = kwargs["plan_task"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def task_template_id(self):
            return self._row.task_template_id

        @property
        def sequence_no(self):
            return self._row.sequence_no

        @property
        def trigger_scope(self):
            return self._row.trigger_scope.value

        @property
        def trigger_mode_override(self):
            return None

        @property
        def calendar_frequency_unit_override(self):
            return None

        @property
        def calendar_frequency_value_override(self):
            return None

        @property
        def sensor_id_override(self):
            return None

        @property
        def sensor_threshold_override(self):
            return None

        @property
        def sensor_direction_override(self):
            return None

        @property
        def is_mandatory(self):
            return False

        @property
        def default_assigned_team_id(self):
            return self._row.default_assigned_team_id or ""

        @property
        def estimated_minutes_override(self):
            return 25

        @property
        def notes(self):
            return "Updated from preventive detail."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.preventive_library.detail_dialog.MaintenancePreventivePlanTaskEditDialog",
        FakeEditTaskDialog,
    )
    dialog.btn_edit_plan_task.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.task_table, 0, "2")
    assert dialog.task_table.item(added_row, 4).text() == "No"
    assert dialog.task_table.item(added_row, 5).text() == "25"


def test_preventive_plan_edit_dialog_loads_generation_lead_settings(qapp, services):
    site, _location, _system, asset, _sensor, _task_template, plan, _plan_task = _create_preventive_library_context(services)
    services["maintenance_preventive_plan_service"].update_preventive_plan(
        plan.id,
        generation_lead_value=14,
        generation_lead_unit="weeks",
        expected_version=plan.version,
    )
    refreshed = services["maintenance_preventive_plan_service"].get_preventive_plan(plan.id)

    dialog = MaintenancePreventivePlanEditDialog(
        sites=services["site_service"].list_sites(active_only=None),
        assets=services["maintenance_asset_service"].list_assets(active_only=None),
        components=services["maintenance_asset_component_service"].list_components(active_only=None),
        systems=services["maintenance_system_service"].list_systems(active_only=None),
        sensors=services["maintenance_sensor_service"].list_sensors(active_only=None),
        preventive_plan=refreshed,
    )

    assert dialog.site_id == site.id
    assert dialog.asset_id == asset.id
    assert dialog.generation_lead_value == 14
    assert dialog.generation_lead_unit == "WEEKS"
