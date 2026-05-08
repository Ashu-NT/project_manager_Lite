from __future__ import annotations

from PySide6.QtWidgets import QDialog

from ui.modules.maintenance_management.requests.tab import MaintenanceRequestsTab


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


def test_maintenance_requests_tab_supports_guided_request_intake(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site = services["site_service"].create_site(site_code="REQ-UI", name="Request UI Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="req-area",
        name="Request Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="req-asset",
        name="Request Asset",
    )

    class FakeCreateDialog:
        def __init__(self, *args, **kwargs):
            self._site_id = site.id
            self._asset_id = asset.id
            self._location_id = location.id

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def site_id(self):
            return self._site_id

        @property
        def request_code(self):
            return "wr-flow-new"

        @property
        def source_type(self):
            return "MANUAL"

        @property
        def request_type(self):
            return "inspection"

        @property
        def asset_id(self):
            return self._asset_id

        @property
        def system_id(self):
            return None

        @property
        def location_id(self):
            return self._location_id

        @property
        def title(self):
            return "Guided intake request"

        @property
        def description(self):
            return "Created from the maintenance request queue."

        @property
        def priority(self):
            return "MEDIUM"

        @property
        def failure_symptom_code(self):
            return ""

        @property
        def safety_risk_level(self):
            return "LOW"

        @property
        def production_impact_level(self):
            return "MEDIUM"

        @property
        def notes(self):
            return "Created through the guided intake flow."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.requests.tab.MaintenanceRequestEditDialog",
        FakeCreateDialog,
    )

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

    tab.btn_new_request.click()
    qapp.processEvents()

    created = services["maintenance_work_request_service"].find_work_request_by_code("WR-FLOW-NEW")
    assert created is not None
    row = _find_row_by_contains(tab.request_table, 0, "WR-FLOW-NEW")
    assert row >= 0


def test_maintenance_requests_tab_supports_request_to_work_order_conversion(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site = services["site_service"].create_site(site_code="REQ-CONV", name="Request Conversion Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="conv-area",
        name="Conversion Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="conv-asset",
        name="Conversion Asset",
    )
    request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-conv-1",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        title="Convert this request",
        priority="high",
    )

    class FakeConvertDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def work_order_code(self):
            return "wo-conv-1"

        @property
        def work_order_type(self):
            return "CORRECTIVE"

        @property
        def title(self):
            return ""

        @property
        def description(self):
            return ""

        @property
        def assigned_team_id(self):
            return "TEAM-CONV"

        @property
        def requires_shutdown(self):
            return False

        @property
        def permit_required(self):
            return False

        @property
        def approval_required(self):
            return False

        @property
        def notes(self):
            return "Converted from the requests queue."

    monkeypatch.setattr(
        "ui.modules.maintenance_management.requests.tab.MaintenanceRequestConvertDialog",
        FakeConvertDialog,
    )

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
    row = _find_row_by_contains(tab.request_table, 0, "WR-CONV-1")
    assert row >= 0
    tab.request_table.selectRow(row)
    qapp.processEvents()

    assert tab.btn_convert_request.isEnabled()
    tab.btn_convert_request.click()
    qapp.processEvents()

    work_order = services["maintenance_work_order_service"].find_work_order_by_code("WO-CONV-1")
    refreshed_request = services["maintenance_work_request_service"].get_work_request(request.id)
    assert work_order is not None
    assert work_order.source_id == request.id
    assert refreshed_request.status.value == "CONVERTED"
    assert not tab.btn_convert_request.isEnabled()
