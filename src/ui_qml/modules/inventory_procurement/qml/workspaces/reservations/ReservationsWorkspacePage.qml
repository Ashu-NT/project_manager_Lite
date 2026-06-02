pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import "dialogs" as Dialogs
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})
    Component.onCompleted: { if (root.platformCatalog) root._caps = root.platformCatalog.capabilitySnapshot() }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementReservationsWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.reservationsWorkspace
        : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Reservations", "subtitle": "Stock holds, issuing, release, and cancellation flows.", "metrics": [] })
    readonly property var reservationsModel: root.workspaceController
        ? root.workspaceController.reservations
        : ({ "items": [], "emptyState": "No reservations found." })
    readonly property var selectedReservationModel: root.workspaceController
        ? root.workspaceController.selectedReservation
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })

    title:    root.overviewModel.title    || "Reservations"
    subtitle: root.overviewModel.subtitle || ""

    // ── Detail state ───────────────────────────────────────────────────
    property bool _detailOpen:          false
    property int  _pendingDetailSection: 0
    readonly property var _detailPage:  _detailPageLoader.item

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        const st = root.selectedReservationModel.state || {}
        const actions = []
        if (st.canIssue)   actions.push({ "id": "issue",   "label": "Issue",   "icon": "arrow_down", "enabled": true, "danger": false })
        if (st.canRelease) actions.push({ "id": "release", "label": "Release", "icon": "approve",    "enabled": true, "danger": false })
        if (st.canCancel)  actions.push({ "id": "cancel",  "label": "Cancel",  "icon": "reject",     "enabled": true, "danger": true  })
        return actions
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null || sectionIndex !== 1) return
        root.workspaceController.loadDetailActivity(String(root.selectedReservationModel.id || ""), "stock_reservation")
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) {
            root._detailPage.scrollToSection(sectionIndex)
            root._loadLazyDetailSection(sectionIndex)
        }
    }

    // ── Export dialog ──────────────────────────────────────────────────
    FileDialog {
        id: _exportDialog
        title: "Export Reservations"; fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: { if (root.workspaceController !== null) root.workspaceController.exportTable([], String(selectedFile || "")) }
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.ReservationsDialogHost {
                itemOptions:     root.workspaceController ? (root.workspaceController.itemOptions     || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                workspaceController: root.workspaceController
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.ReservationsListPage {
                anchors.fill:         parent
                workspaceController:  root.workspaceController
                overviewModel:        root.overviewModel
                reservationsModel:    root.reservationsModel
                detailOpen:           root._detailOpen

                onRowActivated:    root._openDetail(0)
                onExportRequested: _exportDialog.open()
                onCreateRequested: function(itemFilter, storeroomFilter) {
                    dialogHostLoader.invoke("openCreateReservationDialog", itemFilter, storeroomFilter)
                }
            }
        }

        Loader {
            id: _detailPageLoader
            anchors.fill: parent
            active:       root._detailOpen
            visible:      root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent
            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    ["Overview", "Activity"]
                z:           20
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root.selectedReservationModel.title    || "Reservation Detail"
                    subtitle: root.selectedReservationModel.statusLabel || root.selectedReservationModel.subtitle || ""
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  root._detailActions
                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if      (actionId === "issue")   dialogHostLoader.invoke("openIssueReservationDialog", root.selectedReservationModel)
                        else if (actionId === "release") dialogHostLoader.invoke("openReleaseConfirmation",    root.selectedReservationModel)
                        else if (actionId === "cancel")  dialogHostLoader.invoke("openCancelConfirmation",     root.selectedReservationModel)
                    }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.ReservationsDetailPanel {
                    width:               parent ? parent.width : 0
                    detailPage:          root._detailPage
                    reservationDetail:   root.selectedReservationModel
                    activityItems:       root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                }
            }
        }
    }
}
