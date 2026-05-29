pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

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
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })
    readonly property var selectedStoreroomModel: root.workspaceController
        ? root.workspaceController.selectedStoreroom
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })

    readonly property bool _isBalancesView: root.workspaceController
        ? root.workspaceController.activeView === "balances"
        : true

    title: root.overviewModel.title || "Inventory"
    subtitle: root.overviewModel.subtitle || ""

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _balanceColumns: [
        { "key": "title",            "label": "Item Name", "flex": 2,   "sortable": true  },
        { "key": "storeroomLabel",   "label": "Storeroom", "flex": 1.5 },
        { "key": "onHandQtyLabel",   "label": "On Hand",   "flex": 1   },
        { "key": "statusLabel",      "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _storeroomColumns: [
        { "key": "title",            "label": "Storeroom", "flex": 2,   "sortable": true  },
        { "key": "storeroomCode",    "label": "Code",      "flex": 1   },
        { "key": "siteLabel",        "label": "Site",      "flex": 1.5 },
        { "key": "statusLabel",      "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]

    readonly property var _detailSections: root._isBalancesView
        ? ["Overview", "Activity"]
        : ["Overview", "Activity"]

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        if (root._isBalancesView) {
            return [
                { "id": "issue",    "label": "Issue",    "icon": "arrow_down", "enabled": true, "danger": false },
                { "id": "adjust",   "label": "Adjust",   "icon": "edit",       "enabled": true, "danger": false },
                { "id": "transfer", "label": "Transfer", "icon": "transfer",   "enabled": true, "danger": false }
            ]
        }
        const detail = root.selectedStoreroomModel
        const isActive = detail && detail.state && detail.state.isActive
        return [
            { "id": "edit",   "label": "Edit",   "icon": "edit",             "enabled": true, "danger": false },
            { "id": "toggle", "label": isActive ? "Deactivate" : "Activate",
              "icon": isActive ? "reject" : "approve",                         "enabled": true, "danger": false }
        ]
    }

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) return
        if (sectionIndex !== 1) return
        const entityId = root._isBalancesView
            ? String(root.selectedBalanceModel.id || "")
            : String(root.selectedStoreroomModel.id || "")
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

    // ── Dialog host ────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            InventoryDialogHost {
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                storeroomStatusOptions: root.workspaceController ? (root.workspaceController.storeroomStatusOptions || []) : []
                managerPartyOptions: root.workspaceController ? (root.workspaceController.managerPartyOptions || []) : []
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []

                onCreateStoreroomRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createStoreroom(payload)
                }
                onUpdateStoreroomRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateStoreroom(payload)
                }
                onPostOpeningBalanceRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.postOpeningBalance(payload)
                }
                onPostAdjustmentRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.postAdjustment(payload)
                }
                onIssueStockRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.issueStock(payload)
                }
                onReturnStockRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.returnStock(payload)
                }
                onTransferStockRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.transferStock(payload)
                }
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────
    Item {
        anchors.fill: parent

        // ── List page ──────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading inventory..."
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Saving changes..."
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                    searchPlaceholder: root._isBalancesView ? "Search stock balances..." : "Search storerooms..."
                    showCreate: !root._isBalancesView
                    createLabel: "New Storeroom"
                    showFilter: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {}
                    onCreateRequested: dialogHostLoader.invoke("openCreateStoreroomDialog")
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _balancesTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: root._isBalancesView
                        multiSelect: true
                        columns: root._balanceColumns
                        sourceModel: root.workspaceController ? root.workspaceController.balancesTableModel : null
                        rows: root.balancesModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.balancesModel.emptyState || "No stock balances."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedBalanceId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedBalanceIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectBalance(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateBalance(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setBalanceBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleBalances()
                            else root.workspaceController.clearBalanceBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.DataTable {
                        id: _storeroomsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: !root._isBalancesView
                        multiSelect: true
                        columns: root._storeroomColumns
                        sourceModel: root.workspaceController ? root.workspaceController.storeroomsTableModel : null
                        rows: root.storeroomsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.storeroomsModel.emptyState || "No storerooms configured."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedStoreroomId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedStoreroomIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectStoreroom(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateStoreroom(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setStoreroomBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleStorerooms()
                            else root.workspaceController.clearStoreroomBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root._isBalancesView
                            ? (root.workspaceController ? root.workspaceController.balancePage : 1)
                            : (root.workspaceController ? root.workspaceController.storeroomPage : 1)
                        pageSize: root._isBalancesView
                            ? (root.workspaceController ? root.workspaceController.balancePageSize : 25)
                            : (root.workspaceController ? root.workspaceController.storeroomPageSize : 25)
                        totalItems: root._isBalancesView
                            ? (root.workspaceController ? root.workspaceController.balanceTotalCount : 0)
                            : (root.workspaceController ? root.workspaceController.storeroomTotalCount : 0)
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController === null) return
                            if (root._isBalancesView) root.workspaceController.setBalancePage(page)
                            else root.workspaceController.setStoreroomPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController === null) return
                            if (root._isBalancesView) root.workspaceController.setBalancePageSize(size)
                            else root.workspaceController.setStoreroomPageSize(size)
                        }
                    }

                    // ── Filter popup ───────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 304
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Site"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.siteOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                                    }
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
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.activeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setActiveFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Storeroom"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: root._isBalancesView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: root._isBalancesView
                                model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setStoreroomFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Item"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: root._isBalancesView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: root._isBalancesView
                                model: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.itemOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setItemFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Clear"
                                    iconName: "close"
                                    onClicked: {
                                        if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                        filterPopup.close()
                                    }
                                }
                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text: "Apply"
                                    iconName: "filter"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    onClicked: filterPopup.close()
                                }
                            }
                        }
                    }

                    // ── Views popup ────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: viewsPopup
                        anchorItem: tableToolbar.viewsButtonItem
                        width: 220
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "View"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.PrimaryButton {
                                Layout.fillWidth: true
                                text: "Stock Balances"
                                iconName: "inventory"
                                enabled: !root._isBalancesView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("balances")
                                    viewsPopup.close()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Storerooms"
                                iconName: "location"
                                enabled: root._isBalancesView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("storerooms")
                                    viewsPopup.close()
                                }
                            }
                        }
                    }

                    // ── Bulk action bar ────────────────────────────
                    AppWidgets.BulkActionBar {
                        id: _balanceBulkBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        visible: root._isBalancesView
                        selectedCount: root.workspaceController ? root.workspaceController.selectedBalanceCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "opening_balance", "label": "Opening Balance", "icon": "add",   "danger": false, "enabled": true },
                            { "id": "adjustment",      "label": "Adjust",          "icon": "edit",  "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearBalanceBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "opening_balance") {
                                dialogHostLoader.invoke("openOpeningBalanceDialog",
                                    root.selectedBalanceModel, root.selectedStoreroomModel,
                                    root.workspaceController ? root.workspaceController.selectedItemFilter : "all")
                            } else if (actionId === "adjustment") {
                                dialogHostLoader.invoke("openAdjustmentDialog", root.selectedBalanceModel)
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (lazy loaded) ──────────────────────────────
        Loader {
            id: _detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: root._detailSections
                z: 20
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }

                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }

                // ── Contextual toolbar ─────────────────────────────
                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._isBalancesView
                        ? (root.selectedBalanceModel.title || "Balance Detail")
                        : (root.selectedStoreroomModel.title || "Storeroom Detail")
                    subtitle: root._isBalancesView
                        ? (root.selectedBalanceModel.statusLabel || root.selectedBalanceModel.subtitle || "")
                        : (root.selectedStoreroomModel.statusLabel || root.selectedStoreroomModel.subtitle || "")
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (root._isBalancesView) {
                            if (actionId === "issue") {
                                dialogHostLoader.invoke("openIssueDialog", root.selectedBalanceModel)
                            } else if (actionId === "adjust") {
                                dialogHostLoader.invoke("openAdjustmentDialog", root.selectedBalanceModel)
                            } else if (actionId === "transfer") {
                                dialogHostLoader.invoke("openTransferDialog", root.selectedBalanceModel)
                            }
                        } else {
                            if (actionId === "edit") {
                                dialogHostLoader.invoke("openEditStoreroomDialog", root.selectedStoreroomModel)
                            } else if (actionId === "toggle") {
                                const state = root.selectedStoreroomModel.state || {}
                                if (root.workspaceController !== null && state.storeroomId) {
                                    root.workspaceController.toggleStoreroomActive(
                                        String(state.storeroomId || ""),
                                        parseInt(String(state.version || "0"), 10)
                                    )
                                }
                            }
                        }
                    }
                }

                // ── Detail content (fields + activity) ─────────────
                Item {
                    id: _detailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _detailSectionArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _detail: root._isBalancesView
                        ? root.selectedBalanceModel
                        : root.selectedStoreroomModel
                    readonly property var _fields: _detailContent._detail ? (_detailContent._detail.fields || []) : []

                    Item {
                        id: _detailSectionArea
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.pagePadding
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.pagePadding
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.AppTheme.pagePadding
                        implicitHeight: _detailOverview.visible ? _detailOverview.implicitHeight
                            : _detailActivity.implicitHeight + Theme.AppTheme.spacingMd

                        // Overview
                        Item {
                            id: _detailOverview
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _detailContent._idx === 0
                            implicitHeight: _detailFieldsGrid.visible ? _detailFieldsGrid.implicitHeight : _detailEmpty.implicitHeight

                            GridLayout {
                                id: _detailFieldsGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingMd
                                visible: _detailContent._fields.length > 0

                                Repeater {
                                    model: _detailContent._fields

                                    delegate: ColumnLayout {
                                        id: _dfd
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 2

                                        AppControls.Label {
                                            text: _dfd.modelData.label || ""
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.family: Theme.AppTheme.fontFamily
                                            font.bold: true
                                        }
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: _dfd.modelData.value || "—"
                                            color: Theme.AppTheme.textPrimary
                                            font.pixelSize: Theme.AppTheme.bodySize
                                            font.family: Theme.AppTheme.fontFamily
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }
                                    }
                                }
                            }

                            AppWidgets.EmptyState {
                                id: _detailEmpty
                                width: parent.width
                                visible: _detailContent._fields.length === 0
                                title: _detailContent._detail
                                    ? (_detailContent._detail.emptyState || "No details available.")
                                    : "No details available."
                            }
                        }

                        // Activity
                        AppWidgets.ActivityFeed {
                            id: _detailActivity
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _detailContent._idx === 1
                            items: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                            emptyText: "No activity recorded yet."
                        }
                    }
                }
            }
        }
    }
}
