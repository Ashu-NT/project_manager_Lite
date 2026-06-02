import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import "sections" as Sections

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenancePlannerWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.plannerWorkspace
        : null
    readonly property var workspaceModel: root.maintenanceCatalog
        ? root.maintenanceCatalog.workspace("maintenance_management.planner")
        : ({
            "routeId": "maintenance_management.planner",
            "title": "Planner",
            "summary": "Forward maintenance scheduling, release readiness, and capacity-aware planning views.",
            "migrationStatus": "QML planner review slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            MaintenanceWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            Sections.PlannerFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? root.workspaceController.siteOptions : []
                assetOptions: root.workspaceController ? root.workspaceController.assetOptions : []
                systemOptions: root.workspaceController ? root.workspaceController.systemOptions : []
                requestQueueOptions: root.workspaceController ? root.workspaceController.requestQueueOptions : []
                workOrderQueueOptions: root.workspaceController ? root.workspaceController.workOrderQueueOptions : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedAssetFilter: root.workspaceController ? root.workspaceController.selectedAssetFilter : "all"
                selectedSystemFilter: root.workspaceController ? root.workspaceController.selectedSystemFilter : "all"
                selectedRequestQueue: root.workspaceController ? root.workspaceController.selectedRequestQueue : ""
                selectedWorkOrderQueue: root.workspaceController ? root.workspaceController.selectedWorkOrderQueue : ""
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                onSiteFilterUpdated: function(siteId) {
                    if (root.workspaceController) {
                        root.workspaceController.setSiteFilter(siteId)
                    }
                }
                onAssetFilterUpdated: function(assetId) {
                    if (root.workspaceController) {
                        root.workspaceController.setAssetFilter(assetId)
                    }
                }
                onSystemFilterUpdated: function(systemId) {
                    if (root.workspaceController) {
                        root.workspaceController.setSystemFilter(systemId)
                    }
                }
                onRequestQueueUpdated: function(requestQueue) {
                    if (root.workspaceController) {
                        root.workspaceController.setRequestQueue(requestQueue)
                    }
                }
                onWorkOrderQueueUpdated: function(workOrderQueue) {
                    if (root.workspaceController) {
                        root.workspaceController.setWorkOrderQueue(workOrderQueue)
                    }
                }
                onSearchTextUpdated: function(searchValue) {
                    if (root.workspaceController) {
                        root.workspaceController.setSearchText(searchValue)
                    }
                }
                onRefreshRequested: function() {
                    if (root.workspaceController) {
                        root.workspaceController.refresh()
                    }
                }
            }

            AppWidgets.KpiStrip {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            MaintenanceWidgets.WorkspaceStatusSection {
                visible: false
                Layout.fillWidth: true
                migrationStatus: root.workspaceModel.migrationStatus || ""
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Planner desktop API"
                architectureSummary: "Planner intake, backlog, material risk, preventive readiness, and recurring review now render through the typed maintenance QML catalog."
            }

            Sections.PlannerRequestsSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.requestRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            Sections.PlannerBacklogSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.workOrderRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            Sections.PlannerMaterialRisksSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.materialRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            Sections.PlannerPreventiveSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.preventiveRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            Sections.PlannerRecurringSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.recurringRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }
        }
    }
}
