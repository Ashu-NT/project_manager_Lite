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
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) {
            root._caps = root.platformCatalog.capabilitySnapshot()
        }
    }

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenanceWorkOrdersWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.workOrdersWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.work_orders",
            "title": "Work Orders",
            "summary": "Execution planning, lifecycle control, and assignment readiness for maintenance delivery.",
            "migrationStatus": "QML work-order slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var workOrdersModel: root.workspaceController
        ? root.workspaceController.workOrders
        : ({
            "title": "Work Orders",
            "subtitle": "Review execution records, readiness state, and lifecycle progression before deeper execution handling.",
            "emptyState": "Maintenance work-orders desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedWorkOrderModel: root.workspaceController
        ? root.workspaceController.selectedWorkOrder
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a work order to inspect execution scope, planning state, and update actions.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",              "label": "Code",     "flex": 1,   "sortable": true  },
        { "key": "subtitle",           "label": "Title",    "flex": 2,   "sortable": true  },
        { "key": "siteLabel",          "label": "Site",     "flex": 1.2, "sortable": true  },
        { "key": "statusLabel",        "label": "Status",   "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "priorityLabel",      "label": "Priority", "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "workOrderTypeLabel", "label": "Type",     "flex": 1,   "sortable": true  },
        { "key": "assetLabel",         "label": "Asset",    "flex": 1.5                    },
        { "key": "plannedStart",       "label": "Planned",  "flex": 0,   "minWidth": 100   }
    ]

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.WorkOrdersDialogHost {

        siteOptions: root.workspaceController ? (root.workspaceController.formSiteOptions || []) : []
        locationOptions: root.workspaceController ? (root.workspaceController.formLocationOptions || []) : []
        systemOptions: root.workspaceController ? (root.workspaceController.formSystemOptions || []) : []
        assetOptions: root.workspaceController ? (root.workspaceController.formAssetOptions || []) : []
        componentOptions: root.workspaceController ? (root.workspaceController.formComponentOptions || []) : []
        sourceTypeOptions: root.workspaceController ? (root.workspaceController.formSourceTypeOptions || []) : []
        sourceWorkRequestOptions: root.workspaceController ? (root.workspaceController.formSourceWorkRequestOptions || []) : []
        workOrderTypeOptions: root.workspaceController ? (root.workspaceController.formWorkOrderTypeOptions || []) : []
        priorityOptions: root.workspaceController ? (root.workspaceController.formPriorityOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.formStatusOptions || []) : []
        vendorOptions: root.workspaceController ? (root.workspaceController.formVendorOptions || []) : []

                workspaceController: root.workspaceController

                onStatusChangeRequested: function(workOrderId, statusValue, expectedVersion) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setWorkOrderStatus(workOrderId, statusValue, expectedVersion)
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
                ? "QML work-order slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Work-order filters, execution-scope edits, and lifecycle status changes now run through a typed maintenance controller backed by the work-orders desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search work orders…"
            showCreate: true
            createLabel: "New Work Order"
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

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: workOrdersTable
                anchors.fill: parent
                columns: root._tableColumns
                sourceModel: root.workspaceController ? root.workspaceController.workOrdersTableModel : null
                selectedRowId: root.workspaceController ? root.workspaceController.selectedWorkOrderId : ""
                showFilter: true

                onFilterClicked: filterPopup.open()
                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkOrder(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkOrder(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectWorkOrder(rowId)
                    detailPage.open = true
                }            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: workOrdersTable.filterButtonItem
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
                        text: "Type"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.workOrderTypeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.workOrderTypeOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setWorkOrderTypeFilter(String(opts[index].value || "all"))
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
                title: root.selectedWorkOrderModel.title || "Work Order Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Details", "Actions"]

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedWorkOrderModel)
                onDeleteRequested: detailPage.open = false

                // ── Detail-scoped messages ─────────────────────────
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: detailPage.open
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: detailPage.open
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.WorkOrderDetailPanel {
                    width: parent.width
                    detailPage: detailPage
                    workOrderDetail: root.selectedWorkOrderModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedWorkOrderModel)
                    onStatusRequested: dialogHostLoader.invoke("openStatusDialog", root.selectedWorkOrderModel)
                }
            }
        }
    }
}
