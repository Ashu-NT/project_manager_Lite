from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    run_mutation,
    serialize_assets_workspace_state,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceAssetsWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenanceAssetsWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    siteOptionsChanged = Signal()
    activeFilterOptionsChanged = Signal()
    selectedSiteFilterChanged = Signal()
    selectedActiveFilterChanged = Signal()
    searchTextChanged = Signal()
    locationsChanged = Signal()
    systemsChanged = Signal()
    assetsChanged = Signal()
    componentsChanged = Signal()
    selectedLocationChanged = Signal()
    selectedSystemChanged = Signal()
    selectedAssetChanged = Signal()
    selectedComponentChanged = Signal()
    selectedLocationIdChanged = Signal()
    selectedSystemIdChanged = Signal()
    selectedAssetIdChanged = Signal()
    selectedComponentIdChanged = Signal()
    formSiteOptionsChanged = Signal()
    formLocationOptionsChanged = Signal()
    formParentLocationOptionsChanged = Signal()
    formSystemOptionsChanged = Signal()
    formParentSystemOptionsChanged = Signal()
    formAssetOptionsChanged = Signal()
    formParentAssetOptionsChanged = Signal()
    formComponentOptionsChanged = Signal()
    formParentComponentOptionsChanged = Signal()
    formStatusOptionsChanged = Signal()
    formCriticalityOptionsChanged = Signal()
    formManufacturerOptionsChanged = Signal()
    formSupplierOptionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        assets_workspace_presenter: MaintenanceAssetsWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.assets"
        )
        self._assets_workspace_presenter = (
            assets_workspace_presenter or MaintenanceAssetsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._site_options: list[dict[str, object]] = []
        self._active_filter_options: list[dict[str, object]] = []
        self._selected_site_filter = "all"
        self._selected_active_filter = "all"
        self._search_text = ""
        self._locations: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._systems: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._assets: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._components: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_location: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_system: dict[str, object] = dict(self._selected_location)
        self._selected_asset: dict[str, object] = dict(self._selected_location)
        self._selected_component: dict[str, object] = dict(self._selected_location)
        self._selected_location_id = ""
        self._selected_system_id = ""
        self._selected_asset_id = ""
        self._selected_component_id = ""
        self._form_site_options: list[dict[str, str]] = []
        self._form_location_options: list[dict[str, str]] = []
        self._form_parent_location_options: list[dict[str, str]] = []
        self._form_system_options: list[dict[str, str]] = []
        self._form_parent_system_options: list[dict[str, str]] = []
        self._form_asset_options: list[dict[str, str]] = []
        self._form_parent_asset_options: list[dict[str, str]] = []
        self._form_component_options: list[dict[str, str]] = []
        self._form_parent_component_options: list[dict[str, str]] = []
        self._form_status_options: list[dict[str, str]] = []
        self._form_criticality_options: list[dict[str, str]] = []
        self._form_manufacturer_options: list[dict[str, str]] = []
        self._form_supplier_options: list[dict[str, str]] = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=siteOptionsChanged)
    def siteOptions(self) -> list[dict[str, object]]:
        return self._site_options

    @Property("QVariantList", notify=activeFilterOptionsChanged)
    def activeFilterOptions(self) -> list[dict[str, object]]:
        return self._active_filter_options

    @Property(str, notify=selectedSiteFilterChanged)
    def selectedSiteFilter(self) -> str:
        return self._selected_site_filter

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=locationsChanged)
    def locations(self) -> dict[str, object]:
        return self._locations

    @Property("QVariantMap", notify=systemsChanged)
    def systems(self) -> dict[str, object]:
        return self._systems

    @Property("QVariantMap", notify=assetsChanged)
    def assets(self) -> dict[str, object]:
        return self._assets

    @Property("QVariantMap", notify=componentsChanged)
    def components(self) -> dict[str, object]:
        return self._components

    @Property("QVariantMap", notify=selectedLocationChanged)
    def selectedLocation(self) -> dict[str, object]:
        return self._selected_location

    @Property("QVariantMap", notify=selectedSystemChanged)
    def selectedSystem(self) -> dict[str, object]:
        return self._selected_system

    @Property("QVariantMap", notify=selectedAssetChanged)
    def selectedAsset(self) -> dict[str, object]:
        return self._selected_asset

    @Property("QVariantMap", notify=selectedComponentChanged)
    def selectedComponent(self) -> dict[str, object]:
        return self._selected_component

    @Property(str, notify=selectedLocationIdChanged)
    def selectedLocationId(self) -> str:
        return self._selected_location_id

    @Property(str, notify=selectedSystemIdChanged)
    def selectedSystemId(self) -> str:
        return self._selected_system_id

    @Property(str, notify=selectedAssetIdChanged)
    def selectedAssetId(self) -> str:
        return self._selected_asset_id

    @Property(str, notify=selectedComponentIdChanged)
    def selectedComponentId(self) -> str:
        return self._selected_component_id

    @Property("QVariantList", notify=formSiteOptionsChanged)
    def formSiteOptions(self) -> list[dict[str, str]]:
        return self._form_site_options

    @Property("QVariantList", notify=formLocationOptionsChanged)
    def formLocationOptions(self) -> list[dict[str, str]]:
        return self._form_location_options

    @Property("QVariantList", notify=formParentLocationOptionsChanged)
    def formParentLocationOptions(self) -> list[dict[str, str]]:
        return self._form_parent_location_options

    @Property("QVariantList", notify=formSystemOptionsChanged)
    def formSystemOptions(self) -> list[dict[str, str]]:
        return self._form_system_options

    @Property("QVariantList", notify=formParentSystemOptionsChanged)
    def formParentSystemOptions(self) -> list[dict[str, str]]:
        return self._form_parent_system_options

    @Property("QVariantList", notify=formAssetOptionsChanged)
    def formAssetOptions(self) -> list[dict[str, str]]:
        return self._form_asset_options

    @Property("QVariantList", notify=formParentAssetOptionsChanged)
    def formParentAssetOptions(self) -> list[dict[str, str]]:
        return self._form_parent_asset_options

    @Property("QVariantList", notify=formComponentOptionsChanged)
    def formComponentOptions(self) -> list[dict[str, str]]:
        return self._form_component_options

    @Property("QVariantList", notify=formParentComponentOptionsChanged)
    def formParentComponentOptions(self) -> list[dict[str, str]]:
        return self._form_parent_component_options

    @Property("QVariantList", notify=formStatusOptionsChanged)
    def formStatusOptions(self) -> list[dict[str, str]]:
        return self._form_status_options

    @Property("QVariantList", notify=formCriticalityOptionsChanged)
    def formCriticalityOptions(self) -> list[dict[str, str]]:
        return self._form_criticality_options

    @Property("QVariantList", notify=formManufacturerOptionsChanged)
    def formManufacturerOptions(self) -> list[dict[str, str]]:
        return self._form_manufacturer_options

    @Property("QVariantList", notify=formSupplierOptionsChanged)
    def formSupplierOptions(self) -> list[dict[str, str]]:
        return self._form_supplier_options

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            state = serialize_assets_workspace_state(
                self._assets_workspace_presenter.build_workspace_state(
                    search_text=self._search_text,
                    site_filter=self._selected_site_filter,
                    active_filter=self._selected_active_filter,
                    selected_location_id=self._selected_location_id or None,
                    selected_system_id=self._selected_system_id or None,
                    selected_asset_id=self._selected_asset_id or None,
                    selected_component_id=self._selected_component_id or None,
                )
            )
            self._set_overview(state["overview"])
            self._set_site_options(state["siteOptions"])
            self._set_active_filter_options(state["activeFilterOptions"])
            self._set_selected_site_filter(str(state["selectedSiteFilter"]))
            self._set_selected_active_filter(str(state["selectedActiveFilter"]))
            self._set_search_text(str(state["searchText"]))
            self._set_locations(state["locations"])
            self._set_systems(state["systems"])
            self._set_assets(state["assets"])
            self._set_components(state["components"])
            self._set_selected_location_id(str(state["selectedLocationId"]))
            self._set_selected_system_id(str(state["selectedSystemId"]))
            self._set_selected_asset_id(str(state["selectedAssetId"]))
            self._set_selected_component_id(str(state["selectedComponentId"]))
            self._set_selected_location(state["selectedLocation"])
            self._set_selected_system(state["selectedSystem"])
            self._set_selected_asset(state["selectedAsset"])
            self._set_selected_component(state["selectedComponent"])
            self._set_form_site_options(state["formSiteOptions"])
            self._set_form_location_options(state["formLocationOptions"])
            self._set_form_parent_location_options(state["formParentLocationOptions"])
            self._set_form_system_options(state["formSystemOptions"])
            self._set_form_parent_system_options(state["formParentSystemOptions"])
            self._set_form_asset_options(state["formAssetOptions"])
            self._set_form_parent_asset_options(state["formParentAssetOptions"])
            self._set_form_component_options(state["formComponentOptions"])
            self._set_form_parent_component_options(
                state["formParentComponentOptions"]
            )
            self._set_form_status_options(state["formStatusOptions"])
            self._set_form_criticality_options(state["formCriticalityOptions"])
            self._set_form_manufacturer_options(state["formManufacturerOptions"])
            self._set_form_supplier_options(state["formSupplierOptions"])
            self._set_empty_state(str(state["emptyState"]))
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
        self.refresh()

    @Slot(str)
    def setSiteFilter(self, site_id: str) -> None:
        normalized = (site_id or "").strip() or "all"
        if normalized == self._selected_site_filter:
            return
        self._set_selected_site_filter(normalized)
        self.refresh()

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        normalized = (active_filter or "").strip() or "all"
        if normalized == self._selected_active_filter:
            return
        self._set_selected_active_filter(normalized)
        self.refresh()

    @Slot(str)
    def selectLocation(self, location_id: str) -> None:
        normalized = (location_id or "").strip()
        if normalized == self._selected_location_id:
            return
        self._set_selected_location_id(normalized)
        self.refresh()

    @Slot(str)
    def selectSystem(self, system_id: str) -> None:
        normalized = (system_id or "").strip()
        if normalized == self._selected_system_id:
            return
        self._set_selected_system_id(normalized)
        self.refresh()

    @Slot(str)
    def selectAsset(self, asset_id: str) -> None:
        normalized = (asset_id or "").strip()
        if normalized == self._selected_asset_id:
            return
        self._set_selected_asset_id(normalized)
        self.refresh()

    @Slot(str)
    def selectComponent(self, component_id: str) -> None:
        normalized = (component_id or "").strip()
        if normalized == self._selected_component_id:
            return
        self._set_selected_component_id(normalized)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.create_location(
                dict(payload)
            ),
            success_message="Location created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateLocation(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.update_location(
                dict(payload)
            ),
            success_message="Location updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleLocationActive(
        self,
        location_id: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.toggle_location_active(
                location_id,
                expected_version=expected_version,
            ),
            success_message="Location active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createSystem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.create_system(
                dict(payload)
            ),
            success_message="System created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateSystem(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.update_system(
                dict(payload)
            ),
            success_message="System updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleSystemActive(
        self,
        system_id: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.toggle_system_active(
                system_id,
                expected_version=expected_version,
            ),
            success_message="System active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createAsset(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.create_asset(
                dict(payload)
            ),
            success_message="Asset created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateAsset(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.update_asset(
                dict(payload)
            ),
            success_message="Asset updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleAssetActive(
        self,
        asset_id: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.toggle_asset_active(
                asset_id,
                expected_version=expected_version,
            ),
            success_message="Asset active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createComponent(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.create_component(
                dict(payload)
            ),
            success_message="Component created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateComponent(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.update_component(
                dict(payload)
            ),
            success_message="Component updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, int, result="QVariantMap")
    def toggleComponentActive(
        self,
        component_id: str,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._assets_workspace_presenter.toggle_component_active(
                component_id,
                expected_version=expected_version,
            ),
            success_message="Component active state updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_site_options(self, options: list[dict[str, object]]) -> None:
        if options == self._site_options:
            return
        self._site_options = options
        self.siteOptionsChanged.emit()

    def _set_active_filter_options(self, options: list[dict[str, object]]) -> None:
        if options == self._active_filter_options:
            return
        self._active_filter_options = options
        self.activeFilterOptionsChanged.emit()

    def _set_selected_site_filter(self, value: str) -> None:
        if value == self._selected_site_filter:
            return
        self._selected_site_filter = value
        self.selectedSiteFilterChanged.emit()

    def _set_selected_active_filter(self, value: str) -> None:
        if value == self._selected_active_filter:
            return
        self._selected_active_filter = value
        self.selectedActiveFilterChanged.emit()

    def _set_search_text(self, value: str) -> None:
        if value == self._search_text:
            return
        self._search_text = value
        self.searchTextChanged.emit()

    def _set_locations(self, value: dict[str, object]) -> None:
        if value == self._locations:
            return
        self._locations = value
        self.locationsChanged.emit()

    def _set_systems(self, value: dict[str, object]) -> None:
        if value == self._systems:
            return
        self._systems = value
        self.systemsChanged.emit()

    def _set_assets(self, value: dict[str, object]) -> None:
        if value == self._assets:
            return
        self._assets = value
        self.assetsChanged.emit()

    def _set_components(self, value: dict[str, object]) -> None:
        if value == self._components:
            return
        self._components = value
        self.componentsChanged.emit()

    def _set_selected_location(self, value: dict[str, object]) -> None:
        if value == self._selected_location:
            return
        self._selected_location = value
        self.selectedLocationChanged.emit()

    def _set_selected_system(self, value: dict[str, object]) -> None:
        if value == self._selected_system:
            return
        self._selected_system = value
        self.selectedSystemChanged.emit()

    def _set_selected_asset(self, value: dict[str, object]) -> None:
        if value == self._selected_asset:
            return
        self._selected_asset = value
        self.selectedAssetChanged.emit()

    def _set_selected_component(self, value: dict[str, object]) -> None:
        if value == self._selected_component:
            return
        self._selected_component = value
        self.selectedComponentChanged.emit()

    def _set_selected_location_id(self, value: str) -> None:
        if value == self._selected_location_id:
            return
        self._selected_location_id = value
        self.selectedLocationIdChanged.emit()

    def _set_selected_system_id(self, value: str) -> None:
        if value == self._selected_system_id:
            return
        self._selected_system_id = value
        self.selectedSystemIdChanged.emit()

    def _set_selected_asset_id(self, value: str) -> None:
        if value == self._selected_asset_id:
            return
        self._selected_asset_id = value
        self.selectedAssetIdChanged.emit()

    def _set_selected_component_id(self, value: str) -> None:
        if value == self._selected_component_id:
            return
        self._selected_component_id = value
        self.selectedComponentIdChanged.emit()

    def _set_form_site_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_site_options:
            return
        self._form_site_options = value
        self.formSiteOptionsChanged.emit()

    def _set_form_location_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_location_options:
            return
        self._form_location_options = value
        self.formLocationOptionsChanged.emit()

    def _set_form_parent_location_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_parent_location_options:
            return
        self._form_parent_location_options = value
        self.formParentLocationOptionsChanged.emit()

    def _set_form_system_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_system_options:
            return
        self._form_system_options = value
        self.formSystemOptionsChanged.emit()

    def _set_form_parent_system_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_parent_system_options:
            return
        self._form_parent_system_options = value
        self.formParentSystemOptionsChanged.emit()

    def _set_form_asset_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_asset_options:
            return
        self._form_asset_options = value
        self.formAssetOptionsChanged.emit()

    def _set_form_parent_asset_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_parent_asset_options:
            return
        self._form_parent_asset_options = value
        self.formParentAssetOptionsChanged.emit()

    def _set_form_component_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_component_options:
            return
        self._form_component_options = value
        self.formComponentOptionsChanged.emit()

    def _set_form_parent_component_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_parent_component_options:
            return
        self._form_parent_component_options = value
        self.formParentComponentOptionsChanged.emit()

    def _set_form_status_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_status_options:
            return
        self._form_status_options = value
        self.formStatusOptionsChanged.emit()

    def _set_form_criticality_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_criticality_options:
            return
        self._form_criticality_options = value
        self.formCriticalityOptionsChanged.emit()

    def _set_form_manufacturer_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_manufacturer_options:
            return
        self._form_manufacturer_options = value
        self.formManufacturerOptionsChanged.emit()

    def _set_form_supplier_options(self, value: list[dict[str, str]]) -> None:
        if value == self._form_supplier_options:
            return
        self._form_supplier_options = value
        self.formSupplierOptionsChanged.emit()


__all__ = ["MaintenanceAssetsWorkspaceController"]
