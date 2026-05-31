pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import QtQuick.Dialogs

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    FileDialog {
        id: _exportDialog
        title: "Export Reservations"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                const cols = _reservationsTable.columns.filter(function(c) { return c.visible !== false })
                    .map(function(c) { return { "key": c.key, "label": c.label } })
                root.workspaceController.exportTable(cols, String(selectedFile || ""))
            }
        }
    }

    Component.onCompleted: {
        if (root.platformCatalog) {
            root._caps = root.platformCatalog.capabilitySnapshot()
        }
    }

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

    title: root.overviewModel.title || "Reservations"
    subtitle: root.overviewModel.subtitle || ""

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _reservationColumns: [
        { "key": "title",            "label": "Reference",      "flex": 2,   "sortable": true },
        { "key": "subtitle",         "label": "Item / Storeroom", "flex": 1.5 },
        { "key": "remainingQtyLabel","label": "Remaining Qty",  "flex": 1 },
        { "key": "statusLabel",      "label": "Status",         "flex": 0,   "minWidth": 90, "type": "status" }
    ]

    readonly property var _detailSections: ["Overview", "Activity"]

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        const state = root.selectedReservationModel.state || {}
        const actions = []
        if (state.canIssue)   actions.push({ "id": "issue",   "label": "Issue",   "icon": "arrow_down", "enabled": true, "danger": false })
        if (state.canRelease) actions.push({ "id": "release", "label": "Release", "icon": "approve",    "enabled": true, "danger": false })
        if (state.canCancel)  actions.push({ "id": "cancel",  "label": "Cancel",  "icon": "reject",     "enabled": true, "danger": true  })
        return actions
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
        root.workspaceController.loadDetailActivity(
            String(root.selectedReservationModel.id || ""),
            "stock_reservation"
        )
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
            ReservationsDialogHost {
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                workspaceController: root.workspaceController
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
                    message: "Loading reservations..."
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
                    searchPlaceholder: "Search reservations..."
                    showCreate: true
                    createLabel: "New Reservation"
                    showFilter: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: _exportDialog.open()
                    onCreateRequested: dialogHostLoader.invoke(
                        "openCreateReservationDialog",
                        root.workspaceController ? root.workspaceController.selectedItemFilter : "all",
                        root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                    )
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _reservationsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._reservationColumns
                        sourceModel: root.workspaceController ? root.workspaceController.reservationsTableModel : null
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.reservationsModel.emptyState || "No reservations found."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedReservationId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedReservationIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectReservation(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateReservation(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setReservationBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleReservations()
                            else root.workspaceController.clearReservationBulkSelection()
                        }                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root.workspaceController ? root.workspaceController.reservationPage : 1
                        pageSize: root.workspaceController ? root.workspaceController.reservationPageSize : 25
                        totalItems: root.workspaceController ? root.workspaceController.reservationTotalCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setReservationPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController !== null) root.workspaceController.setReservationPageSize(size)
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
                                text: "Status"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Item"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
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

                            AppControls.Label {
                                text: "Storeroom"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
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

                    // ── Bulk action bar ────────────────────────────
                    AppWidgets.BulkActionBar {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedReservationCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "cancel", "label": "Cancel Selected", "icon": "reject", "danger": true, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearReservationBulkSelection()
                        }
                        onActionTriggered: function(actionId) {}
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

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedReservationModel.title || "Reservation Detail"
                    subtitle: root.selectedReservationModel.statusLabel || root.selectedReservationModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (actionId === "issue") {
                            dialogHostLoader.invoke("openIssueReservationDialog", root.selectedReservationModel)
                        } else if (actionId === "release") {
                            dialogHostLoader.invoke("openReleaseConfirmation", root.selectedReservationModel)
                        } else if (actionId === "cancel") {
                            dialogHostLoader.invoke("openCancelConfirmation", root.selectedReservationModel)
                        }
                    }
                }

                Item {
                    id: _resDetailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _resDetailArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _fields: root.selectedReservationModel.fields || []

                    Item {
                        id: _resDetailArea
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.pagePadding
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.pagePadding
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.AppTheme.pagePadding
                        implicitHeight: _resOverview.visible ? _resOverview.implicitHeight
                            : _resActivity.implicitHeight + Theme.AppTheme.spacingMd

                        Item {
                            id: _resOverview
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _resDetailContent._idx === 0
                            implicitHeight: _resFieldsGrid.visible ? _resFieldsGrid.implicitHeight : _resEmpty.implicitHeight

                            GridLayout {
                                id: _resFieldsGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingMd
                                visible: _resDetailContent._fields.length > 0

                                Repeater {
                                    model: _resDetailContent._fields

                                    delegate: ColumnLayout {
                                        id: _rfd
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 2

                                        AppControls.Label {
                                            text: _rfd.modelData.label || ""
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.family: Theme.AppTheme.fontFamily
                                            font.bold: true
                                        }
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: _rfd.modelData.value || "—"
                                            color: Theme.AppTheme.textPrimary
                                            font.pixelSize: Theme.AppTheme.bodySize
                                            font.family: Theme.AppTheme.fontFamily
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }
                                    }
                                }
                            }

                            AppWidgets.EmptyState {
                                id: _resEmpty
                                width: parent.width
                                visible: _resDetailContent._fields.length === 0
                                title: root.selectedReservationModel.emptyState || "No details available."
                            }
                        }

                        AppWidgets.ActivityFeed {
                            id: _resActivity
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _resDetailContent._idx === 1
                            items: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                            emptyText: "No activity recorded yet."
                        }
                    }
                }
            }
        }
    }
}
