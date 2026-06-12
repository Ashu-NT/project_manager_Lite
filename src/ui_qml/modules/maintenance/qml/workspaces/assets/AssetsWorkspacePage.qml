pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import "dialogs" as Dialogs
import "sections" as Sections
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceAssetsWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.assetsWorkspace
        : null

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.assets",
            "title": "Assets",
            "summary": "Sites, locations, systems, assets, and component-library structures for maintenance scope.",
            "migrationStatus": "QML asset-library slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
          })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var selectedLocationModel: root.workspaceController
        ? root.workspaceController.selectedLocation
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a location to inspect hierarchy, lifecycle state, and update actions.", "fields": [], "state": {} })
    readonly property var selectedSystemModel: root.workspaceController
        ? root.workspaceController.selectedSystem
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a system to inspect hierarchy, lifecycle state, and update actions.", "fields": [], "state": {} })
    readonly property var selectedAssetModel: root.workspaceController
        ? root.workspaceController.selectedAsset
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select an asset to inspect anchor context, lifecycle state, and update actions.", "fields": [], "state": {} })
    readonly property var selectedComponentModel: root.workspaceController
        ? root.workspaceController.selectedComponent
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "emptyState": "Select a component to inspect asset scope, lifecycle state, and update actions.", "fields": [], "state": {} })

    title:    root.overviewModel.title    || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    // ── Toggle helpers ─────────────────────────────────────────────────
    function _stateFrom(r) { return r && r.state ? r.state : (r || {}) }

    function _toggleForTab(detailModel, tabIndex) {
        const s = root._stateFrom(detailModel)
        if (root.workspaceController === null) return
        switch (tabIndex) {
        case 0: root.workspaceController.toggleLocationActive(String(s.locationId  || ""), Number(s.expectedVersion || 0)); break
        case 1: root.workspaceController.toggleSystemActive(  String(s.systemId    || ""), Number(s.expectedVersion || 0)); break
        case 2: root.workspaceController.toggleAssetActive(   String(s.assetId     || ""), Number(s.expectedVersion || 0)); break
        default: root.workspaceController.toggleComponentActive(String(s.componentId || ""), Number(s.expectedVersion || 0)); break
        }
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.AssetsDialogHost {
                siteOptions:              root.workspaceController ? (root.workspaceController.formSiteOptions             || []) : []
                locationOptions:          root.workspaceController ? (root.workspaceController.formLocationOptions         || []) : []
                parentLocationOptions:    root.workspaceController ? (root.workspaceController.formParentLocationOptions   || []) : []
                systemOptions:            root.workspaceController ? (root.workspaceController.formSystemOptions           || []) : []
                parentSystemOptions:      root.workspaceController ? (root.workspaceController.formParentSystemOptions     || []) : []
                assetOptions:             root.workspaceController ? (root.workspaceController.formAssetOptions            || []) : []
                parentAssetOptions:       root.workspaceController ? (root.workspaceController.formParentAssetOptions      || []) : []
                componentOptions:         root.workspaceController ? (root.workspaceController.formComponentOptions        || []) : []
                parentComponentOptions:   root.workspaceController ? (root.workspaceController.formParentComponentOptions  || []) : []
                statusOptions:            root.workspaceController ? (root.workspaceController.formStatusOptions           || []) : []
                criticalityOptions:       root.workspaceController ? (root.workspaceController.formCriticalityOptions      || []) : []
                manufacturerOptions:      root.workspaceController ? (root.workspaceController.formManufacturerOptions     || []) : []
                supplierOptions:          root.workspaceController ? (root.workspaceController.formSupplierOptions         || []) : []
                workspaceController:      root.workspaceController
            }
        }
    }

    // ── Layout ─────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        MaintenanceWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading:        root.workspaceController ? root.workspaceController.isLoading       : false
            isBusy:           root.workspaceController ? root.workspaceController.isBusy          : false
            errorMessage:     root.workspaceController ? root.workspaceController.errorMessage    : ""
            feedbackMessage:  root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        Components.AssetsLibraryPage {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            workspaceController:      root.workspaceController
            selectedLocationModel:    root.selectedLocationModel
            selectedSystemModel:      root.selectedSystemModel
            selectedAssetModel:       root.selectedAssetModel
            selectedComponentModel:   root.selectedComponentModel

            onCreateRequested: function(tabIndex) {
                switch (tabIndex) {
                case 0: dialogHostLoader.invoke("openCreateLocationDialog");  break
                case 1: dialogHostLoader.invoke("openCreateSystemDialog");    break
                case 2: dialogHostLoader.invoke("openCreateAssetDialog");     break
                default: dialogHostLoader.invoke("openCreateComponentDialog"); break
                }
            }
            onEditRequested: function(detailModel, tabIndex) {
                switch (tabIndex) {
                case 0: dialogHostLoader.invoke("openEditLocationDialog",  detailModel); break
                case 1: dialogHostLoader.invoke("openEditSystemDialog",    detailModel); break
                case 2: dialogHostLoader.invoke("openEditAssetDialog",     detailModel); break
                default: dialogHostLoader.invoke("openEditComponentDialog", detailModel); break
                }
            }
            onToggleActiveRequested: function(detailModel, tabIndex) {
                root._toggleForTab(detailModel, tabIndex)
            }
        }
    }
}
