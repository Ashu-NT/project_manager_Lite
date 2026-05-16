import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceWorkRequestsWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.workRequestsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.work_requests",
            "title": "Work Requests",
            "summary": "Request intake, triage, conversion to execution, and backlog prioritization.",
            "migrationStatus": "QML work-request slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var workRequestsModel: root.workspaceController
        ? root.workspaceController.workRequests
        : ({
            "title": "Work Requests",
            "subtitle": "Review intake requests, triage state, and conversion-ready backlog before execution planning.",
            "emptyState": "Maintenance work-requests desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedWorkRequestModel: root.workspaceController
        ? root.workspaceController.selectedWorkRequest
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a work request to inspect its intake context, triage state, and update actions.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    WorkRequestsDialogHost {
        id: dialogHost

        siteOptions: root.workspaceController ? (root.workspaceController.formSiteOptions || []) : []
        locationOptions: root.workspaceController ? (root.workspaceController.formLocationOptions || []) : []
        systemOptions: root.workspaceController ? (root.workspaceController.formSystemOptions || []) : []
        assetOptions: root.workspaceController ? (root.workspaceController.formAssetOptions || []) : []
        componentOptions: root.workspaceController ? (root.workspaceController.formComponentOptions || []) : []
        sourceTypeOptions: root.workspaceController ? (root.workspaceController.formSourceTypeOptions || []) : []
        priorityOptions: root.workspaceController ? (root.workspaceController.formPriorityOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.formStatusOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createWorkRequest(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateWorkRequest(payload)
            }
        }

        onStatusChangeRequested: function(workRequestId, statusValue, expectedVersion) {
            if (root.workspaceController !== null) {
                root.workspaceController.setWorkRequestStatus(workRequestId, statusValue, expectedVersion)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            WorkRequestsMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            MaintenanceWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            MaintenanceWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML work-request slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Work-request filters, intake edits, and triage status changes now run through a typed maintenance controller backed by the work-requests desktop API."
            }

            WorkRequestsFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                priorityOptions: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                assetOptions: root.workspaceController ? (root.workspaceController.assetOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                selectedPriorityFilter: root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
                selectedAssetFilter: root.workspaceController ? root.workspaceController.selectedAssetFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onSiteFilterUpdated: function(siteId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSiteFilter(siteId)
                    }
                }

                onStatusFilterUpdated: function(statusValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(statusValue)
                    }
                }

                onPriorityFilterUpdated: function(priorityValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setPriorityFilter(priorityValue)
                    }
                }

                onAssetFilterUpdated: function(assetId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setAssetFilter(assetId)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateRequested: function() {
                    dialogHost.openCreateDialog()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                WorkRequestsCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    workRequestsModel: root.workRequestsModel
                    selectedWorkRequestId: root.workspaceController ? root.workspaceController.selectedWorkRequestId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onWorkRequestSelected: function(workRequestId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectWorkRequest(workRequestId)
                        }
                    }

                    onEditRequested: function(workRequestData) {
                        if (workRequestData && workRequestData.id && root.workspaceController !== null) {
                            root.workspaceController.selectWorkRequest(workRequestData.id)
                        }
                        dialogHost.openEditDialog(workRequestData)
                    }

                    onStatusRequested: function(workRequestData) {
                        if (workRequestData && workRequestData.id && root.workspaceController !== null) {
                            root.workspaceController.selectWorkRequest(workRequestData.id)
                        }
                        dialogHost.openStatusDialog(workRequestData)
                    }
                }

                WorkRequestDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    workRequestDetail: root.selectedWorkRequestModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedWorkRequestModel)
                    onStatusRequested: dialogHost.openStatusDialog(root.selectedWorkRequestModel)
                }
            }
        }
    }
}
