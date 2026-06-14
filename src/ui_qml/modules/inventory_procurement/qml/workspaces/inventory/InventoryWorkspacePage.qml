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
import "sections" as Sections
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) root._caps = root.platformCatalog.capabilitySnapshot()
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.inventoryWorkspace
        : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Inventory", "subtitle": "Stock balances, storerooms, and movement history.", "metrics": [] })
    readonly property var balancesModel: root.workspaceController
        ? root.workspaceController.balances
        : ({ "items": [], "emptyState": "No stock balances." })
    readonly property var storeroomsModel: root.workspaceController
        ? root.workspaceController.storerooms
        : ({ "items": [], "emptyState": "No storerooms configured." })
    readonly property var selectedBalanceModel: root.workspaceController
        ? root.workspaceController.selectedBalance
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "state": {} })
    readonly property var selectedStoreroomModel: root.workspaceController
        ? root.workspaceController.selectedStoreroom
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "state": {} })

    readonly property bool _isBalancesView: root.workspaceController
        ? root.workspaceController.activeView === "balances"
        : true

    title:    root.overviewModel.title    || "Inventory"
    subtitle: root.overviewModel.subtitle || ""

    // ── Detail state ───────────────────────────────────────────────────
    property bool _detailOpen: false
    property int  _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _detailSections: ["Overview", "Activity"]
    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        if (root._isBalancesView)
            return [
                { "id": "issue",    "label": "Issue",    "icon": "arrow_down", "enabled": true, "danger": false },
                { "id": "adjust",   "label": "Adjust",   "icon": "edit",       "enabled": true, "danger": false },
                { "id": "transfer", "label": "Transfer", "icon": "transfer",   "enabled": true, "danger": false }
            ]
        const detail   = root.selectedStoreroomModel
        const isActive = detail && detail.state && detail.state.isActive
        return [
            { "id": "edit",   "label": "Edit",                               "icon": "edit",                          "enabled": true, "danger": false },
            { "id": "toggle", "label": isActive ? "Deactivate" : "Activate", "icon": isActive ? "reject" : "approve", "enabled": true, "danger": false }
        ]
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null || sectionIndex !== 1) return
        const entityId   = root._isBalancesView ? String(root.selectedBalanceModel.id || "") : String(root.selectedStoreroomModel.id || "")
        const entityType = root._isBalancesView ? "inventory_stock_balance" : "inventory_storeroom"
        root.workspaceController.loadDetailActivity(entityId, entityType)
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
        title: "Export Inventory"; fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: { if (root.workspaceController !== null) root.workspaceController.exportTable([], String(selectedFile || "")) }
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.InventoryDialogHost {
                siteOptions:            root.workspaceController ? (root.workspaceController.siteOptions            || []) : []
                storeroomStatusOptions: root.workspaceController ? (root.workspaceController.storeroomStatusOptions || []) : []
                managerPartyOptions:    root.workspaceController ? (root.workspaceController.managerPartyOptions    || []) : []
                itemOptions:            root.workspaceController ? (root.workspaceController.itemOptions            || []) : []
                storeroomOptions:       root.workspaceController ? (root.workspaceController.storeroomOptions       || []) : []
                workspaceController:    root.workspaceController
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.InventoryListPage {
                anchors.fill:           parent
                workspaceController:    root.workspaceController
                overviewModel:          root.overviewModel
                balancesModel:          root.balancesModel
                storeroomsModel:        root.storeroomsModel
                selectedBalanceModel:   root.selectedBalanceModel
                selectedStoreroomModel: root.selectedStoreroomModel
                detailOpen:             root._detailOpen

                onRowActivated:            root._openDetail(0)
                onExportRequested:         _exportDialog.open()
                onCreateStoreroomRequested: dialogHostLoader.invoke("openCreateStoreroomDialog")
                onOpenOpeningBalanceDialogRequested: function(bal, storeroom, filter) {
                    dialogHostLoader.invoke("openOpeningBalanceDialog", bal, storeroom, filter)
                }
                onOpenAdjustmentDialogRequested: function(bal) {
                    dialogHostLoader.invoke("openAdjustmentDialog", bal)
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
                sections:    root._detailSections
                z:           20
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root._isBalancesView ? (root.selectedBalanceModel.title || "Balance Detail") : (root.selectedStoreroomModel.title || "Storeroom Detail")
                    subtitle: root._isBalancesView ? (root.selectedBalanceModel.statusLabel || root.selectedBalanceModel.subtitle || "") : (root.selectedStoreroomModel.statusLabel || root.selectedStoreroomModel.subtitle || "")
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  root._detailActions
                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (root._isBalancesView) {
                            if      (actionId === "issue")    dialogHostLoader.invoke("openIssueDialog", root.selectedBalanceModel)
                            else if (actionId === "adjust")   dialogHostLoader.invoke("openAdjustmentDialog", root.selectedBalanceModel)
                            else if (actionId === "transfer") dialogHostLoader.invoke("openTransferDialog", root.selectedBalanceModel)
                        } else {
                            if (actionId === "edit") {
                                dialogHostLoader.invoke("openEditStoreroomDialog", root.selectedStoreroomModel)
                            } else if (actionId === "toggle") {
                                const s = root.selectedStoreroomModel.state || {}
                                if (root.workspaceController !== null && s.storeroomId)
                                    root.workspaceController.toggleStoreroomActive(String(s.storeroomId || ""), parseInt(String(s.version || "0"), 10))
                            }
                        }
                    }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.InventoryDetailPanel {
                    width:         parent ? parent.width : 0
                    detailPage:    root._detailPage
                    fields:        root._isBalancesView ? (root.selectedBalanceModel.fields || []) : (root.selectedStoreroomModel.fields || [])
                    activityItems: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                    emptyState:    root._isBalancesView
                        ? (root.selectedBalanceModel.emptyState   || "Select a balance row to inspect details.")
                        : (root.selectedStoreroomModel.emptyState || "Select a storeroom row to inspect details.")
                }
            }
        }
    }
}
