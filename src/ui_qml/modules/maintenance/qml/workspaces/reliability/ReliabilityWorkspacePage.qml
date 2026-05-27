import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceReliabilityWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.reliabilityWorkspace
        : null
    readonly property var workspaceModel: root.maintenanceCatalog
        ? root.maintenanceCatalog.workspace("maintenance_management.reliability")
        : ({
            "routeId": "maintenance_management.reliability",
            "title": "Reliability",
            "summary": "Sensors, readings, exceptions, downtime events, and recurring-failure analysis.",
            "migrationStatus": "QML reliability analytics slice active",
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

            ReliabilityFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? root.workspaceController.siteOptions : []
                assetOptions: root.workspaceController ? root.workspaceController.assetOptions : []
                systemOptions: root.workspaceController ? root.workspaceController.systemOptions : []
                locationOptions: root.workspaceController ? root.workspaceController.locationOptions : []
                failureSymptomOptions: root.workspaceController ? root.workspaceController.failureSymptomOptions : []
                daysOptions: root.workspaceController ? root.workspaceController.daysOptions : []
                limitOptions: root.workspaceController ? root.workspaceController.limitOptions : []
                thresholdOptions: root.workspaceController ? root.workspaceController.thresholdOptions : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedAssetFilter: root.workspaceController ? root.workspaceController.selectedAssetFilter : "all"
                selectedSystemFilter: root.workspaceController ? root.workspaceController.selectedSystemFilter : "all"
                selectedLocationFilter: root.workspaceController ? root.workspaceController.selectedLocationFilter : "all"
                selectedFailureCodeFilter: root.workspaceController ? root.workspaceController.selectedFailureCodeFilter : "all"
                selectedDaysFilter: root.workspaceController ? root.workspaceController.selectedDaysFilter : "90"
                selectedLimitFilter: root.workspaceController ? root.workspaceController.selectedLimitFilter : "20"
                selectedThresholdFilter: root.workspaceController ? root.workspaceController.selectedThresholdFilter : "2"
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
                onFailureCodeFilterUpdated: function(failureCode) {
                    if (root.workspaceController) {
                        root.workspaceController.setFailureCodeFilter(failureCode)
                    }
                }
                onDaysFilterUpdated: function(days) {
                    if (root.workspaceController) {
                        root.workspaceController.setDaysFilter(days)
                    }
                }
                onLimitFilterUpdated: function(limitValue) {
                    if (root.workspaceController) {
                        root.workspaceController.setLimitFilter(limitValue)
                    }
                }
                onThresholdFilterUpdated: function(thresholdValue) {
                    if (root.workspaceController) {
                        root.workspaceController.setThresholdFilter(thresholdValue)
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
                architectureStatus: "Reliability desktop API"
                architectureSummary: "Root-cause suggestions, recurring-failure analytics, and filter-driven review now render through the typed maintenance QML catalog."
            }

            ReliabilitySuggestionsSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.suggestionRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            ReliabilityRootCausesSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.rootCauseRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }

            ReliabilityRecurringSection {
                Layout.fillWidth: true
                items: root.workspaceController ? root.workspaceController.recurringRows : []
                emptyState: root.workspaceController ? root.workspaceController.emptyState : ""
            }
        }
    }
}
