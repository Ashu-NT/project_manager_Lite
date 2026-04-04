from __future__ import annotations

from PySide6.QtWidgets import QDialog

from ui.modules.maintenance_management.asset_library.detail_dialog import MaintenanceAssetLibraryDetailDialog
from ui.modules.maintenance_management.asset_library.tab import MaintenanceAssetLibraryTab


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


def _create_asset_library_context(services):
    site = services["site_service"].create_site(
        site_code="MNT-LIB",
        name="Maintenance Library Site",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="area-lib",
        name="Library Area",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="sys-lib",
        name="Library System",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="pump-lib",
        name="Pump Library Asset",
        asset_category="ROTATING",
        asset_type="PUMP",
        maintenance_strategy="PM",
        service_level="A",
    )
    component = services["maintenance_asset_component_service"].create_component(
        asset_id=asset.id,
        component_code="seal-lib",
        name="Seal Assembly",
        component_type="SEAL",
        is_critical_component=True,
    )
    return site, location, system, asset, component


def test_asset_library_tab_supports_create_edit_toggle_and_detail(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    site, _location, _system, asset, _component = _create_asset_library_context(services)

    tab = MaintenanceAssetLibraryTab(
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_service=services["site_service"],
        location_service=services["maintenance_location_service"],
        system_service=services["maintenance_system_service"],
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
        def asset_code(self):
            return "motor-lib"

        @property
        def name(self):
            return "Motor Library Asset"

        @property
        def site_id(self):
            return site.id

        @property
        def location_id(self):
            return services["maintenance_location_service"].list_locations(site_id=site.id, active_only=None)[0].id

        @property
        def system_id(self):
            return services["maintenance_system_service"].list_systems(site_id=site.id, active_only=None)[0].id

        @property
        def parent_asset_id(self):
            return asset.id

        @property
        def asset_type(self):
            return "MOTOR"

        @property
        def asset_category(self):
            return "DRIVE"

        @property
        def criticality(self):
            return "HIGH"

        @property
        def status(self):
            return "ACTIVE"

        @property
        def model_number(self):
            return "MX-200"

        @property
        def serial_number(self):
            return "SN-200"

        @property
        def barcode(self):
            return "BC-200"

        @property
        def maintenance_strategy(self):
            return "CBM"

        @property
        def service_level(self):
            return "B"

        @property
        def description(self):
            return "Created from asset library UI."

        @property
        def notes(self):
            return "Asset-library create flow."

        @property
        def requires_shutdown_for_major_work(self):
            return True

        @property
        def is_active(self):
            return True

    monkeypatch.setattr(
        "ui.modules.maintenance_management.asset_library.tab.MaintenanceAssetEditDialog",
        FakeCreateDialog,
    )
    tab.btn_new_asset.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "MOTOR-LIB")
    assert created_row >= 0

    tab.table.selectRow(created_row)
    qapp.processEvents()

    class FakeEditDialog:
        def __init__(self, *args, **kwargs):
            self._asset = kwargs["asset"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def asset_code(self):
            return self._asset.asset_code

        @property
        def name(self):
            return "Motor Library Asset Updated"

        @property
        def site_id(self):
            return self._asset.site_id

        @property
        def location_id(self):
            return self._asset.location_id

        @property
        def system_id(self):
            return self._asset.system_id

        @property
        def parent_asset_id(self):
            return self._asset.parent_asset_id

        @property
        def asset_type(self):
            return "DRIVE"

        @property
        def asset_category(self):
            return self._asset.asset_category

        @property
        def criticality(self):
            return self._asset.criticality.value

        @property
        def status(self):
            return self._asset.status.value

        @property
        def model_number(self):
            return self._asset.model_number

        @property
        def serial_number(self):
            return self._asset.serial_number

        @property
        def barcode(self):
            return self._asset.barcode

        @property
        def maintenance_strategy(self):
            return "Predictive"

        @property
        def service_level(self):
            return self._asset.service_level

        @property
        def description(self):
            return "Updated through asset library."

        @property
        def notes(self):
            return self._asset.notes

        @property
        def requires_shutdown_for_major_work(self):
            return self._asset.requires_shutdown_for_major_work

        @property
        def is_active(self):
            return self._asset.is_active

    monkeypatch.setattr(
        "ui.modules.maintenance_management.asset_library.tab.MaintenanceAssetEditDialog",
        FakeEditDialog,
    )
    tab.btn_edit_asset.click()
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "MOTOR-LIB")
    assert "Motor Library Asset Updated" in tab.table.item(created_row, 1).text()

    tab.table.selectRow(created_row)
    qapp.processEvents()
    tab.btn_toggle_active.click()
    qapp.processEvents()
    assert _find_row_by_contains(tab.table, 0, "MOTOR-LIB") == -1
    tab.status_combo.setCurrentIndex(2)
    qapp.processEvents()
    created_row = _find_row_by_contains(tab.table, 0, "MOTOR-LIB")
    assert tab.table.item(created_row, 7).text() == "No"

    original_row = _find_row_by_contains(tab.table, 0, "PUMP-LIB")
    tab.table.selectRow(original_row)
    qapp.processEvents()
    tab.btn_open_detail.click()
    qapp.processEvents()
    dialog = tab._detail_dialog
    assert dialog is not None
    assert dialog.context_badge.text() == "Asset: PUMP-LIB"
    assert dialog.component_table.rowCount() >= 1


def test_asset_library_detail_supports_component_create_edit_and_toggle(qapp, services, monkeypatch):
    _mute_message_boxes(monkeypatch)
    _site, _location, _system, asset, _component = _create_asset_library_context(services)

    dialog = MaintenanceAssetLibraryDetailDialog(
        asset_service=services["maintenance_asset_service"],
        component_service=services["maintenance_asset_component_service"],
        site_labels={asset.site_id: "Maintenance Library Site"},
        location_labels={asset.location_id: "Library Area"},
        system_labels={asset.system_id: "Library System"},
        can_manage=True,
    )
    dialog.load_asset(asset.id)
    assert dialog.component_table.rowCount() == 1

    class FakeCreateComponentDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def component_code(self):
            return "bearing-lib"

        @property
        def name(self):
            return "Bearing Set"

        @property
        def parent_component_id(self):
            return None

        @property
        def component_type(self):
            return "BEARING"

        @property
        def status(self):
            return "ACTIVE"

        @property
        def manufacturer_part_number(self):
            return "BR-01"

        @property
        def supplier_part_number(self):
            return "SUP-BR-01"

        @property
        def model_number(self):
            return "BRG-500"

        @property
        def serial_number(self):
            return "BRG-SN-01"

        @property
        def expected_life_hours(self):
            return 12000

        @property
        def expected_life_cycles(self):
            return 500

        @property
        def description(self):
            return "Created in asset-library detail."

        @property
        def notes(self):
            return "New bearing component."

        @property
        def is_critical_component(self):
            return True

        @property
        def is_active(self):
            return True

    monkeypatch.setattr(
        "ui.modules.maintenance_management.asset_library.detail_dialog.MaintenanceAssetComponentEditDialog",
        FakeCreateComponentDialog,
    )
    dialog.btn_new_component.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.component_table, 0, "BEARING-LIB")
    assert added_row >= 0

    dialog.component_table.selectRow(added_row)
    qapp.processEvents()

    class FakeEditComponentDialog:
        def __init__(self, *args, **kwargs):
            self._component = kwargs["component"]

        def exec(self):
            return QDialog.DialogCode.Accepted

        @property
        def component_code(self):
            return self._component.component_code

        @property
        def name(self):
            return "Bearing Set Updated"

        @property
        def parent_component_id(self):
            return self._component.parent_component_id

        @property
        def component_type(self):
            return self._component.component_type

        @property
        def status(self):
            return self._component.status.value

        @property
        def manufacturer_part_number(self):
            return self._component.manufacturer_part_number

        @property
        def supplier_part_number(self):
            return self._component.supplier_part_number

        @property
        def model_number(self):
            return self._component.model_number

        @property
        def serial_number(self):
            return self._component.serial_number

        @property
        def expected_life_hours(self):
            return self._component.expected_life_hours

        @property
        def expected_life_cycles(self):
            return self._component.expected_life_cycles

        @property
        def description(self):
            return "Updated component detail."

        @property
        def notes(self):
            return self._component.notes

        @property
        def is_critical_component(self):
            return self._component.is_critical_component

        @property
        def is_active(self):
            return self._component.is_active

    monkeypatch.setattr(
        "ui.modules.maintenance_management.asset_library.detail_dialog.MaintenanceAssetComponentEditDialog",
        FakeEditComponentDialog,
    )
    dialog.btn_edit_component.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.component_table, 0, "BEARING-LIB")
    assert "Bearing Set Updated" in dialog.component_table.item(added_row, 1).text()

    dialog.component_table.selectRow(added_row)
    qapp.processEvents()
    dialog.btn_toggle_component.click()
    qapp.processEvents()
    added_row = _find_row_by_contains(dialog.component_table, 0, "BEARING-LIB")
    assert dialog.component_table.item(added_row, 5).text() == "No"
