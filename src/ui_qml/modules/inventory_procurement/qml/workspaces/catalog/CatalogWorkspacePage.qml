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
    property InventoryProcurementControllers.InventoryProcurementCatalogWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.catalogWorkspace
        : null
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Catalog", "subtitle": "Item master, categories, supplier references, and stock policies.", "metrics": [] })
    readonly property var itemsModel: root.workspaceController
        ? root.workspaceController.items
        : ({ "items": [], "emptyState": "No catalog items." })
    readonly property var categoriesModel: root.workspaceController
        ? root.workspaceController.categories
        : ({ "items": [], "emptyState": "No categories." })
    readonly property var selectedItemModel: root.workspaceController
        ? root.workspaceController.selectedItem
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "linkedDocuments": [], "state": {} })
    readonly property var selectedCategoryModel: root.workspaceController
        ? root.workspaceController.selectedCategory
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })

    readonly property bool _isItemsView: root.workspaceController
        ? root.workspaceController.activeView === "items"
        : true

    title: root.overviewModel.title || "Catalog"
    subtitle: root.overviewModel.subtitle || ""

    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _itemColumns: [
        { "key": "title",         "label": "Item Name", "flex": 2,   "sortable": true  },
        { "key": "itemCode",      "label": "Code",      "flex": 1   },
        { "key": "categoryLabel", "label": "Category",  "flex": 1.5 },
        { "key": "statusLabel",   "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _categoryColumns: [
        { "key": "title",             "label": "Category", "flex": 2,   "sortable": true  },
        { "key": "categoryCode",      "label": "Code",     "flex": 1   },
        { "key": "categoryTypeLabel", "label": "Type",     "flex": 1.5 },
        { "key": "statusLabel",       "label": "Status",   "flex": 0,   "minWidth": 90, "type": "status" }
    ]

    readonly property var _bulkChangeProperties: {
        const props = []
        const opts = root.workspaceController
            ? (root.workspaceController.itemStatusOptions || [])
            : []
        if (opts.length > 0) {
            props.push({ "id": "status", "label": "Status", "values": opts })
        }
        return props
    }

    readonly property var _detailSections: root._isItemsView
        ? ["Overview", "Documents", "Activity"]
        : ["Overview", "Activity"]

    readonly property var _detailActions: {
        const page = root._detailPage
        const idx = page ? page.activeSectionIndex : 0
        if (idx === 0) {
            const detail = root._isItemsView ? root.selectedItemModel : root.selectedCategoryModel
            const isActive = detail && detail.state && detail.state.isActive
            return [
                { "id": "edit",   "label": "Edit",       "icon": "edit",    "enabled": true, "danger": false },
                { "id": "toggle", "label": isActive ? "Deactivate" : "Activate",
                  "icon": isActive ? "reject" : "approve", "enabled": true, "danger": false }
            ]
        }
        return []
    }

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return 0
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) return
        const activityIdx = root._isItemsView ? 2 : 1
        if (sectionIndex !== activityIdx) return
        const entityId = root._isItemsView
            ? String(root.selectedItemModel.id || "")
            : String(root.selectedCategoryModel.id || "")
        const entityType = root._isItemsView ? "inventory_item" : "inventory_category"
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

    // ── Dialog host (lazy) ─────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            CatalogDialogHost {
                categoryTypeOptions: root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                itemStatusOptions: root.workspaceController ? (root.workspaceController.itemStatusOptions || []) : []
                businessPartyOptions: root.workspaceController ? (root.workspaceController.businessPartyOptions || []) : []
                availableDocuments: root.workspaceController ? (root.workspaceController.availableDocuments || []) : []

                onCreateCategoryRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createCategory(payload)
                }
                onUpdateCategoryRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateCategory(payload)
                }
                onCreateItemRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createItem(payload)
                }
                onUpdateItemRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.updateItem(payload)
                }
                onLinkDocumentRequested: function(itemId, documentId) {
                    if (root.workspaceController !== null) root.workspaceController.linkDocument(itemId, documentId)
                }
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────
    Item {
        anchors.fill: parent

        // ── List page ──────────────────────────────────────────────
        Item {
            id: _listPage
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
                    message: "Loading catalog..."
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
                    searchPlaceholder: root._isItemsView ? "Search items..." : "Search categories..."
                    showCreate: true
                    createLabel: root._isItemsView ? "New Item" : "New Category"
                    showFilter: true
                    showCustomize: root._isItemsView
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: {
                        if (root._isItemsView) {
                            _itemsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                        }
                    }
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {}
                    onCreateRequested: {
                        if (root._isItemsView) {
                            dialogHostLoader.invoke("openCreateItemDialog")
                        } else {
                            dialogHostLoader.invoke("openCreateCategoryDialog")
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    // Items DataTable
                    AppWidgets.DataTable {
                        id: _itemsTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: root._isItemsView
                        multiSelect: true
                        columns: root._itemColumns
                        rows: root.itemsModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.itemsModel.emptyState || "No catalog items."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedItemId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedItemIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectItem(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateItem(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setItemBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) {
                                root.workspaceController.selectVisibleItems()
                            } else {
                                root.workspaceController.clearItemBulkSelection()
                            }
                        }
                        onSortRequested: function(key) {}
                    }

                    // Categories DataTable
                    AppWidgets.DataTable {
                        id: _categoriesTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: _paginationBar.top
                        visible: !root._isItemsView
                        multiSelect: true
                        columns: root._categoryColumns
                        rows: root.categoriesModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.categoriesModel.emptyState || "No categories."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedCategoryId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedCategoryIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectCategory(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.activateCategory(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) root.workspaceController.setCategoryBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) {
                                root.workspaceController.selectVisibleCategories()
                            } else {
                                root.workspaceController.clearCategoryBulkSelection()
                            }
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        currentPage: root._isItemsView
                            ? (root.workspaceController ? root.workspaceController.itemPage : 1)
                            : (root.workspaceController ? root.workspaceController.categoryPage : 1)
                        pageSize: root._isItemsView
                            ? (root.workspaceController ? root.workspaceController.itemPageSize : 25)
                            : (root.workspaceController ? root.workspaceController.categoryPageSize : 25)
                        totalItems: root._isItemsView
                            ? (root.workspaceController ? root.workspaceController.itemTotalCount : 0)
                            : (root.workspaceController ? root.workspaceController.categoryTotalCount : 0)
                        busy: root.workspaceController ? root.workspaceController.isBusy : false

                        onPageRequested: function(page) {
                            if (root.workspaceController === null) return
                            if (root._isItemsView) root.workspaceController.setItemPage(page)
                            else root.workspaceController.setCategoryPage(page)
                        }
                        onPageSizeRequested: function(size) {
                            if (root.workspaceController === null) return
                            if (root._isItemsView) root.workspaceController.setItemPageSize(size)
                            else root.workspaceController.setCategoryPageSize(size)
                        }
                    }

                    // Filter popup
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
                                text: "Category"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.categoryOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setCategoryFilter(String(opts[index].value || "all"))
                                    }
                                }
                            }

                            AppControls.Label {
                                text: "Category Type"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedCategoryTypeFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setCategoryTypeFilter(String(opts[index].value || "all"))
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

                    // Views popup (switch Items / Categories)
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
                                text: "Items"
                                iconName: "inventory"
                                enabled: !root._isItemsView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("items")
                                    viewsPopup.close()
                                }
                            }
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                text: "Categories"
                                iconName: "register"
                                enabled: root._isItemsView
                                onClicked: {
                                    if (root.workspaceController !== null) root.workspaceController.setActiveView("categories")
                                    viewsPopup.close()
                                }
                            }
                        }
                    }

                    // Bulk action bar (items)
                    AppWidgets.BulkActionBar {
                        id: _itemBulkBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        visible: root._isItemsView
                        selectedCount: root.workspaceController ? root.workspaceController.selectedItemCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearItemBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "change_property") {
                                _itemBulkChangePopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: _itemBulkChangePopup
                        anchorItem: _itemBulkBar.actionButtonForId("change_property")
                        selectedCount: root.workspaceController ? root.workspaceController.selectedItemCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        properties: root._bulkChangeProperties

                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) {
                                return
                            }
                            if (payload.propertyId === "status") {
                                root.workspaceController.applyBulkStatus({ "status": payload.value })
                            }
                        }
                    }

                    // Bulk action bar (categories)
                    AppWidgets.BulkActionBar {
                        id: _catBulkBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        visible: !root._isItemsView
                        selectedCount: root.workspaceController ? root.workspaceController.selectedCategoryCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "archive", "label": "Archive", "icon": "delete", "danger": true, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearCategoryBulkSelection()
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

                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }
                onSectionChanged: function(index) {
                    root._loadLazyDetailSection(index)
                }

                // ── Contextual toolbar ─────────────────────────────
                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root._isItemsView
                        ? (root.selectedItemModel.title || "Item Detail")
                        : (root.selectedCategoryModel.title || "Category Detail")
                    subtitle: root._isItemsView
                        ? (root.selectedItemModel.statusLabel || root.selectedItemModel.subtitle || "")
                        : (root.selectedCategoryModel.statusLabel || root.selectedCategoryModel.subtitle || "")
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            if (root._isItemsView) {
                                dialogHostLoader.invoke("openEditItemDialog", root.selectedItemModel)
                            } else {
                                dialogHostLoader.invoke("openEditCategoryDialog", root.selectedCategoryModel)
                            }
                        } else if (actionId === "toggle") {
                            if (root._isItemsView) {
                                const state = root.selectedItemModel.state || {}
                                if (root.workspaceController !== null && state.itemId) {
                                    root.workspaceController.toggleItemActive(
                                        String(state.itemId || ""),
                                        parseInt(String(state.version || "0"), 10)
                                    )
                                }
                            } else {
                                const state = root.selectedCategoryModel.state || {}
                                if (root.workspaceController !== null && state.categoryId) {
                                    root.workspaceController.toggleCategoryActive(
                                        String(state.categoryId || ""),
                                        parseInt(String(state.version || "0"), 10)
                                    )
                                }
                            }
                        }
                    }
                }

                // ── Detail content ─────────────────────────────────
                CatalogDetailContent {
                    width: parent ? parent.width : 0
                    isItemsView: root._isItemsView
                    itemDetail: root.selectedItemModel
                    categoryDetail: root.selectedCategoryModel
                    detailPage: root._detailPage
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    activityItems: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []

                    onLinkDocumentRequested: dialogHostLoader.invoke("openLinkDocumentDialog", root.selectedItemModel)
                    onUnlinkDocumentRequested: function(documentData) {
                        const state = root.selectedItemModel.state || {}
                        if (root.workspaceController !== null && state.itemId && documentData && documentData.value) {
                            root.workspaceController.unlinkDocument(
                                String(state.itemId || ""),
                                String(documentData.value || "")
                            )
                        }
                    }
                }
            }
        }
    }
}
