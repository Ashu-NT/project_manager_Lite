from __future__ import annotations

from PySide6.QtWidgets import QDialog

from ui.modules.maintenance_management.task_templates.detail_dialog import MaintenanceTaskTemplateDetailDialog
from ui.modules.maintenance_management.task_templates.tab import MaintenanceTaskTemplatesTab


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


def _create_task_template_context(services):
    template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="pm-seal-check",
        name="Seal Inspection Route",
        maintenance_type="preventive",
        revision_no=2,
        template_status="active",
        estimated_minutes=45,
        required_skill="Mechanical",
        requires_shutdown=True,
    )
    step = services["maintenance_task_step_template_service"].create_step_template(
        task_template_id=template.id,
        step_number=1,
        instruction="Inspect the seal housing and confirm visible wear state.",
        expected_result="Seal condition verified.",
        requires_confirmation=True,
        sort_order=1,
    )
    return template, step


def test_task_templates_tab_supports_create_edit_toggle_and_detail(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    template, _step = _create_task_template_context(services)

    tab = MaintenanceTaskTemplatesTab(
        task_template_service=services["maintenance_task_template_service"],
        task_step_template_service=services["maintenance_task_step_template_service"],
        platform_runtime_application_service=services["platform_runtime_application_service"],
        user_session=services["user_session"],
    )

    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.table.rowCount() >= 1
    assert "Open Detail" in tab.selection_summary.text()
    row = _find_row_by_contains(tab.table, 0, "PM-SEAL-CHECK")
    assert row >= 0

    class FakeCreateDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def task_template_code(self):
            return "lube-route"

        @property
        def name(self):
            return "Lubrication Route"

        @property
        def description(self):
            return "Reusable lubrication route template."

        @property
        def maintenance_type(self):
            return "preventive"

        @property
        def revision_no(self):
            return 1

        @property
        def template_status(self):
            return "ACTIVE"

        @property
        def estimated_minutes(self):
            return 30

        @property
        def required_skill(self):
            return "Lube Tech"

        @property
        def requires_shutdown(self):
            return False

        @property
        def requires_permit(self):
            return True

        @property
        def is_active(self):
            return True

        @property
        def notes(self):
            return "Created from task template library UI."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.task_templates.tab.MaintenanceTaskTemplateEditDialog",
        FakeCreateDialog,
    )
    tab.btn_new_template.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "LUBE-ROUTE")
    assert created_row >= 0

    tab.table.selectRow(created_row)
    qapp.processEvents()

    class FakeEditDialog:
        def __init__(self, *args, **kwargs):
            self._task_template = kwargs["task_template"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def task_template_code(self):
            return self._task_template.task_template_code

        @property
        def name(self):
            return "Lubrication Route Updated"

        @property
        def description(self):
            return "Updated from the task template library."

        @property
        def maintenance_type(self):
            return "inspection"

        @property
        def revision_no(self):
            return self._task_template.revision_no + 1

        @property
        def template_status(self):
            return self._task_template.template_status.value

        @property
        def estimated_minutes(self):
            return 35

        @property
        def required_skill(self):
            return "Inspector"

        @property
        def requires_shutdown(self):
            return self._task_template.requires_shutdown

        @property
        def requires_permit(self):
            return self._task_template.requires_permit

        @property
        def is_active(self):
            return self._task_template.is_active

        @property
        def notes(self):
            return self._task_template.notes

    monkeypatch.setattr(
        "ui.modules.maintenance_management.task_templates.tab.MaintenanceTaskTemplateEditDialog",
        FakeEditDialog,
    )
    tab.btn_edit_template.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "LUBE-ROUTE")
    assert "Lubrication Route Updated" in tab.table.item(created_row, 1).text()

    tab.table.selectRow(created_row)
    qapp.processEvents()
    tab.btn_toggle_active.click()
    qapp.processEvents()
    assert _find_row_by_contains(tab.table, 0, "LUBE-ROUTE") == -1
    tab.active_combo.setCurrentIndex(2)
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "LUBE-ROUTE")
    assert tab.table.item(created_row, 7).text() == "No"

    original_row = _find_row_by_contains(tab.table, 0, template.task_template_code)
    tab.table.selectRow(original_row)
    qapp.processEvents()
    tab.btn_open_detail.click()
    qapp.processEvents()
    dialog = tab._detail_dialog
    assert dialog is not None
    assert dialog.context_badge.text() == "Template: PM-SEAL-CHECK"
    assert dialog.step_table.rowCount() >= 1


def test_task_template_detail_dialog_supports_step_create_edit_and_toggle(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    template, _step = _create_task_template_context(services)

    dialog = MaintenanceTaskTemplateDetailDialog(
        task_template_service=services["maintenance_task_template_service"],
        task_step_template_service=services["maintenance_task_step_template_service"],
        can_manage=True,
    )
    dialog.load_task_template(template.id)
    assert dialog.step_table.rowCount() == 1

    class FakeCreateStepDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def step_number(self):
            return 2

        @property
        def sort_order(self):
            return 2

        @property
        def instruction(self):
            return "Record lubrication condition and capture follow-up hint."

        @property
        def expected_result(self):
            return "Lubrication condition logged."

        @property
        def hint_level(self):
            return "HIGH"

        @property
        def hint_text(self):
            return "Escalate abnormal grease contamination."

        @property
        def requires_confirmation(self):
            return True

        @property
        def requires_measurement(self):
            return False

        @property
        def requires_photo(self):
            return True

        @property
        def measurement_unit(self):
            return ""

        @property
        def notes(self):
            return "Created in detail popup."

        @property
        def is_active(self):
            return True

    monkeypatch.setattr(
        "ui.modules.maintenance_management.task_templates.detail_dialog.MaintenanceTaskStepTemplateEditDialog",
        FakeCreateStepDialog,
    )
    dialog.btn_new_step.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.step_table, 0, "2")
    assert added_row >= 0

    dialog.step_table.selectRow(added_row)
    qapp.processEvents()

    class FakeEditStepDialog:
        def __init__(self, *args, **kwargs):
            self._step = kwargs["step_template"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def step_number(self):
            return self._step.step_number

        @property
        def sort_order(self):
            return self._step.sort_order

        @property
        def instruction(self):
            return "Record lubrication condition and updated escalation notes."

        @property
        def expected_result(self):
            return self._step.expected_result

        @property
        def hint_level(self):
            return self._step.hint_level

        @property
        def hint_text(self):
            return "Updated hint"

        @property
        def requires_confirmation(self):
            return self._step.requires_confirmation

        @property
        def requires_measurement(self):
            return self._step.requires_measurement

        @property
        def requires_photo(self):
            return self._step.requires_photo

        @property
        def measurement_unit(self):
            return self._step.measurement_unit

        @property
        def notes(self):
            return self._step.notes

        @property
        def is_active(self):
            return self._step.is_active

    monkeypatch.setattr(
        "ui.modules.maintenance_management.task_templates.detail_dialog.MaintenanceTaskStepTemplateEditDialog",
        FakeEditStepDialog,
    )
    dialog.btn_edit_step.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.step_table, 0, "2")
    assert "updated escalation notes" in dialog.step_table.item(added_row, 1).text().lower()

    dialog.step_table.selectRow(added_row)
    qapp.processEvents()
    dialog.btn_toggle_step.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.step_table, 0, "2")
    assert dialog.step_table.item(added_row, 4).text() == "No"
