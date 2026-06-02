pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import App.Controls 1.0 as AppControls
import "dialogs" as Dialogs
import "sections" as Sections

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

    readonly property var _tableColumns: [
        { "key": "title",          "label": "Code",        "flex": 1,   "sortable": true  },
        { "key": "subtitle",       "label": "Description", "flex": 2,   "sortable": true  },
        { "key": "statusLabel",    "label": "Status",      "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "priorityLabel",  "label": "Priority",    "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "assetLabel",     "label": "Asset",       "flex": 1.5                    },
        { "key": "requestedAt",    "label": "Requested",   "flex": 0,   "minWidth": 100   }
    ]

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.WorkRequestsDialogHost {

        siteOptions: root.workspaceController ? (root.workspaceController.formSiteOptions || []) : []
        locationOptions: root.workspaceController ? (root.workspaceController.formLocationOptions || []) : []
        systemOptions: root.workspaceController ? (root.workspaceController.formSystemOptions || []) : []
        assetOptions: root.workspaceController ? (root.workspaceController.formAssetOptions || []) : []
        componentOptions: root.workspaceController ? (root.workspaceController.formComponentOptions || []) : []
        sourceTypeOptions: root.workspaceController ? (root.workspaceController.formSourceTypeOptions || []) : []
        priorityOptions: root.workspaceController ? (root.workspaceController.formPriorityOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.formStatusOptions || []) : []

                workspaceController: root.workspaceController

                onStatusChangeRequested: function(workRequestId, statusValue, expectedVersion) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setWorkRequestStatus(workRequestId, statusValue, expectedVersion)
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
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
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML work-request slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Work-request filters, intake edits, and triage status changes now run through a typed maintenance controller backed by the work-requests desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search work requestsâ€¦"
            showCreate: true
            createLabel: "New Request"
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
        }

        // â”€â”€ Full-width table with full-page detail view â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: workRequestsTable
                anchors.fill: parent
                columns: root._tableColumns
                sourceModel: root.workspaceController ? root.workspaceController.workRequestsTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedWorkRequestId : ""
                showFilter: true

                onFilterClicked: filterPopup.open()
                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkRequest(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkRequest(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkRequest(rowId)
                    detailPage.open = true
                }            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: workRequestsTable.filterButtonItem
                width: 260
                padding: 12
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Column {
                    width: parent.width
                    spacing: 8

                    AppControls.Label {
                        text: "Site"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label {
                        text: "Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label {
                        text: "Priority"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setPriorityFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label {
                        text: "Asset"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.assetOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.assetOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setAssetFilter(String(opts[index].value || "all"))
                        }
                    }
                }
            }

            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedWorkRequestModel.title || "Work Request Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Details", "Actions"]

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedWorkRequestModel)
                onDeleteRequested: detailPage.open = false

                // â”€â”€ Detail-scoped messages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: detailPage.open
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: detailPage.open
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Sections.WorkRequestDetailPanel {
                    width: parent.width
                    detailPage: detailPage
                    workRequestDetail: root.selectedWorkRequestModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedWorkRequestModel)
                    onStatusRequested: dialogHostLoader.invoke("openStatusDialog", root.selectedWorkRequestModel)
                }
            }
        }
    }
}
