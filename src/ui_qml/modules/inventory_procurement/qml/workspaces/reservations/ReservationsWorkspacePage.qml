pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) {
            root._caps = root.platformCatalog.capabilitySnapshot()
        }
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementReservationsWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.reservationsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.reservations",
            "title": "Reservations",
            "summary": "Reservation holds, issuing, release flows, and source-reference stock demand.",
            "migrationStatus": "QML reservations slice active",
            "legacyRuntimeStatus": "Existing QWidget reservations workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var reservationsModel: root.workspaceController
        ? root.workspaceController.reservations
        : ({
            "title": "Reservations",
            "subtitle": "Manage stock holds, issuing, release, and cancellation flows against real upstream demand.",
            "emptyState": "Reservations desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedReservationModel: root.workspaceController
        ? root.workspaceController.selectedReservation
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a reservation to inspect source context or operate on the remaining quantity.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ReservationsDialogHost {
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []

                onCreateReservationRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.createReservation(payload)
                    }
                }

                onIssueReservationRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.issueReservation(payload)
                    }
                }

                onReleaseReservationRequested: function(reservationId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.releaseReservation(reservationId)
                    }
                }

                onCancelReservationRequested: function(reservationId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.cancelReservation(reservationId)
                    }
                }
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

            ReservationsMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            InventoryWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            InventoryWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML reservations slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Reservation search, filters, create, issue, release, and cancel flows now run through a typed reservations controller backed by the split reservations desktop API."
            }

            ReservationsFiltersSection {
                Layout.fillWidth: true
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                selectedItemFilter: root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                selectedStoreroomFilter: root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onStatusFilterUpdated: function(status) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(status)
                    }
                }

                onItemFilterUpdated: function(itemId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setItemFilter(itemId)
                    }
                }

                onStoreroomFilterUpdated: function(storeroomId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStoreroomFilter(storeroomId)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateReservationRequested: dialogHostLoader.invoke(
                    "openCreateReservationDialog",
                    root.workspaceController ? root.workspaceController.selectedItemFilter : "all",
                    root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                )
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ReservationsCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    reservationsModel: root.reservationsModel
                    selectedReservationId: root.workspaceController ? root.workspaceController.selectedReservationId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onReservationSelected: function(reservationId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectReservation(reservationId)
                        }
                    }

                    onIssueRequested: function(reservationData) {
                        if (reservationData && reservationData.id && root.workspaceController !== null) {
                            root.workspaceController.selectReservation(reservationData.id)
                        }
                        dialogHostLoader.invoke("openIssueReservationDialog", reservationData)
                    }

                    onReleaseRequested: function(reservationData) {
                        if (reservationData && reservationData.id && root.workspaceController !== null) {
                            root.workspaceController.selectReservation(reservationData.id)
                        }
                        dialogHostLoader.invoke("openReleaseConfirmation", reservationData)
                    }

                    onCancelRequested: function(reservationData) {
                        if (reservationData && reservationData.id && root.workspaceController !== null) {
                            root.workspaceController.selectReservation(reservationData.id)
                        }
                        dialogHostLoader.invoke("openCancelConfirmation", reservationData)
                    }
                }

                ReservationDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    reservationDetail: root.selectedReservationModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onIssueRequested: dialogHostLoader.invoke("openIssueReservationDialog", root.selectedReservationModel)
                    onReleaseRequested: dialogHostLoader.invoke("openReleaseConfirmation", root.selectedReservationModel)
                    onCancelRequested: dialogHostLoader.invoke("openCancelConfirmation", root.selectedReservationModel)
                }
            }
        }
    }
}
