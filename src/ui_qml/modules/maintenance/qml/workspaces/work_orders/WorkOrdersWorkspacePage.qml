import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets

AppLayouts.WorkspaceFrame {
    id: root

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

    WorkOrdersDialogHost {
        id: dialogHost

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

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createWorkOrder(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateWorkOrder(payload)
            }
        }

        onStatusChangeRequested: function(workOrderId, statusValue, expectedVersion) {
            if (root.workspaceController !== null) {
                root.workspaceController.setWorkOrderStatus(workOrderId, statusValue, expectedVersion)
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

            WorkOrdersMetricsSection {
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
                    ? "QML work-order slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Work-order filters, execution-scope edits, and lifecycle status changes now run through a typed maintenance controller backed by the work-orders desktop API."
            }

            WorkOrdersFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                priorityOptions: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                workOrderTypeOptions: root.workspaceController ? (root.workspaceController.workOrderTypeOptions || []) : []
                assetOptions: root.workspaceController ? (root.workspaceController.assetOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                selectedPriorityFilter: root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
                selectedWorkOrderTypeFilter: root.workspaceController ? root.workspaceController.selectedWorkOrderTypeFilter : "all"
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

                onWorkOrderTypeFilterUpdated: function(workOrderTypeValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setWorkOrderTypeFilter(workOrderTypeValue)
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

                WorkOrdersCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    workOrdersModel: root.workOrdersModel
                    selectedWorkOrderId: root.workspaceController ? root.workspaceController.selectedWorkOrderId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onWorkOrderSelected: function(workOrderId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectWorkOrder(workOrderId)
                        }
                    }

                    onEditRequested: function(workOrderData) {
                        if (workOrderData && workOrderData.id && root.workspaceController !== null) {
                            root.workspaceController.selectWorkOrder(workOrderData.id)
                        }
                        dialogHost.openEditDialog(workOrderData)
                    }

                    onStatusRequested: function(workOrderData) {
                        if (workOrderData && workOrderData.id && root.workspaceController !== null) {
                            root.workspaceController.selectWorkOrder(workOrderData.id)
                        }
                        dialogHost.openStatusDialog(workOrderData)
                    }
                }

                WorkOrderDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    workOrderDetail: root.selectedWorkOrderModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedWorkOrderModel)
                    onStatusRequested: dialogHost.openStatusDialog(root.selectedWorkOrderModel)
                }
            }
        }
    }
}
