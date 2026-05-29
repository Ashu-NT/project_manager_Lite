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

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.inventoryWorkspace
        : null

    readonly property var storeroomsModel: root.workspaceController
        ? root.workspaceController.storerooms
        : ({ "items": [], "emptyState": "No storerooms configured." })
    readonly property var foundationModel: root.workspaceController
        ? root.workspaceController.foundation
        : ({ "locations": [], "locationTypeOptions": [] })
    readonly property var selectedStoreroomModel: root.workspaceController
        ? root.workspaceController.selectedStoreroom
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "state": {} })

    property string _warehouseView: "storerooms"
    readonly property bool _isStoreroomsView: root._warehouseView === "storerooms"

    readonly property string _selectedLocationId: root.workspaceController
        ? root.workspaceController.selectedLocationId
        : ""
    readonly property var _selectedLocationRow: {
        const id = root._selectedLocationId
        if (!id) return null
        const locs = root.foundationModel.locations || []
        for (let i = 0; i < locs.length; i++) {
            if (String(locs[i].id || "") === id) return locs[i]
        }
        return null
    }
    readonly property var _selectedLocationFields: {
        const row = root._selectedLocationRow
        if (!row) return []
        const fields = []
        if (row.title)         fields.push({ "label": "Location",       "value": row.title })
        if (row.statusLabel)   fields.push({ "label": "Type",           "value": row.statusLabel })
        if (row.subtitle)      fields.push({ "label": "Storeroom",      "value": row.subtitle })
        if (row.supportingText)fields.push({ "label": "Details",        "value": row.supportingText })
        if (row.metaText)      fields.push({ "label": "Active",         "value": row.metaText })
        return fields
    }

    title: "Warehouses & Locations"
    subtitle: "Storerooms, storage zones, bins, and sub-locations across all sites."

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _storeroomColumns: [
        { "key": "title",         "label": "Storeroom", "flex": 2,   "sortable": true  },
        { "key": "storeroomCode", "label": "Code",      "flex": 1   },
        { "key": "siteLabel",     "label": "Site",      "flex": 1.5 },
        { "key": "statusLabel",   "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _locationColumns: [
        { "key": "title",       "label": "Location",  "flex": 2,   "sortable": true  },
        { "key": "subtitle",    "label": "Storeroom", "flex": 1.5 },
        { "key": "statusLabel", "label": "Type",      "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "metaText",    "label": "Active",    "flex": 0,   "minWidth": 80 }
    ]

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        if (root._isStoreroomsView) {
            const detail = root.selectedStoreroomModel
            const isActive = detail && detail.state && detail.state.isActive
            return [
                { "id": "edit",   "label": "Edit",   "icon": "edit",             "enabled": true, "danger": false },
                { "id": "toggle", "label": isActive ? "Deactivate" : "Activate",
                  "icon": isActive ? "reject" : "approve",                         "enabled": true, "danger": false }
            ]
        }
        const row = root._selectedLocationRow
        const isActive = row && row.state && row.state.isActive
        return [
            { "id": "edit_location",   "label": "Edit",
              "icon": "edit",          "enabled": true, "danger": false },
            { "id": "toggle_location", "label": isActive ? "Deactivate" : "Activate",
              "icon": isActive ? "reject" : "approve",  "enabled": true, "danger": false }
        ]
    }

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) root._detailPage.scrollToSection(sectionIndex)
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
                onCreateLocationRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createLocation(payload)
                }
                onUpdateLocationRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateLocation(payload)
                }
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading warehouses..."
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
                    searchPlaceholder: root._isStoreroomsView ? "Search storerooms..." : "Search locations..."
                    showCreate: true
                    createLabel: root._isStoreroomsView ? "New Storeroom" : "New Location"
                    showFilter: true
                    showViews: true
                    showRefresh: true
                    showExport: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onCreateRequested: {
                        if (root._isStoreroomsView) {
                            dialogHostLoader.invoke("openCreateStoreroomDialog")
                        } else {
                            dialogHostLoader.invoke("openCreateLocationDialog",
                                root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all")
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: _storeroomsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: root._isStoreroomsView
                        multiSelect: false
                        columns: root._storeroomColumns
                        sourceModel: root.workspaceController ? root.workspaceController.storeroomsTableModel : null
                        rows: root.storeroomsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.storeroomsModel.emptyState || "No storerooms configured."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedStoreroomId : ""

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectStoreroom(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateStoreroom(rowId)
                            root._openDetail(0)
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.DataTable {
                        id: _locationsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: !root._isStoreroomsView
                        multiSelect: false
                        columns: root._locationColumns
                        sourceModel: root.workspaceController ? root.workspaceController.foundationTableModel : null
                        rows: root.foundationModel.locations || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: "No storage locations found."
                        selectedRowId: root._selectedLocationId

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectLocation(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateLocation(rowId)
                            root._openDetail(0)
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root._isStoreroomsView
                            ? (root.workspaceController ? root.workspaceController.storeroomPage : 1)
                            : (root.workspaceController ? root.workspaceController.locationPage : 1)
                        pageSize: root._isStoreroomsView
                            ? (root.workspaceController ? root.workspaceController.storeroomPageSize : 25)
                            : (root.workspaceController ? root.workspaceController.locationPageSize : 25)
                        totalItems: root._isStoreroomsView
                            ? (root.workspaceController ? root.workspaceController.storeroomTotalCount : 0)
                            : (root.workspaceController ? root.workspaceController.locationTotalCount : 0)
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController === null) return
                            if (root._isStoreroomsView) root.workspaceController.setStoreroomPage(page)
                            else root.workspaceController.setLocationPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController === null) return
                            if (root._isStoreroomsView) root.workspaceController.setStoreroomPageSize(size)
                            else root.workspaceController.setLocationPageSize(size)
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
                                visible: !root._isStoreroomsView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: !root._isStoreroomsView
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
                                text: "Location Type"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                visible: !root._isStoreroomsView
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                visible: !root._isStoreroomsView
                                model: root.foundationModel.locationTypeOptions || []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
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
                                text: "Storerooms"
                                iconName: "location"
                                enabled: !root._isStoreroomsView
                                onClicked: { root._warehouseView = "storerooms"; viewsPopup.close() }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Locations"
                                iconName: "inventory"
                                enabled: root._isStoreroomsView
                                onClicked: { root._warehouseView = "locations"; viewsPopup.close() }
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
                sections: ["Overview", "Activity"]
                z: 20

                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                }

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._isStoreroomsView
                        ? (root.selectedStoreroomModel.title || "Storeroom Detail")
                        : (root._selectedLocationRow ? (root._selectedLocationRow.title || "Location Detail") : "Location Detail")
                    subtitle: root._isStoreroomsView
                        ? (root.selectedStoreroomModel.statusLabel || root.selectedStoreroomModel.subtitle || "")
                        : (root._selectedLocationRow ? (root._selectedLocationRow.statusLabel || "") : "")
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
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
                        } else if (actionId === "edit_location") {
                            dialogHostLoader.invoke("openEditLocationDialog", root._selectedLocationRow || {})
                        } else if (actionId === "toggle_location") {
                            const row = root._selectedLocationRow
                            const st = row ? (row.state || {}) : {}
                            if (root.workspaceController !== null && st.locationId) {
                                root.workspaceController.updateLocation({
                                    "locationId": String(st.locationId || ""),
                                    "version": parseInt(String(st.version || "0"), 10),
                                    "isActive": !st.isActive,
                                })
                            }
                        }
                    }
                }

                Item {
                    id: _detailContent
                    width: parent ? parent.width : 0
                    implicitHeight: _detailSectionArea.implicitHeight + 2 * Theme.AppTheme.pagePadding

                    readonly property int _idx: root._detailPage ? root._detailPage.activeSectionIndex : 0
                    readonly property var _fields: root._isStoreroomsView
                        ? (root.selectedStoreroomModel.fields || [])
                        : root._selectedLocationFields

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
                                title: "No details available."
                            }
                        }

                        AppWidgets.ActivityFeed {
                            id: _detailActivity
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            visible: _detailContent._idx === 1
                            items: []
                            emptyText: "Activity history will appear here."
                        }
                    }
                }
            }
        }
    }
}
