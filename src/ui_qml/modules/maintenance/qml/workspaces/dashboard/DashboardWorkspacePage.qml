import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceDashboardWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.dashboardWorkspace
        : null
    readonly property var workspaceModel: root.maintenanceCatalog
        ? root.maintenanceCatalog.workspace("maintenance_management.dashboard")
        : ({
            "routeId": "maintenance_management.dashboard",
            "title": "Maintenance Dashboard",
            "summary": "Reliability KPIs, execution backlog, compliance watchlists, and downtime health.",
            "migrationStatus": "QML analytics dashboard slice active",
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

            DashboardFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? root.workspaceController.siteOptions : []
                assetOptions: root.workspaceController ? root.workspaceController.assetOptions : []
                systemOptions: root.workspaceController ? root.workspaceController.systemOptions : []
                locationOptions: root.workspaceController ? root.workspaceController.locationOptions : []
                windowOptions: root.workspaceController ? root.workspaceController.windowOptions : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedAssetFilter: root.workspaceController ? root.workspaceController.selectedAssetFilter : "all"
                selectedSystemFilter: root.workspaceController ? root.workspaceController.selectedSystemFilter : "all"
                selectedLocationFilter: root.workspaceController ? root.workspaceController.selectedLocationFilter : "all"
                selectedDaysFilter: root.workspaceController ? root.workspaceController.selectedDaysFilter : "90"
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
                onLocationFilterUpdated: function(locationId) {
                    if (root.workspaceController) {
                        root.workspaceController.setLocationFilter(locationId)
                    }
                }
                onDaysFilterUpdated: function(days) {
                    if (root.workspaceController) {
                        root.workspaceController.setDaysFilter(days)
                    }
                }
                onRefreshRequested: function() {
                    if (root.workspaceController) {
                        root.workspaceController.refresh()
                    }
                }
            }

            DashboardMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            MaintenanceWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceModel.migrationStatus || ""
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Dashboard desktop API"
                architectureSummary: "Maintenance backlog, root-cause, and recurring-failure analytics now render through the typed maintenance QML catalog."
            }

            DashboardBacklogSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.backlogRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            DashboardRootCausesSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.rootCauseRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            DashboardRecurringSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.recurringRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }
        }
    }
}
